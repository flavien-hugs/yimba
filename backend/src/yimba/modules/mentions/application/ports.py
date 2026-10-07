from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol, Sequence

from yimba.modules.analysis.public import Emotion, SentimentLabel
from yimba.modules.mentions.domain.model import Mention
from yimba.shared.pagination import Page, PageParams
from yimba.shared.source import SourceKind


class GroupBy(StrEnum):
    DAY = "day"
    SOURCE = "source"
    LANGUAGE = "language"


@dataclass(frozen=True, slots=True)
class MentionFilters:
    watch_id: str
    source: SourceKind | None = None
    language: str | None = None
    sentiment: SentimentLabel | None = None
    emotion: Emotion | None = None
    start: datetime | None = None
    end: datetime | None = None
    query: str | None = None


@dataclass(frozen=True, slots=True)
class Counts:
    total: int = 0
    positive: int = 0
    neutral: int = 0
    negative: int = 0

    @property
    def negative_share(self) -> float:
        return self.negative / self.total if self.total else 0.0


@dataclass(frozen=True, slots=True)
class Bucket:
    key: str
    counts: Counts


@dataclass(frozen=True, slots=True)
class Stats:
    totals: Counts
    buckets: Sequence[Bucket] = field(default_factory=tuple)
    emotions: dict[str, int] = field(default_factory=dict)


class MentionRepository(Protocol):
    async def add_new(self, mentions: Sequence[Mention]) -> int:
        """Persist the mentions not already known (same source id or same content); return how many were new."""

    async def search(self, filters: MentionFilters, params: PageParams) -> Page[Mention]: ...

    async def stats(self, filters: MentionFilters, group_by: GroupBy) -> Stats: ...

    async def sample(self, filters: MentionFilters, size: int) -> Sequence[Mention]:
        """Random mentions, e.g. to build an annotation corpus."""
