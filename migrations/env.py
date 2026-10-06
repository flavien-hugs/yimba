from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from yimba.config import get_settings
from yimba.infrastructure.db import Base

# Importing the persistence adapters registers every table on Base.metadata.
from yimba.modules.alerts.adapters import persistence as _alerts  # noqa: F401
from yimba.modules.collection.adapters import persistence as _collection  # noqa: F401
from yimba.modules.mentions.adapters import persistence as _mentions  # noqa: F401
from yimba.modules.watches.adapters import persistence as _watches  # noqa: F401

target_metadata = Base.metadata


def _url() -> str:
    return context.config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def _do_run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(_url())
    async with engine.connect() as connection:
        await connection.run_sync(_do_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
