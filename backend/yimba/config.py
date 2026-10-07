from __future__ import annotations

from functools import lru_cache
from urllib.parse import urljoin

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SALT = "dev-only-change-me"
_DEV_JWT_SECRET = "dev-only-jwt-secret-change-me-in-production"
# Values that are not secrets: the development defaults and the placeholders of .env.example.
_PLACEHOLDERS = {_DEV_SALT, _DEV_JWT_SECRET, "changeme", "change-me", "secret"}


class Settings(BaseSettings):
    """Every setting comes from an UPPERCASE environment variable of the same name.

    No .env file is read here: docker compose passes the variables listed in its x-app-env, and the root Makefile
    exports the .env for local commands.
    """

    model_config = SettingsConfigDict(case_sensitive=True)

    APP_ENV: str = "dev"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8800
    CORS_ALLOW_ORIGINS: str = "*"
    SENTRY_DSN: str | None = None

    DATABASE_URL: str = "sqlite+aiosqlite:///./yimba.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Authentication: "local" accounts in this database (JWT), or the legacy "remote" auth microservice.
    AUTH_PROVIDER: str = "local"
    JWT_SECRET: str = _DEV_JWT_SECRET
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 30
    REGISTRATION_ENABLED: bool = True
    # After this many wrong passwords in a row, the account refuses logins for LOGIN_LOCK_MINUTES.
    LOGIN_MAX_FAILURES: int = 5
    LOGIN_LOCK_MINUTES: int = 15
    # Accepted password lengths (any characters): 8 <= MIN_PASSWORD_LENGTH <= MAX_PASSWORD_LENGTH <= 1024.
    MIN_PASSWORD_LENGTH: int = 10
    MAX_PASSWORD_LENGTH: int = 128

    # Legacy auth microservice, used only when AUTH_PROVIDER=remote (same variable names as before).
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
        if self.AUTH_PROVIDER not in {"local", "remote"}:
            raise ValueError("AUTH_PROVIDER must be 'local' or 'remote'")
        if not 8 <= self.MIN_PASSWORD_LENGTH <= self.MAX_PASSWORD_LENGTH <= 1024:
            raise ValueError("password lengths must satisfy 8 <= MIN_PASSWORD_LENGTH <= MAX_PASSWORD_LENGTH <= 1024")
        # An empty value (as in .env.example) means "not set".
        self.AUTHOR_HASH_SALT = self.AUTHOR_HASH_SALT or _DEV_SALT
        self.JWT_SECRET = self.JWT_SECRET or _DEV_JWT_SECRET
        if self.is_production:
            if self.AUTHOR_HASH_SALT.lower() in _PLACEHOLDERS:
                raise ValueError("AUTHOR_HASH_SALT must be set in production")
            if self.AUTH_PROVIDER == "local" and (
                self.JWT_SECRET.lower() in _PLACEHOLDERS or len(self.JWT_SECRET) < 32
            ):
                raise ValueError("JWT_SECRET must be set in production, at least 32 random characters")
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
