"""The Celery tasks end to end (eager mode, real SQLite file, fake collector)."""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from yimba.bootstrap import Container
from yimba.config import get_settings
from yimba.infrastructure.db import Base, make_session_factory

# Register tables.
from yimba.modules.alerts.adapters import persistence as _a  # noqa: F401
from yimba.modules.collection.adapters import persistence as _c  # noqa: F401
from yimba.modules.collection.domain.model import CollectedItem
from yimba.modules.mentions.adapters.persistence import SqlMentionRepository
from yimba.modules.mentions.application.ports import MentionFilters
from yimba.modules.watches.adapters.persistence import SqlWatchRepository
from yimba.modules.watches.domain.model import AlertThreshold, Watch
from yimba.shared.pagination import PageParams
from yimba.shared.source import SourceKind


class StaticCollector:
    source = SourceKind.NEWS

    async def collect(self, target):
        return [
            (
                CollectedItem(
                    SourceKind.NEWS,
                    str(i),
                    "Honte et scandale, quelle arnaque",
                    published_at=datetime.now(timezone.utc),
                )
                if i == 0
                else CollectedItem(
                    SourceKind.NEWS,
                    str(i),
                    f"Colère, rupture et pénurie numéro {i}",
                    published_at=datetime.now(timezone.utc),
                )
            )
            for i in range(3)
        ]


@pytest.fixture
async def database(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'worker.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    monkeypatch.setattr(Container, "_build_collectors", lambda self: {SourceKind.NEWS: StaticCollector()})
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = make_session_factory(engine)
    async with sessions() as session:
        watch = Watch.create(
            owner_id="u1",
            name="Santé",
            keywords=["vaccin"],
            sources=[SourceKind.NEWS],
            threshold=AlertThreshold(0.4, 2),
            now=datetime.now(timezone.utc),
        )
        await SqlWatchRepository(session).add(watch)
    yield sessions, watch
    await engine.dispose()
    get_settings.cache_clear()


async def test_collect_task_stores_mentions_and_raises_the_alert(database):
    from yimba.entrypoints.worker.app import collect

    sessions, watch = database
    result = await asyncio.to_thread(lambda: collect.apply(args=[watch.id, "news"]).get())
    assert result == "succeeded"

    async with sessions() as session:
        page = await SqlMentionRepository(session).search(MentionFilters(watch.id), PageParams())
        assert page.total == 3
        from yimba.modules.alerts.adapters.persistence import SqlAlertRepository

        assert (await SqlAlertRepository(session).latest_for_watch(watch.id)) is not None

    # Collecting the same items again stores nothing new and does not alert again (cooldown).
    assert await asyncio.to_thread(lambda: collect.apply(args=[watch.id, "news"]).get()) == "succeeded"
    async with sessions() as session:
        assert (await SqlMentionRepository(session).search(MentionFilters(watch.id), PageParams())).total == 3


async def test_plan_task_enqueues_due_collections_once(database, monkeypatch):
    from yimba.entrypoints.worker.app import celery, plan_collections

    sessions, watch = database
    sent = []
    monkeypatch.setattr(celery, "send_task", lambda name, args: sent.append((name, args)))

    assert await asyncio.to_thread(lambda: plan_collections.apply().get()) == 1
    assert sent == [("yimba.collect", [watch.id, "news"])]

    await asyncio.to_thread(lambda: celery.tasks["yimba.collect"].apply(args=[watch.id, "news"]).get())
    sent.clear()
    assert await asyncio.to_thread(lambda: plan_collections.apply().get()) == 0  # just collected: not due yet
