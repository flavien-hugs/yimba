from __future__ import annotations

import logging
from typing import Collection

from yimba.modules.collection.application.ports import (
    CollectionQueue,
    CollectorRegistry,
    ItemSink,
    RunRepository,
    WatchCatalog,
)
from yimba.modules.collection.domain.model import CollectionRun, CollectionTarget, RunStatus, is_due
from yimba.shared.clock import Clock
from yimba.shared.errors import DomainError
from yimba.shared.ids import new_id
from yimba.shared.source import SourceKind

logger = logging.getLogger(__name__)


class PlanCollections:
    """Called every minute by the scheduler: enqueue a collection for each (watch, source) that is due.

    ``sources`` are the sources that have a collector; the others are skipped, otherwise they would never
    record a run and be enqueued again every minute.
    """

    def __init__(
        self,
        catalog: WatchCatalog,
        runs: RunRepository,
        queue: CollectionQueue,
        clock: Clock,
        sources: Collection[SourceKind] | None = None,
    ) -> None:
        self._catalog = catalog
        self._runs = runs
        self._queue = queue
        self._clock = clock
        self._sources = None if sources is None else frozenset(sources)

    async def execute(self) -> int:
        now = self._clock.now()
        enqueued = 0
        for watch in await self._catalog.list_active():
            for source in watch.sources:
                if self._sources is not None and source not in self._sources:
                    continue
                last_run = await self._runs.last_run(watch.id, source)
                if is_due(last_run, watch.frequency_minutes, now):
                    await self._queue.enqueue_collection(watch.id, source)
                    enqueued += 1
        return enqueued


class CollectForWatch:
    """Collect one source for one watch, hand the items to the sink, and keep a record of the run."""

    def __init__(
        self,
        catalog: WatchCatalog,
        collectors: CollectorRegistry,
        sink: ItemSink,
        runs: RunRepository,
        clock: Clock,
        limit: int = 50,
    ) -> None:
        self._catalog = catalog
        self._collectors = collectors
        self._sink = sink
        self._runs = runs
        self._clock = clock
        self._limit = limit

    async def execute(self, watch_id: str, source: SourceKind) -> CollectionRun | None:
        watch = await self._catalog.get(watch_id)
        if watch is None or not watch.active or source not in watch.sources:
            return None
        collector = self._collectors.get(source)
        if collector is None:
            logger.warning("No collector configured for source %s", source.value)
            return None

        run = CollectionRun(
            id=new_id(), watch_id=watch_id, source=source, status=RunStatus.RUNNING, started_at=self._clock.now()
        )
        await self._runs.save(run)

        target = CollectionTarget(
            watch_id=watch_id,
            source=source,
            keywords=watch.keywords,
            languages=watch.languages,
            countries=watch.countries,
            limit=self._limit,
        )
        try:
            items = await collector.collect(target)
            result = await self._sink.ingest(watch_id, items)
        except DomainError as exc:
            run.fail(at=self._clock.now(), error=exc.message)
            logger.warning("Collection failed for watch=%s source=%s: %s", watch_id, source.value, exc.message)
        except Exception as exc:  # noqa: BLE001 - a crashing source must never take the worker down
            run.fail(at=self._clock.now(), error=f"{type(exc).__name__}: {exc}")
            logger.exception("Unexpected collection failure for watch=%s source=%s", watch_id, source.value)
        else:
            run.succeed(at=self._clock.now(), fetched=len(items), stored=result.stored)
        await self._runs.save(run)
        return run
