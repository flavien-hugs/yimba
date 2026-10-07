from __future__ import annotations

from datetime import timedelta

from yimba.modules.alerts.application.ports import AlertRepository, AlertRules, Notifier, SentimentWindow
from yimba.modules.alerts.domain.model import Alert, should_alert
from yimba.shared.clock import Clock
from yimba.shared.errors import NotFound
from yimba.shared.ids import new_id
from yimba.shared.pagination import Page, PageParams


class EvaluateAlerts:
    """Look at the last ``window`` of mentions of a watch and raise an alert if it is worrying.

    A ``cooldown`` avoids re-alerting on every collection while the situation persists.
    """

    def __init__(
        self,
        rules: AlertRules,
        window: SentimentWindow,
        alerts: AlertRepository,
        notifier: Notifier,
        clock: Clock,
        window_hours: int = 24,
        cooldown_hours: int = 6,
    ) -> None:
        self._rules = rules
        self._window = window
        self._alerts = alerts
        self._notifier = notifier
        self._clock = clock
        self._window_span = timedelta(hours=window_hours)
        self._cooldown = timedelta(hours=cooldown_hours)

    async def execute(self, watch_id: str) -> Alert | None:
        rule = await self._rules.get(watch_id)
        if rule is None:
            return None
        now = self._clock.now()
        counts = await self._window.counts(watch_id, now - self._window_span, now)
        if not should_alert(
            mentions=counts.total,
            negative=counts.negative,
            threshold_share=rule.negative_share,
            min_mentions=rule.min_mentions,
        ):
            return None
        latest = await self._alerts.latest_for_watch(watch_id)
        if latest is not None and now - latest.triggered_at < self._cooldown:
            return None

        alert = Alert(
            id=new_id(),
            watch_id=watch_id,
            window_start=now - self._window_span,
            window_end=now,
            mentions=counts.total,
            negative=counts.negative,
            negative_share=counts.negative / counts.total,
            threshold_share=rule.negative_share,
            triggered_at=now,
        )
        await self._alerts.add(alert)
        await self._notifier.notify(alert, rule)
        return alert


class ListAlerts:
    def __init__(self, alerts: AlertRepository) -> None:
        self._alerts = alerts

    async def execute(self, watch_id: str, params: PageParams) -> Page[Alert]:
        return await self._alerts.list_for_watch(watch_id, params)


class AcknowledgeAlert:
    def __init__(self, alerts: AlertRepository, clock: Clock) -> None:
        self._alerts = alerts
        self._clock = clock

    async def execute(self, watch_id: str, alert_id: str) -> Alert:
        alert = await self._alerts.get(alert_id)
        if alert is None or alert.watch_id != watch_id:
            raise NotFound(f"Alert {alert_id} not found", code="alert/not-found")
        alert.acknowledge(self._clock.now())
        await self._alerts.save(alert)
        return alert
