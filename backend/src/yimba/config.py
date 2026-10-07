from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urljoin

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SALT = "dev-only-change-me"
# The repository's .env sits at the monorepo root (shared with docker compose); a backend/.env may override it.
_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Every setting comes from an UPPERCASE environment variable of the same name, or from a ``.env`` file."""

    model_config = SettingsConfigDict(env_file=(_ROOT_ENV_FILE, ".env"), extra="ignore", case_sensitive=True)

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
    GDELT_ENABLED: bool = True
    YOUTUBE_API_KEY: str | None = None
    YOUTUBE_COMMENT_VIDEOS: int = 5
    BLUESKY_HANDLE: str | None = None
    BLUESKY_APP_PASSWORD: str | None = None
    BLUESKY_SERVICE: str = "https://bsky.social"
    # Meta (Facebook Pages, Instagram hashtags): one Meta app, one long-lived token.
    META_ACCESS_TOKEN: str | None = None
    META_APP_SECRET: str | None = None
    META_GRAPH_VERSION: str = "v25.0"
    FACEBOOK_PAGE_IDS: str = ""
    FACEBOOK_COMMENT_POSTS: int = 5
    INSTAGRAM_ACCOUNT_ID: str | None = None
    COLLECTION_LIMIT: int = 50
    # Raw payloads hold personal data in clear: purged when not seen for this long.
    RAW_RETENTION_DAYS: int = 30

    # Analysis
    ANALYSIS_ENGINE: str = "lexicon"  # "lexicon" (baseline) or "transformers" (needs the 'ml' extra)
    ANALYSIS_MODEL: str | None = None
    # Evaluations against the annotated corpus are recorded on this MLflow server (needs the 'tracking' extra).
    MLFLOW_TRACKING_URI: str | None = None
    MLFLOW_EXPERIMENT: str = "yimba-analysis"
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

    @property
    def facebook_pages(self) -> tuple[str, ...]:
        return tuple(page.strip() for page in self.FACEBOOK_PAGE_IDS.split(",") if page.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
