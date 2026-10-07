from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import typer
import uvicorn

from yimba import __version__
from yimba.config import get_settings
from yimba.shared.source import SourceKind

# backend/ in the repository, /app in the image: where alembic.ini lives.
BACKEND_ROOT = Path(__file__).resolve().parents[2]

app = typer.Typer(no_args_is_help=True, help="Yimba command line")
annotation = typer.Typer(no_args_is_help=True, help="Annotated corpus (Label Studio) and analyzer evaluation")
app.add_typer(annotation, name="annotation")


@app.command()
def api(host: str = typer.Option(None), port: int = typer.Option(None), reload: bool = False) -> None:
    """Run the HTTP API."""
    settings = get_settings()
    uvicorn.run(
        "yimba.entrypoints.api.app:create_app",
        factory=True,
        host=host or settings.API_HOST,
        port=port or settings.API_PORT,
        reload=reload,
    )


@app.command()
def worker(concurrency: int = typer.Option(2)) -> None:
    """Run a collection worker."""
    from yimba.entrypoints.worker.app import celery

    celery.worker_main(["worker", "--loglevel=INFO", f"--concurrency={concurrency}", "-Q", "yimba"])


@app.command()
def beat() -> None:
    """Run the scheduler that plans collections every minute."""
    from yimba.entrypoints.worker.app import celery

    # The schedule state file must live somewhere writable: the image's /app belongs to root.
    celery.start(["beat", "--loglevel=INFO", "--schedule=/tmp/celerybeat-schedule"])


@app.command()
def flower(port: int = typer.Option(5555)) -> None:
    """Run Flower, the web UI that shows the workers, the queue and every task."""
    from yimba.entrypoints.worker.app import celery

    settings = get_settings()
    arguments = ["flower", f"--port={port}"]
    if settings.FLOWER_BASIC_AUTH:
        arguments.append(f"--basic-auth={settings.FLOWER_BASIC_AUTH}")
    elif settings.is_production:
        typer.echo("FLOWER_BASIC_AUTH must be set in production: Flower can revoke tasks.", err=True)
        raise typer.Exit(code=1)
    celery.start(arguments)


@app.command()
def collect(watch_id: str, source: SourceKind) -> None:
    """Collect one source for one watch right now, without going through the queue."""
    from sqlalchemy.pool import NullPool

    from yimba.bootstrap import Container

    async def main() -> None:
        container = Container(get_settings(), engine_kwargs={"poolclass": NullPool})
        try:
            async with container.session_factory() as session:
                run = await container.collect_for_watch(session).execute(watch_id, source)
        finally:
            await container.aclose()
        if run is None:
            typer.echo("Nothing to collect (unknown or inactive watch, source not enabled or not configured).")
            raise typer.Exit(code=1)
        typer.echo(f"{run.status.value}: fetched={run.fetched} stored={run.stored} error={run.error}")

    asyncio.run(main())


@app.command("db-upgrade")
def db_upgrade(revision: str = "head") -> None:
    """Apply database migrations."""
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), revision)


@annotation.command("config")
def annotation_config() -> None:
    """Print the Label Studio labeling interface (paste it in the project settings)."""
    from yimba.modules.analysis.public import LABELING_CONFIG

    typer.echo(LABELING_CONFIG)


@annotation.command("export")
def annotation_export(
    watch_id: str,
    out: Path = typer.Option(..., "--out", help="Label Studio tasks file to write (JSON)"),
    size: int = typer.Option(300, min=1),
    source: SourceKind | None = typer.Option(None),
    language: str | None = typer.Option(None),
    with_predictions: bool = typer.Option(
        False, help="Pre-fill with the analyzer's answers: faster, but biases a reference corpus"
    ),
) -> None:
    """Sample mentions of a watch as Label Studio tasks (text and ids only: no author, no link)."""
    from sqlalchemy.pool import NullPool

    from yimba.bootstrap import Container
    from yimba.modules.analysis.public import build_tasks
    from yimba.modules.mentions.adapters.persistence import SqlMentionRepository
    from yimba.modules.mentions.application.ports import MentionFilters

    settings = get_settings()

    async def main() -> list:
        container = Container(settings, engine_kwargs={"poolclass": NullPool})
        try:
            async with container.session_factory() as session:
                filters = MentionFilters(watch_id=watch_id, source=source, language=language)
                return list(await SqlMentionRepository(session).sample(filters, size))
        finally:
            await container.aclose()

    mentions = asyncio.run(main())
    texts = [{"text": m.text, "mention_id": m.id, "source": m.source.value, "language": m.language} for m in mentions]
    predictions = None
    if with_predictions:
        from yimba.modules.analysis.public import build_text_analyzer

        analyzer = build_text_analyzer(settings.ANALYSIS_ENGINE, settings.ANALYSIS_MODEL)
        predictions = [analyzer.analyze(m.text) for m in mentions]
    tasks = build_tasks(texts, predictions, model_version=settings.ANALYSIS_ENGINE)
    out.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"{len(tasks)} task(s) written to {out}")


@annotation.command("evaluate")
def annotation_evaluate(
    export: Path = typer.Argument(..., exists=True, dir_okay=False, help="Label Studio JSON export"),
    engine: str | None = typer.Option(None, help="Analyzer to evaluate (default: ANALYSIS_ENGINE)"),
    model: str | None = typer.Option(None, help="Model name for the transformers engine"),
    run_name: str | None = typer.Option(None),
) -> None:
    """Score an analyzer against the annotations; record the run on MLflow when MLFLOW_TRACKING_URI is set."""
    from yimba.modules.analysis.public import (
        EvaluateAnalyzer,
        MlflowTracker,
        build_text_analyzer,
        lexicon_fingerprint,
        read_annotations,
    )

    settings = get_settings()
    engine = engine or settings.ANALYSIS_ENGINE
    model = model or settings.ANALYSIS_MODEL
    content = export.read_bytes()
    corpus = read_annotations(json.loads(content))
    if not corpus:
        typer.echo("No usable annotation in this export.", err=True)
        raise typer.Exit(code=1)

    params = {
        "engine": engine,
        "model": model or "-",
        "lexicon_version": lexicon_fingerprint(),
        "corpus_file": export.name,
        "corpus_sha256": hashlib.sha256(content).hexdigest()[:12],
        "yimba_version": __version__,
    }
    tracker = (
        MlflowTracker(settings.MLFLOW_TRACKING_URI, settings.MLFLOW_EXPERIMENT)
        if settings.MLFLOW_TRACKING_URI
        else None
    )
    name = run_name or f"{engine}-{datetime.now(timezone.utc):%Y%m%d-%H%M}"
    reports, run_id = EvaluateAnalyzer(build_text_analyzer(engine, model), tracker).execute(
        corpus, run_name=name, params=params
    )
    for report in reports:
        typer.echo(f"{report.task}: n={report.size} accuracy={report.accuracy:.3f} macro_f1={report.macro_f1:.3f}")
        for label, scores in report.per_label.items():
            typer.echo(
                f"  {label:<9} precision={scores.precision:.3f} recall={scores.recall:.3f} "
                f"f1={scores.f1:.3f} support={scores.support}"
            )
    if run_id:
        typer.echo(f"MLflow run {run_id} ({settings.MLFLOW_TRACKING_URI})")


if __name__ == "__main__":
    app()
