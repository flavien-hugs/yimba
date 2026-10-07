from __future__ import annotations

from datetime import datetime

from yimba.modules.alerts.application.ports import WindowCounts
from yimba.modules.mentions.public import SentimentWindowReader


class MentionsSentimentWindow:
    def __init__(self, reader: SentimentWindowReader) -> None:
        self._reader = reader

    async def counts(self, watch_id: str, start: datetime, end: datetime) -> WindowCounts:
        counts = await self._reader.counts(watch_id, start, end)
        return WindowCounts(total=counts.total, negative=counts.negative)
