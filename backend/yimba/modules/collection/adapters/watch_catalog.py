from __future__ import annotations

from typing import Sequence

from yimba.modules.collection.application.ports import CollectionWatch
from yimba.modules.watches.public import WatchDirectory, WatchSummary


def _to_collection_watch(summary: WatchSummary) -> CollectionWatch:
    return CollectionWatch(
        id=summary.id,
        keywords=summary.keywords,
        sources=summary.sources,
        languages=summary.languages,
        countries=summary.countries,
        frequency_minutes=summary.frequency_minutes,
        active=summary.active,
    )


class DirectoryWatchCatalog:
    """Anti-corruption layer between the watches module and what collection needs to know about a watch."""

    def __init__(self, directory: WatchDirectory) -> None:
        self._directory = directory

    async def get(self, watch_id: str) -> CollectionWatch | None:
        summary = await self._directory.get(watch_id)
        return _to_collection_watch(summary) if summary else None

    async def list_active(self) -> Sequence[CollectionWatch]:
        return tuple(_to_collection_watch(s) for s in await self._directory.list_active())
