from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from yimba.modules.watches.application.ports import WatchRepository
from yimba.modules.watches.domain.model import AlertThreshold, Frequency, Watch
from yimba.shared.clock import Clock
from yimba.shared.errors import Conflict, NotFound
from yimba.shared.pagination import Page, PageParams
from yimba.shared.source import SourceKind


@dataclass(frozen=True, slots=True)
class CreateWatchCommand:
    owner_id: str
    name: str
    keywords: Sequence[str]
    sources: Sequence[SourceKind]
    languages: Sequence[str] = ("fr",)
    countries: Sequence[str] = ("CI",)
    frequency_minutes: int = 60
    alert_negative_share: float = 0.4
    alert_min_mentions: int = 20


@dataclass(frozen=True, slots=True)
class UpdateWatchCommand:
    owner_id: str
    watch_id: str
    name: str | None = None
    keywords: Sequence[str] | None = None
    sources: Sequence[SourceKind] | None = None
    languages: Sequence[str] | None = None
    countries: Sequence[str] | None = None
    frequency_minutes: int | None = None
    alert_negative_share: float | None = None
    alert_min_mentions: int | None = None
    active: bool | None = None


async def _owned(repository: WatchRepository, owner_id: str, watch_id: str) -> Watch:
    watch = await repository.get(watch_id)
    if watch is None or watch.owner_id != owner_id:
        # Same answer for "missing" and "someone else's": do not leak existence.
        raise NotFound(f"Watch {watch_id} not found", code="watch/not-found")
    return watch


class CreateWatch:
    def __init__(self, repository: WatchRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def execute(self, command: CreateWatchCommand) -> Watch:
        watch = Watch.create(
            owner_id=command.owner_id,
            name=command.name,
            keywords=command.keywords,
            sources=command.sources,
            languages=command.languages,
            countries=command.countries,
            frequency=Frequency(command.frequency_minutes),
            threshold=AlertThreshold(command.alert_negative_share, command.alert_min_mentions),
            now=self._clock.now(),
        )
        if await self._repository.slug_exists(watch.owner_id, watch.slug):
            raise Conflict(f"A watch named '{watch.name}' already exists", code="watch/already-exists")
        await self._repository.add(watch)
        return watch


class GetWatch:
    def __init__(self, repository: WatchRepository) -> None:
        self._repository = repository

    async def execute(self, owner_id: str, watch_id: str) -> Watch:
        return await _owned(self._repository, owner_id, watch_id)


class ListWatches:
    def __init__(self, repository: WatchRepository) -> None:
        self._repository = repository

    async def execute(self, owner_id: str, params: PageParams, search: str | None = None) -> Page[Watch]:
        return await self._repository.list_for_owner(owner_id, params, search)


class UpdateWatch:
    def __init__(self, repository: WatchRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def execute(self, command: UpdateWatchCommand) -> Watch:
        watch = await _owned(self._repository, command.owner_id, command.watch_id)
        threshold = None
        if command.alert_negative_share is not None or command.alert_min_mentions is not None:
            threshold = AlertThreshold(
                (
                    command.alert_negative_share
                    if command.alert_negative_share is not None
                    else watch.threshold.negative_share
                ),
                command.alert_min_mentions if command.alert_min_mentions is not None else watch.threshold.min_mentions,
            )
        watch.revise(
            now=self._clock.now(),
            name=command.name,
            keywords=command.keywords,
            sources=command.sources,
            languages=command.languages,
            countries=command.countries,
            frequency=Frequency(command.frequency_minutes) if command.frequency_minutes is not None else None,
            threshold=threshold,
            active=command.active,
        )
        if command.name is not None and await self._repository.slug_exists(
            watch.owner_id, watch.slug, excluding=watch.id
        ):
            raise Conflict(f"A watch named '{watch.name}' already exists", code="watch/already-exists")
        await self._repository.save(watch)
        return watch


class PauseOwnerWatches:
    """When an account is deleted, its watches stop being collected (they stay, paused, with their data)."""

    def __init__(self, repository: WatchRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def execute(self, owner_id: str) -> int:
        return await self._repository.deactivate_for_owner(owner_id, self._clock.now())


class DeleteWatch:
    def __init__(self, repository: WatchRepository) -> None:
        self._repository = repository

    async def execute(self, owner_id: str, watch_id: str) -> None:
        await _owned(self._repository, owner_id, watch_id)
        await self._repository.delete(watch_id)
