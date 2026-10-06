from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from yimba.infrastructure.db import Base, UTCDateTime
from yimba.modules.collection.domain.model import CollectionRun, RunStatus
from yimba.shared.source import SourceKind


class CollectionRunRow(Base):
    __tablename__ = "collection_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    watch_id: Mapped[str] = mapped_column(String(32), index=True)
    source: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(12))
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    fetched: Mapped[int] = mapped_column(Integer, default=0)
    stored: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


def _to_domain(row: CollectionRunRow) -> CollectionRun:
    return CollectionRun(
        id=row.id,
        watch_id=row.watch_id,
        source=SourceKind(row.source),
        status=RunStatus(row.status),
        started_at=row.started_at,
        finished_at=row.finished_at,
        fetched=row.fetched,
        stored=row.stored,
        error=row.error,
    )


class SqlRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def last_run(self, watch_id: str, source: SourceKind) -> CollectionRun | None:
        row = await self._session.scalar(
            select(CollectionRunRow)
            .where(CollectionRunRow.watch_id == watch_id, CollectionRunRow.source == source.value)
            .order_by(CollectionRunRow.started_at.desc())
            .limit(1)
        )
        return _to_domain(row) if row else None

    async def save(self, run: CollectionRun) -> None:
        row = await self._session.get(CollectionRunRow, run.id)
        if row is None:
            row = CollectionRunRow(id=run.id, watch_id=run.watch_id, source=run.source.value, started_at=run.started_at)
            self._session.add(row)
        row.status = run.status.value
        row.finished_at = run.finished_at
        row.fetched = run.fetched
        row.stored = run.stored
        row.error = run.error
        await self._session.commit()
