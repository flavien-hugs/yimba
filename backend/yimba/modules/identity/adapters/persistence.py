from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from yimba.infrastructure.db import Base, UTCDateTime
from yimba.modules.identity.domain.model import RefreshToken, Role, User
from yimba.shared.errors import Conflict
from yimba.shared.pagination import Page, PageParams


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10))
    active: Mapped[bool] = mapped_column(Boolean)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    token_version: Mapped[int] = mapped_column(Integer)
    failed_logins: Mapped[int] = mapped_column(Integer)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class RefreshTokenRow(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_id: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    replaced_by: Mapped[str | None] = mapped_column(String(32), nullable=True)


_USER_FIELDS = (
    "email",
    "password_hash",
    "active",
    "full_name",
    "token_version",
    "failed_logins",
    "locked_until",
    "last_login_at",
    "created_at",
    "updated_at",
)


def _user(row: UserRow) -> User:
    return User(id=row.id, role=Role(row.role), **{field: getattr(row, field) for field in _USER_FIELDS})


def _apply_user(row: UserRow, user: User) -> None:
    row.role = user.role.value
    for field in _USER_FIELDS:
        setattr(row, field, getattr(user, field))


def _token(row: RefreshTokenRow) -> RefreshToken:
    return RefreshToken(
        id=row.id,
        user_id=row.user_id,
        token_hash=row.token_hash,
        family_id=row.family_id,
        created_at=row.created_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        replaced_by=row.replaced_by,
    )


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        row = UserRow(id=user.id)
        _apply_user(row, user)
        self._session.add(row)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            # Two registrations of the same email at once: the unique index decides.
            await self._session.rollback()
            raise Conflict("An account already exists for this email", code="identity/email-taken") from exc

    async def get(self, user_id: str) -> User | None:
        row = await self._session.get(UserRow, user_id)
        return _user(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        row = await self._session.scalar(select(UserRow).where(UserRow.email == email))
        return _user(row) if row else None

    async def save(self, user: User) -> None:
        row = await self._session.get(UserRow, user.id)
        if row is None:
            raise LookupError(user.id)
        _apply_user(row, user)
        await self._session.commit()

    async def list(self, params: PageParams, search: str | None = None) -> Page[User]:
        filters = [UserRow.email.ilike(f"%{search.strip().lower()}%")] if search else []
        total = await self._session.scalar(select(func.count()).select_from(UserRow).where(*filters)) or 0
        rows = await self._session.scalars(
            select(UserRow)
            .where(*filters)
            .order_by(UserRow.created_at.desc(), UserRow.id)
            .offset(params.offset)
            .limit(params.size)
        )
        return Page(items=tuple(_user(row) for row in rows), total=total, page=params.page, size=params.size)

    async def count_active_admins(self) -> int:
        query = select(func.count()).select_from(UserRow).where(UserRow.role == Role.ADMIN.value, UserRow.active)
        return await self._session.scalar(query) or 0


class SqlUserLookup:
    """Reads the caller's account in a short session of its own, outside the request's session."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, user_id: str) -> User | None:
        async with self._session_factory() as session:
            row = await session.get(UserRow, user_id)
            return _user(row) if row else None


class SqlRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: RefreshToken) -> None:
        self._session.add(
            RefreshTokenRow(
                id=token.id,
                user_id=token.user_id,
                token_hash=token.token_hash,
                family_id=token.family_id,
                created_at=token.created_at,
                expires_at=token.expires_at,
                revoked_at=token.revoked_at,
                replaced_by=token.replaced_by,
            )
        )
        await self._session.commit()

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        row = await self._session.scalar(select(RefreshTokenRow).where(RefreshTokenRow.token_hash == token_hash))
        return _token(row) if row else None

    async def save(self, token: RefreshToken) -> None:
        row = await self._session.get(RefreshTokenRow, token.id)
        if row is None:
            raise LookupError(token.id)
        row.revoked_at, row.replaced_by = token.revoked_at, token.replaced_by
        await self._session.commit()

    async def revoke_family(self, family_id: str, at: datetime) -> None:
        await self._revoke(RefreshTokenRow.family_id == family_id, at)

    async def revoke_all_for_user(self, user_id: str, at: datetime) -> None:
        await self._revoke(RefreshTokenRow.user_id == user_id, at)

    async def _revoke(self, condition, at: datetime) -> None:
        await self._session.execute(
            update(RefreshTokenRow).where(condition, RefreshTokenRow.revoked_at.is_(None)).values(revoked_at=at)
        )
        await self._session.commit()

    async def purge(self, now: datetime) -> int:
        result = await self._session.execute(delete(RefreshTokenRow).where(RefreshTokenRow.expires_at < now))
        await self._session.commit()
        return result.rowcount or 0
