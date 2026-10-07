"""AccountService and local access control, on the test database with real tokens and Argon2 (cheap settings)."""

from datetime import timedelta

import pytest

from tests.conftest import NOW, fast_hasher
from yimba.modules.identity.adapters.persistence import SqlRefreshTokenRepository, SqlUserLookup, SqlUserRepository
from yimba.modules.identity.adapters.tokens import JwtAccessTokens, TokenSecrets
from yimba.modules.identity.application.accounts import AccountService, AuthPolicy, TokenAccessControl
from yimba.modules.identity.domain.model import Permission, Role
from yimba.shared.errors import Conflict, Forbidden, InvalidInput, NotFound, Unauthorized
from yimba.shared.pagination import PageParams

PASSWORD = "correct horse battery"
TOKENS = JwtAccessTokens("test-secret-of-at-least-32-characters!!", lifetime_minutes=15)


@pytest.fixture
def accounts(session, clock):
    def build(**policy):
        return AccountService(
            SqlUserRepository(session),
            SqlRefreshTokenRepository(session),
            fast_hasher(),
            TOKENS,
            TokenSecrets(),
            clock,
            AuthPolicy(**policy),
        )

    return build


@pytest.fixture
def access(container, clock):
    return TokenAccessControl(TOKENS, SqlUserLookup(container.session_factory), clock)


async def test_register_normalizes_and_hashes(accounts):
    user = await accounts().register("  Awa@Example.org ", PASSWORD, "  Awa   Koné ")
    assert (user.email, user.full_name, user.role, user.active) == ("awa@example.org", "Awa Koné", Role.USER, True)
    assert user.password_hash != PASSWORD and user.password_hash.startswith("$argon2id$")

    with pytest.raises(Conflict):
        await accounts().register("AWA@example.org", PASSWORD)
    with pytest.raises(InvalidInput):
        await accounts().register("short@example.org", "too short")


async def test_password_lengths_follow_the_policy(accounts):
    from yimba.modules.identity.domain.model import PasswordPolicy

    strict = PasswordPolicy(min_length=24, max_length=64)
    with pytest.raises(InvalidInput):
        await accounts(password=strict).register("u@example.org", PASSWORD)  # 21 characters
    user = await accounts(password=strict).register("u@example.org", PASSWORD + "-and-more")
    with pytest.raises(InvalidInput):
        await accounts(password=strict).change_password(user.id, PASSWORD + "-and-more", "x" * 65)


async def test_closed_registration_still_lets_admins_create_accounts(accounts):
    with pytest.raises(Forbidden):
        await accounts(registration_enabled=False).register("u@example.org", PASSWORD)
    admin = await accounts(registration_enabled=False).register(
        "a@example.org", PASSWORD, role=Role.ADMIN, by_admin=True
    )
    assert admin.role is Role.ADMIN


async def test_login_gives_tokens_the_access_control_accepts(accounts, access):
    user = await accounts().register("u@example.org", PASSWORD)
    pair = await accounts().login("U@example.org", PASSWORD)
    assert pair.token_type == "bearer" and pair.expires_in == 900 and pair.refresh_token

    principal = await access.authenticate(pair.access_token)
    assert (principal.id, principal.email, principal.role) == (user.id, "u@example.org", "user")
    await access.authorize(principal, pair.access_token, [Permission.WATCH_CREATE])
    with pytest.raises(Forbidden):
        await access.authorize(principal, pair.access_token, [Permission.USER_READ])
    assert (await accounts().profile(user.id)).last_login_at == NOW


async def test_wrong_credentials_get_one_answer(accounts):
    await accounts().register("u@example.org", PASSWORD)
    for email, password in [("u@example.org", "wrong password"), ("nobody@example.org", PASSWORD), ("bad", "x")]:
        with pytest.raises(Unauthorized) as raised:
            await accounts().login(email, password)
        assert raised.value.code == "identity/invalid-credentials"


async def test_too_many_failures_lock_the_account(accounts, clock):
    await accounts().register("u@example.org", PASSWORD)
    for _ in range(3):
        with pytest.raises(Unauthorized):
            await accounts(max_failed_logins=3).login("u@example.org", "wrong password")
    with pytest.raises(Unauthorized):  # even with the right password, until the lock expires
        await accounts(max_failed_logins=3).login("u@example.org", PASSWORD)

    clock.set(NOW + timedelta(minutes=15))
    assert (await accounts(max_failed_logins=3).login("u@example.org", PASSWORD)).access_token


