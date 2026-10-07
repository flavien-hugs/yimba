"""Operations tooling: Flower command and error tracking."""

from typer.testing import CliRunner

from yimba.config import get_settings
from yimba.entrypoints import cli
from yimba.infrastructure import error_tracking


def test_flower_refuses_to_start_unprotected_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTHOR_HASH_SALT", "a-real-salt")
    monkeypatch.setenv("JWT_SECRET", "a-real-secret-of-at-least-32-characters")
    monkeypatch.delenv("FLOWER_BASIC_AUTH", raising=False)
    get_settings.cache_clear()
    try:
        result = CliRunner().invoke(cli.app, ["flower"])
    finally:
        get_settings.cache_clear()
    assert result.exit_code == 1 and "FLOWER_BASIC_AUTH" in result.output


def test_flower_gets_the_basic_auth(monkeypatch):
    from yimba.entrypoints.worker.app import celery

    started = []
    monkeypatch.setenv("FLOWER_BASIC_AUTH", "admin:secret")
    monkeypatch.setattr(celery, "start", started.append)
    get_settings.cache_clear()
    try:
        result = CliRunner().invoke(cli.app, ["flower", "--port", "5600"])
    finally:
        get_settings.cache_clear()
    assert result.exit_code == 0
    assert started == [["flower", "--port=5600", "--basic-auth=admin:secret"]]


def test_error_tracking_is_off_without_a_dsn(monkeypatch):
    calls = []
    monkeypatch.setattr(error_tracking.sentry_sdk, "init", lambda **kw: calls.append(kw))
    assert error_tracking.init_error_tracking(None, "dev", "api") is False
    assert calls == []


def test_error_tracking_sends_no_personal_data(monkeypatch):
    calls = []
    monkeypatch.setattr(error_tracking.sentry_sdk, "init", lambda **kw: calls.append(kw))
    monkeypatch.setattr(error_tracking.sentry_sdk, "set_tag", lambda *args: None)
    assert error_tracking.init_error_tracking("http://key@glitchtip:8000/1", "production", "worker") is True
    (options,) = calls
    assert options["dsn"] == "http://key@glitchtip:8000/1" and options["environment"] == "production"
    assert options["send_default_pii"] is False


def test_production_refuses_placeholder_secrets(monkeypatch):
    import pytest

    from yimba.config import Settings

    for salt, secret in [
        ("ChangeMe", "x" * 40),
        ("a-real-salt", ""),
        ("a-real-salt", "too-short"),
        ("a-real-salt", "CHANGEME"),
    ]:
        with pytest.raises(ValueError):
            Settings(APP_ENV="production", AUTHOR_HASH_SALT=salt, JWT_SECRET=secret)
    settings = Settings(APP_ENV="production", AUTHOR_HASH_SALT="a-real-salt", JWT_SECRET="x" * 40)
    assert settings.JWT_SECRET == "x" * 40
    for min_length, max_length in [(7, 128), (20, 10), (10, 2048)]:
        with pytest.raises(ValueError):
            Settings(MIN_PASSWORD_LENGTH=min_length, MAX_PASSWORD_LENGTH=max_length)
    dev = Settings(APP_ENV="dev", AUTHOR_HASH_SALT="", JWT_SECRET="")
    assert dev.JWT_SECRET and dev.AUTHOR_HASH_SALT  # empty means "not set": development defaults
