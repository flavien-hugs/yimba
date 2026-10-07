from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Sequence

from yimba.modules.identity.application.ports import (
    AccessTokens,
    PasswordHasher,
    RefreshTokenRepository,
    SecretGenerator,
    UserLookup,
    UserRepository,
)
from yimba.modules.identity.domain.model import PasswordPolicy, Principal, RefreshToken, Role, User, normalize_email
from yimba.shared.clock import Clock
from yimba.shared.errors import Conflict, Forbidden, InvalidInput, NotFound, Unauthorized
from yimba.shared.ids import new_id
from yimba.shared.pagination import Page, PageParams


@dataclass(frozen=True, slots=True)
class AuthPolicy:
    registration_enabled: bool = True
    refresh_lifetime: timedelta = timedelta(days=30)
    max_failed_logins: int = 5
    lock_duration: timedelta = timedelta(minutes=15)
    password: PasswordPolicy = PasswordPolicy()


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


def _invalid_credentials() -> Unauthorized:
    # One answer for unknown email, wrong password, locked or disabled account: nothing to learn from it.
    return Unauthorized("Invalid credentials", code="identity/invalid-credentials")


def _invalid_refresh_token() -> Unauthorized:
    return Unauthorized("Invalid or expired refresh token", code="identity/invalid-refresh-token")


