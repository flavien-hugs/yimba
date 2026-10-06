from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from yimba.shared.source import SourceKind

# A run that has been "running" for longer than this is considered dead (worker crash) and may be retried.
STALE_RUN_AFTER = timedelta(minutes=30)


@dataclass(frozen=True, slots=True)
class CollectedItem:
    """A publication as read from a source, already mapped to our vocabulary."""

    source: SourceKind
    external_id: str
    text: str
    author_handle: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    likes: int = 0
    shares: int = 0
    views: int = 0
    comments: int = 0


@dataclass(frozen=True, slots=True)
class CollectionTarget:
    watch_id: str
    source: SourceKind
    keywords: tuple[str, ...]
    languages: tuple[str, ...]
    countries: tuple[str, ...]
    limit: int = 50


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(slots=True)
class CollectionRun:
    id: str
    watch_id: str
    source: SourceKind
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    fetched: int = 0
    stored: int = 0
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def succeed(self, *, at: datetime, fetched: int, stored: int) -> None:
        self.status, self.finished_at, self.fetched, self.stored = RunStatus.SUCCEEDED, at, fetched, stored

    def fail(self, *, at: datetime, error: str) -> None:
        self.status, self.finished_at, self.error = RunStatus.FAILED, at, error[:1000]


def is_due(last_run: CollectionRun | None, frequency_minutes: int, now: datetime) -> bool:
    """Should this (watch, source) be collected now?"""
    if last_run is None:
        return True
    if last_run.status is RunStatus.RUNNING:
        return now - last_run.started_at >= STALE_RUN_AFTER
    return now - last_run.started_at >= timedelta(minutes=frequency_minutes)
