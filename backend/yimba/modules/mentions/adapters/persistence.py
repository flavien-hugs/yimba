from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import Float, Integer, String, Text, UniqueConstraint, case, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from yimba.infrastructure.db import Base, UTCDateTime
from yimba.modules.analysis.public import Emotion, Sentiment, SentimentLabel
from yimba.modules.mentions.application.ports import Bucket, Counts, GroupBy, MentionFilters, Stats
from yimba.modules.mentions.domain.model import Mention, Metrics
from yimba.shared.pagination import Page, PageParams
from yimba.shared.source import SourceKind


class MentionRow(Base):
    __tablename__ = "mentions"
    __table_args__ = (
        UniqueConstraint("watch_id", "source", "external_id", name="uq_mentions_source_item"),
        UniqueConstraint("watch_id", "content_hash", name="uq_mentions_content"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    watch_id: Mapped[str] = mapped_column(String(32), index=True)
    source: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(255))
    content_hash: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    author_ref: Mapped[str | None] = mapped_column(String(32), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    collected_at: Mapped[datetime] = mapped_column(UTCDateTime)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    views: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str] = mapped_column(String(8))
    sentiment_positive: Mapped[float] = mapped_column(Float)
    sentiment_neutral: Mapped[float] = mapped_column(Float)
    sentiment_negative: Mapped[float] = mapped_column(Float)
    sentiment_label: Mapped[str] = mapped_column(String(10), index=True)
    emotion: Mapped[str | None] = mapped_column(String(10), nullable=True)
    venue: Mapped[str | None] = mapped_column(String(200), nullable=True)


def _row(mention: Mention) -> MentionRow:
    return MentionRow(
        id=mention.id,
        watch_id=mention.watch_id,
        source=mention.source.value,
        external_id=mention.external_id,
        content_hash=mention.content_hash,
        text=mention.text,
        author_ref=mention.author_ref,
        url=mention.url,
        published_at=mention.published_at,
        collected_at=mention.collected_at,
        likes=mention.metrics.likes,
        shares=mention.metrics.shares,
        views=mention.metrics.views,
        comments=mention.metrics.comments,
        language=mention.language,
        sentiment_positive=mention.sentiment.positive,
        sentiment_neutral=mention.sentiment.neutral,
        sentiment_negative=mention.sentiment.negative,
        sentiment_label=mention.sentiment.label.value,
        emotion=mention.emotion.value if mention.emotion else None,
        venue=mention.venue,
    )


def _to_domain(row: MentionRow) -> Mention:
    pos, neg = row.sentiment_positive, row.sentiment_negative
    return Mention(
        id=row.id,
        watch_id=row.watch_id,
        source=SourceKind(row.source),
        external_id=row.external_id,
        text=row.text,
        content_hash=row.content_hash,
        author_ref=row.author_ref,
        url=row.url,
        published_at=row.published_at,
        collected_at=row.collected_at,
        metrics=Metrics(row.likes, row.shares, row.views, row.comments),
        language=row.language,
        sentiment=Sentiment(positive=pos, neutral=max(0.0, 1.0 - pos - neg), negative=neg),
        emotion=Emotion(row.emotion) if row.emotion else None,
        venue=row.venue,
    )


def _where(filters: MentionFilters) -> list:
    clauses = [MentionRow.watch_id == filters.watch_id]
    if filters.source:
        clauses.append(MentionRow.source == filters.source.value)
    if filters.language:
        clauses.append(MentionRow.language == filters.language)
    if filters.sentiment:
        clauses.append(MentionRow.sentiment_label == filters.sentiment.value)
    if filters.emotion:
        clauses.append(MentionRow.emotion == filters.emotion.value)
    if filters.start:
        clauses.append(MentionRow.published_at >= filters.start)
    if filters.end:
        clauses.append(MentionRow.published_at < filters.end)
    if filters.query:
        clauses.append(MentionRow.text.ilike(f"%{filters.query}%"))
    return clauses


class SqlMentionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_new(self, mentions: Sequence[Mention]) -> int:
        if not mentions:
            return 0
        watch_id = mentions[0].watch_id
        known = await self._session.execute(
            select(MentionRow.source, MentionRow.external_id, MentionRow.content_hash).where(
                MentionRow.watch_id == watch_id,
                or_(
                    MentionRow.external_id.in_([m.external_id for m in mentions]),
                    MentionRow.content_hash.in_([m.content_hash for m in mentions]),
                ),
            )
        )
        known_keys, known_hashes = set(), set()
        for source, external_id, digest in known:
            known_keys.add((source, external_id))
            known_hashes.add(digest)
        fresh = [
            m
            for m in mentions
            if (m.source.value, m.external_id) not in known_keys and m.content_hash not in known_hashes
        ]
        if not fresh:
            return 0

        try:
            self._session.add_all([_row(m) for m in fresh])
            await self._session.commit()
            return len(fresh)
        except IntegrityError:
            # A concurrent collector inserted the same item between our check and our insert.
            await self._session.rollback()
        except SQLAlchemyError:
            # Leave the session usable: the caller still has to record the failed run.
            await self._session.rollback()
            raise
        stored = 0
        for mention in fresh:
            try:
                async with self._session.begin_nested():
                    self._session.add(_row(mention))
                stored += 1
            except IntegrityError:
                continue
        await self._session.commit()
        return stored

    async def search(self, filters: MentionFilters, params: PageParams) -> Page[Mention]:
        clauses = _where(filters)
        total = await self._session.scalar(select(func.count()).select_from(MentionRow).where(*clauses)) or 0
        rows = await self._session.scalars(
            select(MentionRow)
            .where(*clauses)
            .order_by(MentionRow.published_at.desc(), MentionRow.id)
            .offset(params.offset)
            .limit(params.size)
        )
        return Page(items=tuple(_to_domain(r) for r in rows), total=total, page=params.page, size=params.size)

    async def sample(self, filters: MentionFilters, size: int) -> Sequence[Mention]:
        rows = await self._session.scalars(
            select(MentionRow).where(*_where(filters)).order_by(func.random()).limit(size)
        )
        return tuple(_to_domain(row) for row in rows)

    def _bucket(self, group_by: GroupBy):
        if group_by is GroupBy.SOURCE:
            return MentionRow.source
        if group_by is GroupBy.LANGUAGE:
            return MentionRow.language
        if self._session.bind.dialect.name == "sqlite":
            return func.strftime("%Y-%m-%d", MentionRow.published_at)
        return func.to_char(func.timezone("UTC", MentionRow.published_at), "YYYY-MM-DD")

    async def texts(self, filters: MentionFilters, limit: int) -> Sequence[tuple[str, SentimentLabel]]:
        rows = await self._session.execute(
            select(MentionRow.text, MentionRow.sentiment_label)
            .where(*_where(filters))
            .order_by(MentionRow.published_at.desc(), MentionRow.id)
            .limit(limit)
        )
        return [(text, SentimentLabel(label)) for text, label in rows]

    async def stats(self, filters: MentionFilters, group_by: GroupBy) -> Stats:
        clauses = _where(filters)

        def count_of(label: SentimentLabel):
            return func.coalesce(func.sum(case((MentionRow.sentiment_label == label.value, 1), else_=0)), 0)

        columns = (
            func.count(MentionRow.id),
            count_of(SentimentLabel.POSITIVE),
            count_of(SentimentLabel.NEUTRAL),
            count_of(SentimentLabel.NEGATIVE),
        )
        total_row = (await self._session.execute(select(*columns).where(*clauses))).one()
        totals = Counts(*(int(v) for v in total_row))

        bucket = self._bucket(group_by).label("bucket")
        bucket_rows = await self._session.execute(
            select(bucket, *columns).where(*clauses).group_by(bucket).order_by(bucket)
        )
        buckets = tuple(Bucket(key=str(row[0]), counts=Counts(*(int(v) for v in row[1:]))) for row in bucket_rows)

        emotion_rows = await self._session.execute(
            select(MentionRow.emotion, func.count(MentionRow.id))
            .where(*clauses, MentionRow.emotion.is_not(None))
            .group_by(MentionRow.emotion)
        )
        return Stats(totals=totals, buckets=buckets, emotions={str(e): int(c) for e, c in emotion_rows})
