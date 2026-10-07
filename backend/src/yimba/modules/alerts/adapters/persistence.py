from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from yimba.infrastructure.db import Base, UTCDateTime
from yimba.modules.alerts.domain.model import Alert, AlertStatus
from yimba.shared.pagination import Page, PageParams


class AlertRow(Base):
    __tablename__ = "watch_alerts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    watch_id: Mapped[str] = mapped_column(String(32), index=True)
    window_start: Mapped[datetime] = mapped_column(UTCDateTime)
    window_end: Mapped[datetime] = mapped_column(UTCDateTime)
    mentions: Mapped[int] = mapped_column(Integer)
    negative: Mapped[int] = mapped_column(Integer)
    negative_share: Mapped[float] = mapped_column(Float)
    threshold_share: Mapped[float] = mapped_column(Float)
    triggered_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    status: Mapped[str] = mapped_column(String(14))
    acknowledged_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


def _to_domain(row: AlertRow) -> Alert:
    return Alert(
        id=row.id,
        watch_id=row.watch_id,
        window_start=row.window_start,
        window_end=row.window_end,
        mentions=row.mentions,
        negative=row.negative,
        negative_share=row.negative_share,
        threshold_share=row.threshold_share,
        triggered_at=row.triggered_at,
        status=AlertStatus(row.status),
        acknowledged_at=row.acknowledged_at,
    )


class SqlAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, alert: Alert) -> None:
        self._session.add(
            AlertRow(
                id=alert.id,
                watch_id=alert.watch_id,
                window_start=alert.window_start,
                window_end=alert.window_end,
                mentions=alert.mentions,
                negative=alert.negative,
                negative_share=alert.negative_share,
                threshold_share=alert.threshold_share,
                triggered_at=alert.triggered_at,
                status=alert.status.value,
                acknowledged_at=alert.acknowledged_at,
            )
        )
        await self._session.commit()

    async def get(self, alert_id: str) -> Alert | None:
        row = await self._session.get(AlertRow, alert_id)
        return _to_domain(row) if row else None

    async def save(self, alert: Alert) -> None:
        row = await self._session.get(AlertRow, alert.id)
        if row is None:
            raise LookupError(alert.id)
        row.status = alert.status.value
        row.acknowledged_at = alert.acknowledged_at
        await self._session.commit()

    async def latest_for_watch(self, watch_id: str) -> Alert | None:
        row = await self._session.scalar(
            select(AlertRow).where(AlertRow.watch_id == watch_id).order_by(AlertRow.triggered_at.desc()).limit(1)
        )
        return _to_domain(row) if row else None

    async def list_for_watch(self, watch_id: str, params: PageParams) -> Page[Alert]:
        total = await self._session.scalar(
            select(func.count()).select_from(AlertRow).where(AlertRow.watch_id == watch_id)
        )
        rows = await self._session.scalars(
            select(AlertRow)
            .where(AlertRow.watch_id == watch_id)
            .order_by(AlertRow.triggered_at.desc())
            .offset(params.offset)
            .limit(params.size)
        )
        return Page(items=tuple(_to_domain(r) for r in rows), total=total or 0, page=params.page, size=params.size)
