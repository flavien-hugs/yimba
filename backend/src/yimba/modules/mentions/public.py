"""The only import surface other modules may use."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from yimba.modules.analysis.public import TextAnalyzer
from yimba.modules.mentions.adapters.persistence import SqlMentionRepository
from yimba.modules.mentions.application.ports import Counts, MentionFilters
from yimba.modules.mentions.application.use_cases import ComputeStats, IncomingMention, IngestMentions, IngestSummary
from yimba.modules.mentions.domain.model import Metrics
from yimba.shared.clock import Clock


class MentionIngestor(Protocol):
    async def ingest(self, watch_id: str, items: Sequence[IncomingMention]) -> IngestSummary: ...


class SentimentWindowReader(Protocol):
    async def counts(self, watch_id: str, start: datetime, end: datetime) -> Counts: ...


class _Ingestor:
    def __init__(self, use_case: IngestMentions) -> None:
        self._use_case = use_case

    async def ingest(self, watch_id: str, items: Sequence[IncomingMention]) -> IngestSummary:
        return await self._use_case.execute(watch_id, items)


class _WindowReader:
    def __init__(self, use_case: ComputeStats) -> None:
        self._use_case = use_case

    async def counts(self, watch_id: str, start: datetime, end: datetime) -> Counts:
        stats = await self._use_case.execute(MentionFilters(watch_id=watch_id, start=start, end=end))
        return stats.totals


def build_mention_ingestor(
    session: AsyncSession, analyzer: TextAnalyzer, clock: Clock, author_salt: str
) -> MentionIngestor:
    return _Ingestor(IngestMentions(SqlMentionRepository(session), analyzer, clock, author_salt))


def build_sentiment_window_reader(session: AsyncSession) -> SentimentWindowReader:
    return _WindowReader(ComputeStats(SqlMentionRepository(session)))


__all__ = [
    "Counts",
    "IncomingMention",
    "IngestSummary",
    "MentionIngestor",
    "Metrics",
    "SentimentWindowReader",
    "build_mention_ingestor",
    "build_sentiment_window_reader",
]
