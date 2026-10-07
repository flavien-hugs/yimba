from __future__ import annotations

from typing import Protocol, Sequence

from yimba.modules.identity.domain.model import Principal


class AccessControl(Protocol):
    async def authenticate(self, token: str) -> Principal:
        """Return the caller or raise ``Unauthorized``."""

    async def authorize(self, token: str, permissions: Sequence[str]) -> None:
        """Raise ``Forbidden`` unless the token's owner holds every permission."""
