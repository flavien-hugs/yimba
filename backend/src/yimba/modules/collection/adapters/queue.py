from __future__ import annotations

from typing import Callable

from yimba.shared.source import SourceKind


class TaskQueue:
    """Enqueues collections through any ``send_task(name, args)`` callable (Celery's ``send_task`` in production)."""

    COLLECT_TASK = "yimba.collect"

    def __init__(self, send_task: Callable[..., object]) -> None:
        self._send_task = send_task

    async def enqueue_collection(self, watch_id: str, source: SourceKind) -> None:
        self._send_task(self.COLLECT_TASK, args=[watch_id, source.value])
