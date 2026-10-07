"""yimba annotation config | export | evaluate, end to end on a SQLite file."""

import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine
from typer.testing import CliRunner

from yimba.config import get_settings
from yimba.entrypoints import cli
from yimba.infrastructure.db import Base, make_session_factory
from yimba.modules.analysis.public import build_text_analyzer
from yimba.modules.mentions.adapters import persistence as _m  # noqa: F401
from yimba.modules.mentions.public import IncomingMention, build_mention_ingestor
from yimba.modules.watches.adapters.persistence import SqlWatchRepository
from yimba.modules.watches.domain.model import Watch
from yimba.shared.clock import SystemClock
from yimba.shared.source import SourceKind

TEXTS = ["Bravo, super campagne", "Honte et scandale", "Le ministre parle ce matin"]


def seed(url: str) -> str:
    async def main() -> str:
        engine = create_async_engine(url)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with make_session_factory(engine)() as session:
            now = datetime.now(timezone.utc)
            watch = Watch.create(owner_id="u1", name="Santé", keywords=["vaccin"], sources=[SourceKind.NEWS], now=now)
            await SqlWatchRepository(session).add(watch)
            ingest = build_mention_ingestor(session, build_text_analyzer("lexicon"), SystemClock(), "salt")
            await ingest.ingest(
                watch.id,
                [IncomingMention(SourceKind.NEWS, str(i), text, author_handle="@awa") for i, text in enumerate(TEXTS)],
            )
        await engine.dispose()
        return watch.id

    return asyncio.run(main())


def test_export_then_evaluate(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'annotation.db'}"
    watch_id = seed(url)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    get_settings.cache_clear()
    runner = CliRunner()
    try:
        config = runner.invoke(cli.app, ["annotation", "config"])
        assert config.exit_code == 0 and '<Choices name="sentiment"' in config.output

        tasks_file = tmp_path / "tasks.json"
        exported = runner.invoke(cli.app, ["annotation", "export", watch_id, "--out", str(tasks_file), "--size", "10"])
        assert exported.exit_code == 0, exported.output
        tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
        assert sorted(task["data"]["text"] for task in tasks) == sorted(TEXTS)
        assert all("awa" not in json.dumps(task) and "predictions" not in task for task in tasks)

        # What an annotator would send back from Label Studio.
        labels = {TEXTS[0]: "Positif", TEXTS[1]: "Négatif", TEXTS[2]: "Neutre"}
        for task in tasks:
            choice = {"choices": [labels[task["data"]["text"]]]}
            task["annotations"] = [{"result": [{"from_name": "sentiment", "type": "choices", "value": choice}]}]
        export_file = tmp_path / "export.json"
        export_file.write_text(json.dumps(tasks), encoding="utf-8")

        evaluated = runner.invoke(cli.app, ["annotation", "evaluate", str(export_file)])
        assert evaluated.exit_code == 0, evaluated.output
        assert "sentiment: n=3 accuracy=1.000 macro_f1=1.000" in evaluated.output
    finally:
        get_settings.cache_clear()


def test_evaluate_refuses_an_export_without_annotations(tmp_path):
    export_file = tmp_path / "empty.json"
    export_file.write_text("[]", encoding="utf-8")
    result = CliRunner().invoke(cli.app, ["annotation", "evaluate", str(export_file)])
    assert result.exit_code == 1 and "No usable annotation" in result.output
