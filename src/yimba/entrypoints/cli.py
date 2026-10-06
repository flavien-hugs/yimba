from __future__ import annotations

import asyncio

import typer
import uvicorn

from yimba.config import get_settings
from yimba.shared.source import SourceKind

app = typer.Typer(no_args_is_help=True, help="Yimba command line")


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

    celery.start(["beat", "--loglevel=INFO"])


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

    command.upgrade(Config("alembic.ini"), revision)


if __name__ == "__main__":
    app()
