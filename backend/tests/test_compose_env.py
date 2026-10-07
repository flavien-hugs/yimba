"""docker compose lists the backend settings one by one: none may be forgotten."""

from pathlib import Path

import yaml

from yimba.config import Settings

COMPOSE = Path(__file__).resolve().parents[2] / "docker-compose.yaml"
# Set by compose itself (DATABASE_URL, REDIS_URL) or fixed inside the image (API_HOST, API_PORT).
NOT_FROM_ENV_FILE = {"API_HOST", "API_PORT"}


def test_every_setting_reaches_the_backend_containers():
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    passed = set(compose["x-app-env"])
    expected = set(Settings.model_fields) - NOT_FROM_ENV_FILE
    assert expected - passed == set(), "add them to x-app-env in docker-compose.yaml"
    assert passed - set(Settings.model_fields) == set(), "x-app-env passes variables the backend does not read"
