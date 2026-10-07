from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from yimba.modules.analysis.public import SentimentLabel, TextAnalyzer
from yimba.modules.mentions.application.ports import Counts, GroupBy, MentionFilters, MentionRepository, Stats
from yimba.modules.mentions.domain.model import Mention, Metrics, anonymize_author, content_hash, storable_external_id
from yimba.modules.mentions.domain.places import DISTRICTS, districts_in
from yimba.modules.mentions.domain.themes import Theme, top_terms
from yimba.shared.clock import Clock
from yimba.shared.ids import new_id
from yimba.shared.pagination import Page, PageParams
from yimba.shared.source import SourceKind

VENUE_MAX_LENGTH = 200


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
    venue: str | None = None


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
            external_id = storable_external_id(item.external_id)
            key = (item.source.value, external_id)
            if key in prepared or fingerprint in seen_hashes:
                continue
            analysis = self._analyzer.analyze(text)
            prepared[key] = Mention(
                id=new_id(),
                watch_id=watch_id,
                source=item.source,
                external_id=external_id,
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
                venue=" ".join((item.venue or "").split())[:VENUE_MAX_LENGTH] or None,
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


# The analyses of the words read at most this many of the most recent conversations of the period.
TEXT_SAMPLE = 5000


@dataclass(frozen=True, slots=True)
class PlaceCounts:
    district: str
    counts: Counts


@dataclass(frozen=True, slots=True)
class Places:
    districts: Sequence[PlaceCounts]
    located: int
    analyzed: int


class ComputePlaces:
    """Where the conversations come from: those that name a district (or one of its towns), district by district."""

    def __init__(self, repository: MentionRepository) -> None:
        self._repository = repository

    async def execute(self, filters: MentionFilters) -> Places:
        rows = await self._repository.texts(filters, TEXT_SAMPLE)
        tally = {district: Counter[SentimentLabel]() for district in DISTRICTS}
        located = 0
        for text, label in rows:
            named = districts_in(text)
            located += bool(named)
            for district in named:
                tally[district][label] += 1
        districts = [
            PlaceCounts(
                district,
                Counts(
                    total=sum(count.values()),
                    positive=count[SentimentLabel.POSITIVE],
                    neutral=count[SentimentLabel.NEUTRAL],
                    negative=count[SentimentLabel.NEGATIVE],
                ),
            )
            for district, count in tally.items()
        ]
        return Places(districts, located, len(rows))


@dataclass(frozen=True, slots=True)
class Themes:
    themes: Sequence[Theme]
    analyzed: int


class ComputeThemes:
    """What people talk about: the words found in the most conversations, with their sentiment."""

    def __init__(self, repository: MentionRepository) -> None:
        self._repository = repository

    async def execute(self, filters: MentionFilters, keywords: Sequence[str] = (), limit: int = 6) -> Themes:
        rows = await self._repository.texts(filters, TEXT_SAMPLE)
        return Themes(top_terms(rows, exclude=keywords, limit=limit), len(rows))
