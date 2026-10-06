from __future__ import annotations

from functools import lru_cache
from urllib.parse import urljoin

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SALT = "dev-only-change-me"


class Settings(BaseSettings):
    """Every setting comes from an UPPERCASE environment variable of the same name, or a local ``.env`` file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True)

    APP_ENV: str = "dev"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8800
    CORS_ALLOW_ORIGINS: str = "*"
    SENTRY_DSN: str | None = None

    DATABASE_URL: str = "sqlite+aiosqlite:///./yimba.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Existing auth microservice (same variable names as before).
    API_AUTH_URL_BASE: str = "http://auth:9077"
    CHECK_USERINFO_URL: str = "/check-validate-access-token"
    CHECK_ACCESS_URL: str = "/check-access"

    # Collection: official APIs only. A source without credentials has no collector and is never planned.
    NEWS_EXTRA_FEEDS: str = ""
    YOUTUBE_API_KEY: str | None = None
    YOUTUBE_COMMENT_VIDEOS: int = 5
    BLUESKY_HANDLE: str | None = None
    BLUESKY_APP_PASSWORD: str | None = None
    BLUESKY_SERVICE: str = "https://bsky.social"
    COLLECTION_LIMIT: int = 50
    # Raw payloads hold personal data in clear: purged when not seen for this long.
    RAW_RETENTION_DAYS: int = 30

    # Analysis
    ANALYSIS_ENGINE: str = "lexicon"  # "lexicon" (baseline) or "transformers" (needs the 'ml' extra)
    ANALYSIS_MODEL: str | None = None
    AUTHOR_HASH_SALT: str = _DEV_SALT

    # Alerts
    ALERT_WINDOW_HOURS: int = 24
    ALERT_COOLDOWN_HOURS: int = 6

    # Operations: Flower (Celery web UI) credentials, "user:password". Mandatory in production.
    FLOWER_BASIC_AUTH: str | None = None

    @model_validator(mode="after")
    def _require_real_secrets_in_production(self) -> "Settings":
        if self.is_production and self.AUTHOR_HASH_SALT == _DEV_SALT:
            raise ValueError("AUTHOR_HASH_SALT must be set in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in {"prod", "production"}

    @property
    def userinfo_url(self) -> str:
        return urljoin(self.API_AUTH_URL_BASE, self.CHECK_USERINFO_URL)

    @property
    def access_check_url(self) -> str:
        return urljoin(self.API_AUTH_URL_BASE, self.CHECK_ACCESS_URL)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]

    @property
    def extra_news_feeds(self) -> tuple[str, ...]:
        return tuple(feed.strip() for feed in self.NEWS_EXTRA_FEEDS.split(",") if feed.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
