from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, unique
from typing import Protocol, Sequence

from yimba.modules.watches.domain.model import Watch
from yimba.shared.pagination import Page, PageParams


@unique
class WatchSort(StrEnum):
    CREATED = "created"
    NAME = "name"


@dataclass(frozen=True, slots=True)
class WatchFilters:
    """How to list the watches of an owner: what to keep, and in which order."""

    search: str | None = None
    active: bool | None = None
    # Created from (included) to (excluded).
    created_from: datetime | None = None
    created_to: datetime | None = None
    sort: WatchSort = WatchSort.CREATED
    descending: bool = True


class WatchRepository(Protocol):
    async def add(self, watch: Watch) -> None: ...

    async def get(self, watch_id: str) -> Watch | None: ...

    async def save(self, watch: Watch) -> None: ...

    async def delete(self, watch_id: str) -> None: ...

    async def slug_exists(self, owner_id: str, slug: str, *, excluding: str | None = None) -> bool: ...

    async def list_for_owner(
        self, owner_id: str, params: PageParams, filters: WatchFilters = WatchFilters()
    ) -> Page[Watch]: ...

    async def list_active(self) -> Sequence[Watch]: ...

    async def deactivate_for_owner(self, owner_id: str, now: datetime) -> int:
        """Pause every watch of an owner; return how many were active."""
