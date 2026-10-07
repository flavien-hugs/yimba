"""Lenient readers for the values found in provider payloads: bad values become ``0`` / ``None``, never errors."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def as_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
