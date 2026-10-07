"""The only import surface other modules and entrypoints may use."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yimba.modules.identity.adapters.auth_service import AuthServiceAccessControl
from yimba.modules.identity.adapters.passwords import Argon2PasswordHasher
from yimba.modules.identity.adapters.persistence import SqlRefreshTokenRepository, SqlUserLookup, SqlUserRepository
from yimba.modules.identity.adapters.tokens import JwtAccessTokens, TokenSecrets
from yimba.modules.identity.application.accounts import AccountService, AuthPolicy, TokenAccessControl, TokenPair
from yimba.modules.identity.application.ports import AccessControl, AccessTokens, PasswordHasher
from yimba.modules.identity.domain.model import PasswordPolicy, Permission, Principal, Role, User
from yimba.shared.clock import Clock


def build_account_service(
    session: AsyncSession,
    *,
    hasher: PasswordHasher,
    access_tokens: AccessTokens,
    clock: Clock,
    policy: AuthPolicy,
) -> AccountService:
    return AccountService(
        users=SqlUserRepository(session),
        refresh_tokens=SqlRefreshTokenRepository(session),
        hasher=hasher,
        access_tokens=access_tokens,
        secrets=TokenSecrets(),
        clock=clock,
        policy=policy,
    )


def build_local_access_control(
    session_factory: async_sessionmaker[AsyncSession], access_tokens: AccessTokens, clock: Clock
) -> AccessControl:
    return TokenAccessControl(access_tokens, SqlUserLookup(session_factory), clock)


__all__ = [
    "AccessControl",
    "AccountService",
    "Argon2PasswordHasher",
    "AuthPolicy",
    "AuthServiceAccessControl",
    "JwtAccessTokens",
    "PasswordHasher",
    "PasswordPolicy",
    "Permission",
    "Principal",
    "Role",
    "TokenPair",
    "User",
    "build_account_service",
    "build_local_access_control",
]
