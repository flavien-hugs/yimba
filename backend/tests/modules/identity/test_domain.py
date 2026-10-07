from datetime import timedelta

import pytest

from tests.conftest import NOW
from yimba.modules.identity.domain.model import PasswordPolicy, Permission, Principal, Role, User, normalize_email
from yimba.shared.errors import Forbidden, InvalidInput


def test_emails_are_normalized_and_validated():
    assert normalize_email("  Awa.Kone@Example.ORG ") == "awa.kone@example.org"
    assert normalize_email("admin@localhost") == "admin@localhost"
    for invalid in ("awa", "awa@", "@example.org", "awa kone@example.org", "a@b"):
        with pytest.raises(InvalidInput):
            normalize_email(invalid)


def test_password_policy_is_about_length():
    default = PasswordPolicy()
    default.check("x" * 10)
    default.check("é" * 128)
    for invalid in ("x" * 9, "x" * 129):
        with pytest.raises(InvalidInput):
            default.check(invalid)

    strict = PasswordPolicy(min_length=16, max_length=64)
    strict.check("x" * 16)
    with pytest.raises(InvalidInput):
        strict.check("x" * 15)


def test_password_policy_bounds_are_enforced():
    for min_length, max_length in [(7, 128), (20, 10), (10, 2048)]:
        with pytest.raises(ValueError):
            PasswordPolicy(min_length, max_length)


def test_roles_grant_permissions():
    user = User.register(email="u@example.org", password_hash="h", now=NOW)
    admin = User.register(email="a@example.org", password_hash="h", now=NOW, role=Role.ADMIN)
    assert user.role is Role.USER and Permission.WATCH_CREATE in user.permissions
    assert Permission.USER_MANAGE not in user.permissions
    assert admin.permissions > user.permissions and Permission.USER_MANAGE in admin.permissions

    principal = user.principal()
    principal.require([Permission.WATCH_READ, Permission.ALERT_ACKNOWLEDGE])
    with pytest.raises(Forbidden):
        principal.require([Permission.USER_READ])
    with pytest.raises(Forbidden):
        Principal(id="remote").require([Permission.WATCH_READ])  # permissions unknown: nothing granted


def test_repeated_failures_lock_the_account_for_a_while():
    user = User.register(email="u@example.org", password_hash="h", now=NOW)
    for _ in range(4):
        user.record_failed_login(NOW, max_failures=5, lock_for=timedelta(minutes=15))
    assert not user.is_locked(NOW) and user.failed_logins == 4

    user.record_failed_login(NOW, max_failures=5, lock_for=timedelta(minutes=15))
    assert user.is_locked(NOW + timedelta(minutes=14))
    assert not user.is_locked(NOW + timedelta(minutes=15))

    user.record_login(NOW + timedelta(minutes=20))
    assert (user.failed_logins, user.locked_until, user.last_login_at) == (0, None, NOW + timedelta(minutes=20))


def test_changing_the_password_bumps_the_token_version():
    user = User.register(email="u@example.org", password_hash="old", now=NOW)
    user.change_password("new", NOW)
    assert (user.password_hash, user.token_version) == ("new", 1)