async def test_access_tokens_expire_and_cannot_be_forged(accounts, access, clock):
    await accounts().register("u@example.org", PASSWORD)
    pair = await accounts().login("u@example.org", PASSWORD)

    forged = JwtAccessTokens("another-secret-of-at-least-32-characters").issue(
        await accounts().profile((await access.authenticate(pair.access_token)).id), NOW
    )
    for token in (forged, pair.access_token[:-2] + "xx", pair.refresh_token, "not-a-token"):
        with pytest.raises(Unauthorized):
            await access.authenticate(token)

    clock.set(NOW + timedelta(minutes=15))
    with pytest.raises(Unauthorized):
        await access.authenticate(pair.access_token)


async def test_refresh_rotates_and_a_replay_revokes_the_session(accounts, access):
    await accounts().register("u@example.org", PASSWORD)
    first = await accounts().login("u@example.org", PASSWORD)

    second = await accounts().refresh(first.refresh_token)
    assert second.refresh_token != first.refresh_token
    await access.authenticate(second.access_token)

    with pytest.raises(Unauthorized):  # the first refresh token was spent: replaying it means it was stolen
        await accounts().refresh(first.refresh_token)
    with pytest.raises(Unauthorized):  # ...and the whole session is now revoked
        await accounts().refresh(second.refresh_token)


async def test_refresh_tokens_expire(accounts, clock):
    await accounts().register("u@example.org", PASSWORD)
    pair = await accounts(refresh_lifetime=timedelta(days=1)).login("u@example.org", PASSWORD)
    clock.set(NOW + timedelta(days=1))
    with pytest.raises(Unauthorized):
        await accounts().refresh(pair.refresh_token)
    clock.set(NOW + timedelta(days=1, minutes=1))
    assert await accounts().purge_expired_tokens() == 1


async def test_logout_ends_the_session_only(accounts):
    await accounts().register("u@example.org", PASSWORD)
    laptop = await accounts().login("u@example.org", PASSWORD)
    phone = await accounts().login("u@example.org", PASSWORD)

    await accounts().logout(laptop.refresh_token)
    await accounts().logout(laptop.refresh_token)  # twice is fine
    with pytest.raises(Unauthorized):
        await accounts().refresh(laptop.refresh_token)
    assert (await accounts().refresh(phone.refresh_token)).access_token


async def test_changing_the_password_ends_every_session(accounts, access):
    user = await accounts().register("u@example.org", PASSWORD)
    pair = await accounts().login("u@example.org", PASSWORD)

    with pytest.raises(Forbidden):
        await accounts().change_password(user.id, "wrong password", "a brand new password")
    await accounts().change_password(user.id, PASSWORD, "a brand new password")

    with pytest.raises(Unauthorized):
        await access.authenticate(pair.access_token)
    with pytest.raises(Unauthorized):
        await accounts().refresh(pair.refresh_token)
    with pytest.raises(Unauthorized):
        await accounts().login("u@example.org", PASSWORD)
    assert (await accounts().login("u@example.org", "a brand new password")).access_token


async def test_admins_manage_accounts_but_one_admin_always_remains(accounts, access):
    admin = await accounts().register("a@example.org", PASSWORD, role=Role.ADMIN, by_admin=True)
    user = await accounts().register("u@example.org", PASSWORD)
    pair = await accounts().login("u@example.org", PASSWORD)

    with pytest.raises(Conflict):
        await accounts().update_user(admin.id, role=Role.USER)
    with pytest.raises(Conflict):
        await accounts().update_user(admin.id, active=False)
    with pytest.raises(NotFound):
        await accounts().update_user("missing", active=False)

    promoted = await accounts().update_user_by_email("U@example.org", role=Role.ADMIN)
    assert promoted.role is Role.ADMIN
    principal = await access.authenticate(pair.access_token)  # the role is read at each request
    await access.authorize(principal, pair.access_token, [Permission.USER_MANAGE])

    await accounts().update_user(admin.id, role=Role.USER)  # another admin remains: allowed
    with pytest.raises(Conflict):  # the promoted user is now the last admin
        await accounts().update_user(user.id, active=False)
    await accounts().update_user(admin.id, role=Role.ADMIN)
    await accounts().update_user(user.id, active=False)
    with pytest.raises(Unauthorized):  # disabled: access and refresh stop at once
        await access.authenticate(pair.access_token)
    with pytest.raises(Unauthorized):
        await accounts().refresh(pair.refresh_token)

    page = await accounts().list_users(PageParams(1, 10), search="example")
    assert page.total == 2
