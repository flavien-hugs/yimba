from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import Integer, String, Text, UniqueConstraint, delete, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from yimba.infrastructure.db import Base, JSONType, UTCDateTime
from yimba.modules.collection.domain.model import CollectedItem, CollectionRun, RunStatus
from yimba.shared.ids import new_id
from yimba.shared.source import SourceKind

_UPSERT_BATCH = 500


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


class RawItemRow(Base):
    """Landing zone: the provider payload of each item, as last seen."""

    __tablename__ = "raw_items"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_raw_items_source_item"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONType)
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    last_run_id: Mapped[str] = mapped_column(String(32))


class SqlRawArchive:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def keep(self, run_id: str, items: Sequence[CollectedItem], seen_at: datetime) -> int:
        # Keyed by (source, external_id): one INSERT may not touch the same row twice.
        rows = {
            (item.source.value, item.external_id): {
                "id": new_id(),
                "source": item.source.value,
                "external_id": item.external_id,
                "payload": dict(item.raw),
                "first_seen_at": seen_at,
                "last_seen_at": seen_at,
                "last_run_id": run_id,
            }
            for item in items
            if item.raw is not None and item.external_id
        }
        values = list(rows.values())
        insert = postgresql.insert if self._session.bind.dialect.name == "postgresql" else sqlite.insert
        for start in range(0, len(values), _UPSERT_BATCH):
            statement = insert(RawItemRow).values(values[start : start + _UPSERT_BATCH])
            statement = statement.on_conflict_do_update(
                index_elements=["source", "external_id"],
                set_={
                    "payload": statement.excluded.payload,
                    "last_seen_at": statement.excluded.last_seen_at,
                    "last_run_id": statement.excluded.last_run_id,
                },
            )
            await self._session.execute(statement)
        await self._session.commit()
        return len(values)

    async def purge(self, not_seen_since: datetime) -> int:
        result = await self._session.execute(delete(RawItemRow).where(RawItemRow.last_seen_at < not_seen_since))
        await self._session.commit()
        return result.rowcount or 0
