from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum, unique
from typing import Iterable

from yimba.shared.errors import Forbidden, InvalidInput
from yimba.shared.ids import new_id


@unique
class Permission(StrEnum):
    """Permission codes checked on every route (also declared in appdesc.yml for the legacy auth service)."""

    WATCH_CREATE = "watch:can-create"
    WATCH_READ = "watch:can-read"
    WATCH_UPDATE = "watch:can-update"
    WATCH_DELETE = "watch:can-delete"
    MENTION_READ = "mention:can-read"
    STATISTICS_READ = "mention:can-read-statistics"
    ALERT_READ = "alert:can-read"
    ALERT_ACKNOWLEDGE = "alert:can-acknowledge"
    USER_READ = "user:can-read"
    USER_MANAGE = "user:can-manage"


@unique
class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"


_USER_PERMISSIONS = frozenset(
    {
        Permission.WATCH_CREATE,
        Permission.WATCH_READ,
        Permission.WATCH_UPDATE,
        Permission.WATCH_DELETE,
        Permission.MENTION_READ,
        Permission.STATISTICS_READ,
        Permission.ALERT_READ,
        Permission.ALERT_ACKNOWLEDGE,
    }
)
# Each user manages their own watches; an admin also manages the accounts (not other people's watches).
ROLE_PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.USER: _USER_PERMISSIONS,
    Role.ADMIN: _USER_PERMISSIONS | {Permission.USER_READ, Permission.USER_MANAGE},
}


@dataclass(frozen=True, slots=True)
class Principal:
    """Who is calling. ``permissions`` is ``None`` when only the remote auth service knows them."""

    id: str
    email: str | None = None
    role: str | None = None
    permissions: frozenset[str] | None = None

    def require(self, permissions: Iterable[str]) -> None:
        missing = set(permissions) - (self.permissions or frozenset())
        if missing:
            raise Forbidden("Missing permission", code="identity/forbidden")


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$|^[^@\s]+@localhost$")
PASSWORD_LENGTH_FLOOR = 8
PASSWORD_LENGTH_CEILING = 1024


def normalize_email(email: str) -> str:
    cleaned = email.strip().lower()
    if len(cleaned) > 254 or not _EMAIL.match(cleaned):
        raise InvalidInput("invalid email address", code="identity/invalid-email")
    return cleaned


@dataclass(frozen=True, slots=True)
class PasswordPolicy:
    """Length is what makes a password strong: any characters, between ``min_length`` and ``max_length``."""

    min_length: int = 10
    max_length: int = 128

    def __post_init__(self) -> None:
        if not PASSWORD_LENGTH_FLOOR <= self.min_length <= self.max_length <= PASSWORD_LENGTH_CEILING:
            raise ValueError(
                f"password lengths must satisfy {PASSWORD_LENGTH_FLOOR} <= min <= max <= {PASSWORD_LENGTH_CEILING}"
            )

    def check(self, password: str) -> None:
        if not self.min_length <= len(password) <= self.max_length:
            raise InvalidInput(
                f"the password must have between {self.min_length} and {self.max_length} characters",
                code="identity/weak-password",
            )


@dataclass(slots=True)
class User:
    id: str
    email: str
    password_hash: str
    role: Role
    active: bool
    created_at: datetime
    full_name: str | None = None
    # Incremented when the password changes: access tokens carry it, so older ones stop working at once.
    token_version: int = 0
    failed_logins: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    # Soft delete: the row and its history stay, the account is gone for every other purpose.
    deleted_at: datetime | None = None
    updated_at: datetime = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.updated_at is None:
            self.updated_at = self.created_at

    @classmethod
    def register(
        cls, *, email: str, password_hash: str, now: datetime, role: Role = Role.USER, full_name: str | None = None
    ) -> "User":
        name = " ".join((full_name or "").split()) or None
        return cls(
            id=new_id(),
            email=normalize_email(email),
            password_hash=password_hash,
            role=role,
            active=True,
            created_at=now,
            full_name=name[:200] if name else None,
        )

    @property
    def permissions(self) -> frozenset[str]:
        return ROLE_PERMISSIONS[self.role]

    def principal(self) -> Principal:
        return Principal(id=self.id, email=self.email, role=self.role.value, permissions=self.permissions)

    def is_locked(self, now: datetime) -> bool:
        return self.locked_until is not None and now < self.locked_until

    def record_failed_login(self, now: datetime, *, max_failures: int, lock_for: timedelta) -> None:
        self.failed_logins += 1
        if self.failed_logins >= max_failures:
            self.locked_until = now + lock_for
            self.failed_logins = 0
        self.updated_at = now

    def record_login(self, now: datetime) -> None:
        self.failed_logins = 0
        self.locked_until = None
        self.last_login_at = now
        self.updated_at = now

    def change_password(self, password_hash: str, now: datetime) -> None:
        self.password_hash = password_hash
        self.token_version += 1
        self.updated_at = now

    def update(self, now: datetime, *, role: Role | None = None, active: bool | None = None) -> None:
        if role is not None:
            self.role = role
        if active is not None:
            self.active = active
        self.updated_at = now

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def delete(self, now: datetime) -> None:
        """Soft delete: disabled, its tokens invalid at once; its email may be used by a new account."""
        self.deleted_at = now
        self.active = False
        self.token_version += 1
        self.updated_at = now


@dataclass(slots=True)
class RefreshToken:
    """One link of a rotation chain: every refresh replaces the token, the chain (family) shares one id.

    Presenting a token that was already replaced means it was stolen and replayed: the whole family is revoked.
    """

    id: str
    user_id: str
    token_hash: str
    family_id: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    replaced_by: str | None = None

    def is_usable(self, now: datetime) -> bool:
        return self.revoked_at is None and now < self.expires_at
