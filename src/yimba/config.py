from __future__ import annotations

from functools import lru_cache
from urllib.parse import urljoin

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SALT = "dev-only-change-me"


class Settings(BaseSettings):
    """Every setting comes from the environment (case-insensitive) or a local ``.env`` file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    api_host: str = "0.0.0.0"
    api_port: int = 8800
    cors_allow_origins: str = "*"
    sentry_dsn: str | None = None

    database_url: str = "sqlite+aiosqlite:///./yimba.db"
    redis_url: str = "redis://localhost:6379/0"

    # Existing auth microservice (same variable names as before).
    api_auth_url_base: str = "http://auth:9077"
    check_userinfo_url: str = "/check-validate-access-token"
    check_access_url: str = "/check-access"

    # Collection
    apify_token: str | None = None
    apify_facebook_actor: str | None = None
    apify_tiktok_actor: str | None = None
    apify_twitter_actor: str | None = None
    apify_instagram_actor: str | None = None
    apify_youtube_actor: str | None = None
    apify_google_actor: str | None = None
    news_extra_feeds: str = ""
    collection_limit: int = 50

    # Analysis
    analysis_engine: str = "lexicon"  # "lexicon" (baseline) or "transformers" (needs the 'ml' extra)
    analysis_model: str | None = None
    author_hash_salt: str = _DEV_SALT

    # Alerts
    alert_window_hours: int = 24
    alert_cooldown_hours: int = 6

    @model_validator(mode="after")
    def _require_real_secrets_in_production(self) -> "Settings":
        if self.is_production and self.author_hash_salt == _DEV_SALT:
            raise ValueError("AUTHOR_HASH_SALT must be set in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}

    @property
    def userinfo_url(self) -> str:
        return urljoin(self.api_auth_url_base, self.check_userinfo_url)

    @property
    def access_check_url(self) -> str:
        return urljoin(self.api_auth_url_base, self.check_access_url)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def extra_news_feeds(self) -> tuple[str, ...]:
        return tuple(feed.strip() for feed in self.news_extra_feeds.split(",") if feed.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
