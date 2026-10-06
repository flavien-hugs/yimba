"""Celery application: a scheduler tick plans collections, workers run them one (watch, source) at a time."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

from celery import Celery
from sqlalchemy.pool import NullPool

from yimba.bootstrap import Container
from yimba.config import get_settings
from yimba.modules.collection.adapters.queue import TaskQueue
from yimba.modules.collection.domain.model import RunStatus
from yimba.shared.source import SourceKind

logger = logging.getLogger(__name__)
T = TypeVar("T")

settings = get_settings()
celery = Celery("yimba", broker=settings.redis_url)
celery.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="yimba",
    beat_schedule={"plan-collections": {"task": "yimba.plan", "schedule": 60.0}},
)


def _run(work: Callable[[Container], Awaitable[T]]) -> T:
    """Run ``work`` with a short-lived container.

    asyncio.run() creates a fresh event loop per task, so no pooled connection may outlive it (hence NullPool).
    """

    async def main() -> T:
        container = Container(get_settings(), engine_kwargs={"poolclass": NullPool})
        try:
            return await work(container)
        finally:
            await container.aclose()

    return asyncio.run(main())


@celery.task(name="yimba.plan")
def plan_collections() -> int:
    async def work(container: Container) -> int:
        async with container.session_factory() as session:
            return await container.plan_collections(session, celery.send_task).execute()

    enqueued = _run(work)
    if enqueued:
        logger.info("Planned %s collection(s)", enqueued)
    return enqueued


@celery.task(name=TaskQueue.COLLECT_TASK, bind=True, max_retries=0)
def collect(self, watch_id: str, source: str) -> str | None:
    async def work(container: Container) -> str | None:
        async with container.session_factory() as session:
            run = await container.collect_for_watch(session).execute(watch_id, SourceKind(source))
        if run is None:
            return None
        if run.status is RunStatus.SUCCEEDED and run.stored:
            async with container.session_factory() as session:
                await container.evaluate_alerts(session).execute(watch_id)
        return run.status.value

    return _run(work)
