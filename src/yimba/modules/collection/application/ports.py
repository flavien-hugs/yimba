from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from yimba.modules.collection.domain.model import CollectedItem, CollectionRun, CollectionTarget
from yimba.shared.source import SourceKind


@dataclass(frozen=True, slots=True)
class CollectionWatch:
    id: str
    keywords: tuple[str, ...]
    sources: tuple[SourceKind, ...]
    languages: tuple[str, ...]
    countries: tuple[str, ...]
    frequency_minutes: int
    active: bool


@dataclass(frozen=True, slots=True)
class SinkResult:
    stored: int
    duplicates: int
    skipped: int


class Collector(Protocol):
    source: SourceKind

    async def collect(self, target: CollectionTarget) -> Sequence[CollectedItem]:
        """Fetch publications. Raise ``ExternalServiceError`` when the source fails."""


CollectorRegistry = Mapping[SourceKind, Collector]


class WatchCatalog(Protocol):
    async def get(self, watch_id: str) -> CollectionWatch | None: ...

    async def list_active(self) -> Sequence[CollectionWatch]: ...


class ItemSink(Protocol):
    async def ingest(self, watch_id: str, items: Sequence[CollectedItem]) -> SinkResult: ...


class RunRepository(Protocol):
    async def last_run(self, watch_id: str, source: SourceKind) -> CollectionRun | None: ...

    async def save(self, run: CollectionRun) -> None: ...


class CollectionQueue(Protocol):
    async def enqueue_collection(self, watch_id: str, source: SourceKind) -> None: ...
