from __future__ import annotations

import logging

from yimba.modules.alerts.application.ports import AlertRule
from yimba.modules.alerts.domain.model import Alert

logger = logging.getLogger(__name__)


class LogNotifier:
    """Default notifier: writes the alert to the logs. Email / WhatsApp notifiers implement the same port."""

    async def notify(self, alert: Alert, rule: AlertRule) -> None:
        logger.warning("ALERT watch=%s (%s): %s", rule.watch_name, alert.watch_id, alert.message)
