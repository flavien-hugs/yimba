"""The only import surface other modules may use.

Exposes a read-only directory of watches so that collection and alerts never touch
the watches tables or domain objects directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from yimba.modules.watches.adapters.persistence import SqlWatchRepository
from yimba.shared.source import SourceKind


@dataclass(frozen=True, slots=True)
class WatchSummary:
    id: str
    owner_id: str
    name: str
    keywords: tuple[str, ...]
    sources: tuple[SourceKind, ...]
    languages: tuple[str, ...]
    countries: tuple[str, ...]
    frequency_minutes: int
    alert_negative_share: float
    alert_min_mentions: int
    active: bool


class WatchDirectory(Protocol):
    async def get(self, watch_id: str) -> WatchSummary | None: ...

    async def list_active(self) -> Sequence[WatchSummary]: ...


class SqlWatchDirectory:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = SqlWatchRepository(session)

    @staticmethod
    def _summary(watch) -> WatchSummary:
        return WatchSummary(
            id=watch.id,
            owner_id=watch.owner_id,
            name=watch.name,
            keywords=watch.keywords,
            sources=watch.sources,
            languages=watch.languages,
            countries=watch.countries,
            frequency_minutes=watch.frequency.minutes,
            alert_negative_share=watch.threshold.negative_share,
            alert_min_mentions=watch.threshold.min_mentions,
            active=watch.active,
        )

    async def get(self, watch_id: str) -> WatchSummary | None:
        watch = await self._repository.get(watch_id)
        return self._summary(watch) if watch else None

    async def list_active(self) -> Sequence[WatchSummary]:
        return tuple(self._summary(watch) for watch in await self._repository.list_active())


def build_watch_directory(session: AsyncSession) -> WatchDirectory:
    return SqlWatchDirectory(session)


__all__ = ["WatchDirectory", "WatchSummary", "build_watch_directory"]
