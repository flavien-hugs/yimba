from datetime import timedelta

import pytest

from tests.conftest import NOW
from yimba.modules.alerts.adapters.persistence import SqlAlertRepository
from yimba.modules.alerts.application.ports import AlertRule, WindowCounts
from yimba.modules.alerts.application.use_cases import AcknowledgeAlert, EvaluateAlerts, ListAlerts
from yimba.modules.alerts.domain.model import AlertStatus, should_alert
from yimba.shared.errors import NotFound
from yimba.shared.pagination import PageParams


class Rules:
    def __init__(self, rule):
        self.rule = rule

    async def get(self, watch_id):
        return self.rule


class Window:
    def __init__(self, total, negative):
        self.total, self.negative, self.asked = total, negative, []

    async def counts(self, watch_id, start, end):
        self.asked.append((start, end))
        return WindowCounts(self.total, self.negative)


class Notifier:
    def __init__(self):
        self.sent = []

    async def notify(self, alert, rule):
        self.sent.append((alert, rule))


RULE = AlertRule("w1", "Santé", negative_share=0.4, min_mentions=20)


@pytest.mark.parametrize(
    ("mentions", "negative", "expected"),
    [(20, 8, True), (20, 7, False), (19, 19, False), (0, 0, False), (100, 100, True)],
)
def test_should_alert(mentions, negative, expected):
    assert should_alert(mentions=mentions, negative=negative, threshold_share=0.4, min_mentions=20) is expected


def evaluator(session, clock, window, notifier, rule=RULE):
    return EvaluateAlerts(Rules(rule), window, SqlAlertRepository(session), notifier, clock)


async def test_alert_is_raised_stored_and_notified(session, clock):
    notifier, window = Notifier(), Window(50, 30)
    alert = await evaluator(session, clock, window, notifier).execute("w1")

    assert alert and alert.negative_share == 0.6 and alert.status is AlertStatus.OPEN
    assert "60% of 50 mentions" in alert.message
    assert window.asked == [(NOW - timedelta(hours=24), NOW)]
    assert notifier.sent == [(alert, RULE)]
    assert (await ListAlerts(SqlAlertRepository(session)).execute("w1", PageParams())).total == 1


async def test_no_alert_below_threshold_or_for_unknown_watch(session, clock):
    notifier = Notifier()
    assert await evaluator(session, clock, Window(50, 5), notifier).execute("w1") is None
    assert await evaluator(session, clock, Window(50, 50), notifier, rule=None).execute("w1") is None
    assert notifier.sent == []


async def test_cooldown_prevents_repeated_alerts_until_it_expires(session, clock):
    notifier, window = Notifier(), Window(50, 30)
    use_case = evaluator(session, clock, window, notifier)
    assert await use_case.execute("w1")
    clock.set(NOW + timedelta(hours=1))
    assert await use_case.execute("w1") is None
    clock.set(NOW + timedelta(hours=7))
    assert await use_case.execute("w1")
    assert len(notifier.sent) == 2


async def test_acknowledge(session, clock):
    alert = await evaluator(session, clock, Window(50, 30), Notifier()).execute("w1")
    repo = SqlAlertRepository(session)
    done = await AcknowledgeAlert(repo, clock).execute("w1", alert.id)
    assert done.status is AlertStatus.ACKNOWLEDGED and done.acknowledged_at == NOW
    assert (await repo.get(alert.id)).status is AlertStatus.ACKNOWLEDGED
    with pytest.raises(NotFound):
        await AcknowledgeAlert(repo, clock).execute("another-watch", alert.id)
    with pytest.raises(NotFound):
        await AcknowledgeAlert(repo, clock).execute("w1", "missing")
