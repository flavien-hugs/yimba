"""yimba user create | set-role, on a SQLite file."""

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine
from typer.testing import CliRunner

from yimba.config import get_settings
from yimba.entrypoints import cli
from yimba.infrastructure.db import Base
from yimba.modules.identity.adapters import persistence as _i  # noqa: F401


def test_create_the_first_admin_then_change_a_role(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'users.db'}"

    async def create_tables():
        engine = create_async_engine(url)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(create_tables())
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("REGISTRATION_ENABLED", "false")  # the CLI creates accounts anyway
    get_settings.cache_clear()
    runner = CliRunner()
    try:
        password = "correct horse battery\n"
        created = runner.invoke(cli.app, ["user", "create", "Admin@Example.org", "--role", "admin"], input=password * 2)
        assert created.exit_code == 0, created.output
        assert "Created admin@example.org (admin)" in created.output

        duplicate = runner.invoke(cli.app, ["user", "create", "admin@example.org"], input=password * 2)
        assert duplicate.exit_code != 0

        runner.invoke(cli.app, ["user", "create", "u@example.org"], input=password * 2)
        promoted = runner.invoke(cli.app, ["user", "set-role", "u@example.org", "admin"])
        assert promoted.exit_code == 0 and "u@example.org is now admin" in promoted.output
    finally:
        get_settings.cache_clear()
