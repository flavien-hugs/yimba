from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import Boolean, Float, Integer, String, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from yimba.infrastructure.db import Base, JSONType, UTCDateTime
from yimba.modules.watches.domain.model import AlertThreshold, Frequency, Watch
from yimba.shared.pagination import Page, PageParams
from yimba.shared.source import SourceKind


class WatchRow(Base):
    __tablename__ = "watches"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200))
    keywords: Mapped[list] = mapped_column(JSONType)
    sources: Mapped[list] = mapped_column(JSONType)
    languages: Mapped[list] = mapped_column(JSONType)
    countries: Mapped[list] = mapped_column(JSONType)
    frequency_minutes: Mapped[int] = mapped_column(Integer)
    alert_negative_share: Mapped[float] = mapped_column(Float)
    alert_min_mentions: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


def _to_domain(row: WatchRow) -> Watch:
    return Watch(
        id=row.id,
        owner_id=row.owner_id,
        name=row.name,
        slug=row.slug,
        keywords=tuple(row.keywords),
        sources=tuple(SourceKind(value) for value in row.sources),
        languages=tuple(row.languages),
        countries=tuple(row.countries),
        frequency=Frequency(row.frequency_minutes),
        threshold=AlertThreshold(row.alert_negative_share, row.alert_min_mentions),
        active=row.active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _apply(row: WatchRow, watch: Watch) -> None:
    row.owner_id = watch.owner_id
    row.name = watch.name
    row.slug = watch.slug
    row.keywords = list(watch.keywords)
    row.sources = [source.value for source in watch.sources]
    row.languages = list(watch.languages)
    row.countries = list(watch.countries)
    row.frequency_minutes = watch.frequency.minutes
    row.alert_negative_share = watch.threshold.negative_share
    row.alert_min_mentions = watch.threshold.min_mentions
    row.active = watch.active
    row.updated_at = watch.updated_at


class SqlWatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, watch: Watch) -> None:
        row = WatchRow(id=watch.id, created_at=watch.created_at)
        _apply(row, watch)
        self._session.add(row)
        await self._session.commit()

    async def get(self, watch_id: str) -> Watch | None:
        row = await self._session.get(WatchRow, watch_id)
        return _to_domain(row) if row else None

    async def save(self, watch: Watch) -> None:
        row = await self._session.get(WatchRow, watch.id)
        if row is None:
            raise LookupError(watch.id)
        _apply(row, watch)
        await self._session.commit()

    async def delete(self, watch_id: str) -> None:
        await self._session.execute(delete(WatchRow).where(WatchRow.id == watch_id))
        await self._session.commit()

    async def slug_exists(self, owner_id: str, slug: str, *, excluding: str | None = None) -> bool:
        query = select(func.count()).select_from(WatchRow).where(WatchRow.owner_id == owner_id, WatchRow.slug == slug)
        if excluding:
            query = query.where(WatchRow.id != excluding)
        return (await self._session.scalar(query) or 0) > 0

    async def list_for_owner(self, owner_id: str, params: PageParams, search: str | None = None) -> Page[Watch]:
        filters = [WatchRow.owner_id == owner_id]
        if search:
            filters.append(WatchRow.name.ilike(f"%{search}%"))
        total = await self._session.scalar(select(func.count()).select_from(WatchRow).where(*filters)) or 0
        rows = await self._session.scalars(
            select(WatchRow)
            .where(*filters)
            .order_by(WatchRow.created_at.desc(), WatchRow.id)
            .offset(params.offset)
            .limit(params.size)
        )
        return Page(items=tuple(_to_domain(row) for row in rows), total=total, page=params.page, size=params.size)

    async def list_active(self) -> Sequence[Watch]:
        rows = await self._session.scalars(select(WatchRow).where(WatchRow.active.is_(True)))
        return tuple(_to_domain(row) for row in rows)