class AccountService:
    """Accounts and sessions: registration, login, token refresh and revocation, password, administration."""

    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        hasher: PasswordHasher,
        access_tokens: AccessTokens,
        secrets: SecretGenerator,
        clock: Clock,
        policy: AuthPolicy = AuthPolicy(),
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._hasher = hasher
        self._access_tokens = access_tokens
        self._secrets = secrets
        self._clock = clock
        self._policy = policy

    # ---- accounts ---------------------------------------------------------------------------------------------

    async def register(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
        *,
        role: Role = Role.USER,
        by_admin: bool = False,
    ) -> User:
        """Public registration creates plain users; admins (API or CLI) choose the role, even when it is closed."""
        if not by_admin and not self._policy.registration_enabled:
            raise Forbidden("Registration is closed", code="identity/registration-closed")
        email = normalize_email(email)
        self._policy.password.check(password)
        if await self._users.get_by_email(email) is not None:
            raise Conflict("An account already exists for this email", code="identity/email-taken")
        user = User.register(
            email=email,
            password_hash=self._hasher.hash(password),
            now=self._clock.now(),
            role=role,
            full_name=full_name,
        )
        await self._users.add(user)
        return user

    async def profile(self, user_id: str) -> User:
        user = await self._users.get(user_id)
        if user is None or user.is_deleted:
            raise Unauthorized("Unknown account", code="identity/invalid-token")
        return user

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        """Every other session ends: access tokens through the token version, refresh tokens by revocation."""
        user = await self.profile(user_id)
        if not self._hasher.verify(user.password_hash, current_password):
            raise Forbidden("The current password is wrong", code="identity/wrong-password")
        self._policy.password.check(new_password)
        now = self._clock.now()
        user.change_password(self._hasher.hash(new_password), now)
        await self._users.save(user)
        await self._refresh_tokens.revoke_all_for_user(user.id, now)

    async def list_users(
        self, params: PageParams, search: str | None = None, include_deleted: bool = False
    ) -> Page[User]:
        return await self._users.list(params, search, include_deleted)

    async def update_user(self, user_id: str, *, role: Role | None = None, active: bool | None = None) -> User:
        return await self._update(await self._live_user(user_id), role=role, active=active)

    async def delete_user(self, user_id: str) -> User:
        """Soft delete: the account stops working at once (login, access and refresh tokens), the row stays."""
        user = await self._live_user(user_id)
        await self._ensure_an_admin_remains(user)
        now = self._clock.now()
        user.delete(now)
        await self._users.save(user)
        await self._refresh_tokens.revoke_all_for_user(user.id, now)
        return user

    async def _live_user(self, user_id: str) -> User:
        user = await self._users.get(user_id)
        if user is None or user.is_deleted:
            raise NotFound(f"User {user_id} not found", code="identity/user-not-found")
        return user

    async def _ensure_an_admin_remains(self, user: User) -> None:
        if user.role is Role.ADMIN and user.active and await self._users.count_active_admins() <= 1:
            raise Conflict("At least one active admin must remain", code="identity/last-admin")

    async def update_user_by_email(self, email: str, *, role: Role | None = None, active: bool | None = None) -> User:
        user = await self._users.get_by_email(normalize_email(email))
        if user is None:
            raise NotFound(f"No account for {email}", code="identity/user-not-found")
        return await self._update(user, role=role, active=active)

    async def _update(self, user: User, *, role: Role | None, active: bool | None) -> User:
        if role not in (None, Role.ADMIN) or active is False:
            await self._ensure_an_admin_remains(user)
        now = self._clock.now()
        user.update(now, role=role, active=active)
        await self._users.save(user)
        if active is False:
            await self._refresh_tokens.revoke_all_for_user(user.id, now)
        return user

    # ---- sessions ---------------------------------------------------------------------------------------------

    async def login(self, email: str, password: str) -> TokenPair:
        now = self._clock.now()
        try:
            user = await self._users.get_by_email(normalize_email(email))
        except InvalidInput:
            user = None
        if user is None:
            self._hasher.verify_dummy(password)
            raise _invalid_credentials()
        if not user.active or user.is_locked(now):
            self._hasher.verify_dummy(password)
            raise _invalid_credentials()
        if not self._hasher.verify(user.password_hash, password):
            user.record_failed_login(
                now, max_failures=self._policy.max_failed_logins, lock_for=self._policy.lock_duration
            )
            await self._users.save(user)
            raise _invalid_credentials()

        if self._hasher.needs_rehash(user.password_hash):
            user.password_hash = self._hasher.hash(password)
        user.record_login(now)
        await self._users.save(user)
        pair, _ = await self._issue(user, family_id=new_id())
        return pair

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Rotate: the presented token is spent and replaced. Replaying a spent token revokes its whole family."""
        now = self._clock.now()
        stored = await self._refresh_tokens.get_by_hash(self._secrets.digest(refresh_token))
        if stored is None:
            raise _invalid_refresh_token()
        if stored.revoked_at is not None:
            if stored.replaced_by is not None:
                await self._refresh_tokens.revoke_family(stored.family_id, now)
            raise _invalid_refresh_token()
        if not stored.is_usable(now):
            raise _invalid_refresh_token()
        user = await self._users.get(stored.user_id)
        if user is None or not user.active:
            await self._refresh_tokens.revoke_family(stored.family_id, now)
            raise _invalid_refresh_token()

        pair, replacement = await self._issue(user, family_id=stored.family_id)
        stored.revoked_at, stored.replaced_by = now, replacement.id
        await self._refresh_tokens.save(stored)
        return pair

    async def logout(self, refresh_token: str) -> None:
        """Ends the session the refresh token belongs to; logging out twice is not an error."""
        stored = await self._refresh_tokens.get_by_hash(self._secrets.digest(refresh_token))
        if stored is not None:
            await self._refresh_tokens.revoke_family(stored.family_id, self._clock.now())

    async def purge_expired_tokens(self) -> int:
        return await self._refresh_tokens.purge(self._clock.now())

    async def _issue(self, user: User, *, family_id: str) -> tuple[TokenPair, RefreshToken]:
        now = self._clock.now()
        secret = self._secrets.new()
        token = RefreshToken(
            id=new_id(),
            user_id=user.id,
            token_hash=self._secrets.digest(secret),
            family_id=family_id,
            created_at=now,
            expires_at=now + self._policy.refresh_lifetime,
        )
        await self._refresh_tokens.add(token)
        pair = TokenPair(
            access_token=self._access_tokens.issue(user, now),
            refresh_token=secret,
            expires_in=self._access_tokens.lifetime_seconds,
        )
        return pair, token


class TokenAccessControl:
    """Local access control: a signed access token, then the account as it is now (active, role, token version).

    Reading the account on every request makes deactivation, role changes and password changes immediate.
    """

    def __init__(self, access_tokens: AccessTokens, users: UserLookup, clock: Clock) -> None:
        self._access_tokens = access_tokens
        self._users = users
        self._clock = clock

    async def authenticate(self, token: str) -> Principal:
        claims = self._access_tokens.read(token, self._clock.now())
        user = await self._users.get(claims.user_id)
        if user is None or not user.active or user.token_version != claims.token_version:
            raise Unauthorized("Invalid or expired token", code="identity/invalid-token")
        return user.principal()

    async def authorize(self, principal: Principal, token: str, permissions: Sequence[str]) -> None:
        principal.require(permissions)
