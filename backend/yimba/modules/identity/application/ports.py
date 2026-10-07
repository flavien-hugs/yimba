from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence

from yimba.modules.identity.domain.model import Principal, RefreshToken, User
from yimba.shared.pagination import Page, PageParams


class AccessControl(Protocol):
    """What the API depends on, whether the accounts live here or in the legacy auth service."""

    async def authenticate(self, token: str) -> Principal:
        """Return the caller or raise ``Unauthorized``."""

    async def authorize(self, principal: Principal, token: str, permissions: Sequence[str]) -> None:
        """Raise ``Forbidden`` unless the caller holds every permission."""


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...

    async def get(self, user_id: str) -> User | None:
        """Deleted accounts included."""

    async def get_by_email(self, email: str) -> User | None:
        """The live (not deleted) account with this email."""

    async def save(self, user: User) -> None: ...

    async def list(
        self, params: PageParams, search: str | None = None, include_deleted: bool = False
    ) -> Page[User]: ...

    async def count_active_admins(self) -> int: ...


class UserLookup(Protocol):
    """Reads one user outside of any request session (used on every authenticated request)."""

    async def get(self, user_id: str) -> User | None: ...


class RefreshTokenRepository(Protocol):
    async def add(self, token: RefreshToken) -> None: ...

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    async def save(self, token: RefreshToken) -> None: ...

    async def revoke_family(self, family_id: str, at: datetime) -> None: ...

    async def revoke_all_for_user(self, user_id: str, at: datetime) -> None: ...

    async def purge(self, now: datetime) -> int:
        """Delete expired tokens (revoked ones are kept until they expire, to detect replays)."""


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...

    def needs_rehash(self, password_hash: str) -> bool: ...

    def verify_dummy(self, password: str) -> None:
        """Spend the time of a real check, so that unknown emails cannot be told apart by timing."""


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: str
    token_version: int


class AccessTokens(Protocol):
    """Short-lived signed access tokens."""

    @property
    def lifetime_seconds(self) -> int: ...

    def issue(self, user: User, now: datetime) -> str: ...

    def read(self, token: str, now: datetime) -> AccessClaims:
        """Return the claims of a valid, unexpired token or raise ``Unauthorized``."""


class SecretGenerator(Protocol):
    """Opaque refresh tokens: a random secret handed to the client, and the digest kept in the database."""

    def new(self) -> str: ...

    def digest(self, secret: str) -> str: ...
