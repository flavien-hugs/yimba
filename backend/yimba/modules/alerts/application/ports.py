from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from yimba.modules.alerts.domain.model import Alert
from yimba.shared.pagination import Page, PageParams


@dataclass(frozen=True, slots=True)
class AlertRule:
    watch_id: str
    watch_name: str
    negative_share: float
    min_mentions: int


@dataclass(frozen=True, slots=True)
class WindowCounts:
    total: int
    negative: int


class AlertRepository(Protocol):
    async def add(self, alert: Alert) -> None: ...

    async def get(self, alert_id: str) -> Alert | None: ...

    async def save(self, alert: Alert) -> None: ...

    async def latest_for_watch(self, watch_id: str) -> Alert | None: ...

    async def list_for_watch(self, watch_id: str, params: PageParams) -> Page[Alert]: ...


class AlertRules(Protocol):
    async def get(self, watch_id: str) -> AlertRule | None: ...


class SentimentWindow(Protocol):
    async def counts(self, watch_id: str, start: datetime, end: datetime) -> WindowCounts: ...


class Notifier(Protocol):
    async def notify(self, alert: Alert, rule: AlertRule) -> None: ...
