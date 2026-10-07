from __future__ import annotations

from yimba.modules.alerts.application.ports import AlertRule
from yimba.modules.watches.public import WatchDirectory


class DirectoryAlertRules:
    def __init__(self, directory: WatchDirectory) -> None:
        self._directory = directory

    async def get(self, watch_id: str) -> AlertRule | None:
        watch = await self._directory.get(watch_id)
        if watch is None or not watch.active:
            return None
        return AlertRule(
            watch_id=watch.id,
            watch_name=watch.name,
            negative_share=watch.alert_negative_share,
            min_mentions=watch.alert_min_mentions,
        )
