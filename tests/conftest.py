from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy.pool import NullPool, StaticPool

from yimba.bootstrap import Container
from yimba.config import Settings
from yimba.infrastructure.db import Base

# Register every table on Base.metadata.
from yimba.modules.alerts.adapters import persistence as _a  # noqa: F401
from yimba.modules.analysis.public import build_text_analyzer
from yimba.modules.collection.adapters import persistence as _c  # noqa: F401
from yimba.modules.identity.domain.model import Principal
from yimba.modules.mentions.adapters import persistence as _m  # noqa: F401
from yimba.modules.watches.adapters import persistence as _w  # noqa: F401
from yimba.shared.errors import Forbidden, Unauthorized

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)

# Run the suite against a real PostgreSQL with e.g. TEST_DATABASE_URL=postgresql+asyncpg://user@localhost/yimba_test
# (the tables are dropped and recreated for every test). SQLite in memory is the default.
POSTGRES_URL = os.environ.get("TEST_DATABASE_URL")


class FixedClock:
    def __init__(self, now: datetime = NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        self._now = now


class FakeAccessControl:
    """Tokens look like ``user:<id>`` or ``user:<id>|deny=<permission>``."""

    async def authenticate(self, token: str) -> Principal:
        identity = token.split("|")[0]
        kind, _, user_id = identity.partition(":")
        if kind != "user" or not user_id:
            raise Unauthorized("bad token")
        return Principal(id=user_id, email=f"{user_id}@example.org")

    async def authorize(self, token: str, permissions) -> None:
        denied = {part[5:] for part in token.split("|")[1:] if part.startswith("deny=")}
        if denied & set(permissions):
            raise Forbidden("missing permission")


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
async def container(clock):
    settings = Settings(database_url=POSTGRES_URL or "sqlite+aiosqlite://", author_hash_salt="test-salt")
    engine_kwargs = (
        {"poolclass": NullPool}
        if POSTGRES_URL
        else {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
    )
    container = Container(
        settings,
        clock=clock,
        access_control=FakeAccessControl(),
        analyzer=build_text_analyzer("lexicon"),
        collectors={},
        http_client=httpx.AsyncClient(),
        engine_kwargs=engine_kwargs,
    )
    async with container.engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield container
    if POSTGRES_URL:
        async with container.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
    await container.aclose()


@pytest.fixture
async def session(container):
    async with container.session_factory() as session:
        yield session
