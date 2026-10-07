from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AlertStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"


@dataclass(slots=True)
class Alert:
    id: str
    watch_id: str
    window_start: datetime
    window_end: datetime
    mentions: int
    negative: int
    negative_share: float
    threshold_share: float
    triggered_at: datetime
    status: AlertStatus = AlertStatus.OPEN
    acknowledged_at: datetime | None = None

    @property
    def message(self) -> str:
        return (
            f"{self.negative_share:.0%} of {self.mentions} mentions are negative "
            f"(threshold {self.threshold_share:.0%})"
        )

    def acknowledge(self, at: datetime) -> None:
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = at


def should_alert(*, mentions: int, negative: int, threshold_share: float, min_mentions: int) -> bool:
    """Too few mentions say nothing about opinion: wait for a meaningful sample."""
    return mentions >= min_mentions and mentions > 0 and negative / mentions >= threshold_share
