from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from yimba.modules.analysis.public import TextAnalyzer
from yimba.modules.mentions.application.ports import GroupBy, MentionFilters, MentionRepository, Stats
from yimba.modules.mentions.domain.model import Mention, Metrics, anonymize_author, content_hash
from yimba.shared.clock import Clock
from yimba.shared.ids import new_id
from yimba.shared.pagination import Page, PageParams
from yimba.shared.source import SourceKind


@dataclass(frozen=True, slots=True)
class IncomingMention:
    """A publication as delivered by a collector, before normalization and analysis."""

    source: SourceKind
    external_id: str
    text: str
    author_handle: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    metrics: Metrics = Metrics()


@dataclass(frozen=True, slots=True)
class IngestSummary:
    received: int = 0
    skipped: int = 0
    duplicates: int = 0
    stored: int = 0


class IngestMentions:
    def __init__(self, repository: MentionRepository, analyzer: TextAnalyzer, clock: Clock, author_salt: str) -> None:
        self._repository = repository
        self._analyzer = analyzer
        self._clock = clock
        self._salt = author_salt

    async def execute(self, watch_id: str, items: Sequence[IncomingMention]) -> IngestSummary:
        now = self._clock.now()
        prepared: dict[tuple[str, str], Mention] = {}
        seen_hashes: set[str] = set()
        skipped = 0

        for item in items:
            text = (item.text or "").strip()
            if not text or not item.external_id:
                skipped += 1
                continue
            fingerprint = content_hash(text)
            key = (item.source.value, item.external_id)
            if key in prepared or fingerprint in seen_hashes:
                continue
            analysis = self._analyzer.analyze(text)
            prepared[key] = Mention(
                id=new_id(),
                watch_id=watch_id,
                source=item.source,
                external_id=item.external_id,
                text=text,
                content_hash=fingerprint,
                author_ref=anonymize_author(item.author_handle, self._salt),
                url=item.url,
                published_at=item.published_at or now,
                collected_at=now,
                metrics=item.metrics,
                language=analysis.language,
                sentiment=analysis.sentiment,
                emotion=analysis.emotion,
            )
            seen_hashes.add(fingerprint)

        stored = await self._repository.add_new(list(prepared.values())) if prepared else 0
        in_batch_duplicates = len(items) - skipped - len(prepared)
        return IngestSummary(
            received=len(items),
            skipped=skipped,
            duplicates=in_batch_duplicates + (len(prepared) - stored),
            stored=stored,
        )


class SearchMentions:
    def __init__(self, repository: MentionRepository) -> None:
        self._repository = repository

    async def execute(self, filters: MentionFilters, params: PageParams) -> Page[Mention]:
        return await self._repository.search(filters, params)


class ComputeStats:
    def __init__(self, repository: MentionRepository) -> None:
        self._repository = repository

    async def execute(self, filters: MentionFilters, group_by: GroupBy = GroupBy.DAY) -> Stats:
        return await self._repository.stats(filters, group_by)
