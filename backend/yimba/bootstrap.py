"""Composition root: the only place where ports are bound to concrete adapters."""

from __future__ import annotations

from datetime import timedelta
from typing import Callable

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from yimba.config import Settings
from yimba.infrastructure.db import make_engine, make_session_factory
from yimba.modules.alerts.public import (
    DirectoryAlertRules,
    EvaluateAlerts,
    LogNotifier,
    MentionsSentimentWindow,
    SqlAlertRepository,
)
from yimba.modules.analysis.public import TextAnalyzer, build_text_analyzer
from yimba.modules.collection.application.ports import CollectorRegistry
from yimba.modules.collection.public import (
    CollectForWatch,
    DirectoryWatchCatalog,
    MentionsItemSink,
    PlanCollections,
    PurgeRawItems,
    SqlRawArchive,
    SqlRunRepository,
    TaskQueue,
    build_collectors,
)
from yimba.modules.identity.public import (
    AccessControl,
    AccountService,
    Argon2PasswordHasher,
    AuthPolicy,
    AuthServiceAccessControl,
    JwtAccessTokens,
    PasswordHasher,
    PasswordPolicy,
    build_account_service,
    build_local_access_control,
)
from yimba.modules.mentions.public import build_mention_ingestor, build_sentiment_window_reader
from yimba.modules.watches.public import build_watch_directory
from yimba.shared.clock import Clock, SystemClock


class Container:
    """Holds the long-lived objects and builds per-session use cases.

    Everything can be overridden (tests pass fakes), nothing is created at import time.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        engine: AsyncEngine | None = None,
        clock: Clock | None = None,
        analyzer: TextAnalyzer | None = None,
        access_control: AccessControl | None = None,
        collectors: CollectorRegistry | None = None,
        http_client: httpx.AsyncClient | None = None,
        engine_kwargs: dict | None = None,
        password_hasher: PasswordHasher | None = None,
    ) -> None:
        self.settings = settings
        self.clock: Clock = clock or SystemClock()
        self.http = http_client or httpx.AsyncClient(timeout=15.0)
        self.engine = engine or make_engine(settings.DATABASE_URL, **(engine_kwargs or {}))
        self.session_factory: async_sessionmaker[AsyncSession] = make_session_factory(self.engine)
        self.analyzer = analyzer or build_text_analyzer(settings.ANALYSIS_ENGINE, settings.ANALYSIS_MODEL)
        self.password_hasher: PasswordHasher = password_hasher or Argon2PasswordHasher()
        self.access_tokens = JwtAccessTokens(settings.JWT_SECRET, settings.ACCESS_TOKEN_MINUTES)
        self.auth_policy = AuthPolicy(
            registration_enabled=settings.REGISTRATION_ENABLED,
            refresh_lifetime=timedelta(days=settings.REFRESH_TOKEN_DAYS),
            max_failed_logins=settings.LOGIN_MAX_FAILURES,
            lock_duration=timedelta(minutes=settings.LOGIN_LOCK_MINUTES),
            password=PasswordPolicy(settings.MIN_PASSWORD_LENGTH, settings.MAX_PASSWORD_LENGTH),
        )
        self.access_control = access_control or self._build_access_control()
        self.collectors: CollectorRegistry = collectors if collectors is not None else self._build_collectors()

    def _build_access_control(self) -> AccessControl:
        s = self.settings
        if s.AUTH_PROVIDER == "remote":
            return AuthServiceAccessControl(self.http, s.userinfo_url, s.access_check_url)
        return build_local_access_control(self.session_factory, self.access_tokens, self.clock)

    def _build_collectors(self) -> CollectorRegistry:
        s = self.settings
        return build_collectors(
            http_client=self.http,
            extra_news_feeds=s.extra_news_feeds,
            gdelt=s.GDELT_ENABLED,
            youtube_api_key=s.YOUTUBE_API_KEY,
            youtube_comment_videos=s.YOUTUBE_COMMENT_VIDEOS,
            bluesky_handle=s.BLUESKY_HANDLE,
            bluesky_app_password=s.BLUESKY_APP_PASSWORD,
            bluesky_service=s.BLUESKY_SERVICE,
            meta_access_token=s.META_ACCESS_TOKEN,
            meta_app_secret=s.META_APP_SECRET,
            meta_graph_version=s.META_GRAPH_VERSION,
            facebook_page_ids=s.facebook_pages,
            facebook_comment_posts=s.FACEBOOK_COMMENT_POSTS,
            instagram_account_id=s.INSTAGRAM_ACCOUNT_ID,
        )

    # ---- use cases bound to a session --------------------------------------------------------------------------

    def accounts(self, session: AsyncSession) -> AccountService:
        return build_account_service(
            session,
            hasher=self.password_hasher,
            access_tokens=self.access_tokens,
            clock=self.clock,
            policy=self.auth_policy,
        )

    def collect_for_watch(self, session: AsyncSession) -> CollectForWatch:
        return CollectForWatch(
            catalog=DirectoryWatchCatalog(build_watch_directory(session)),
            collectors=self.collectors,
            sink=MentionsItemSink(
                build_mention_ingestor(session, self.analyzer, self.clock, self.settings.AUTHOR_HASH_SALT)
            ),
            runs=SqlRunRepository(session),
            archive=SqlRawArchive(session),
            clock=self.clock,
            limit=self.settings.COLLECTION_LIMIT,
        )

    def purge_raw_items(self, session: AsyncSession) -> PurgeRawItems:
        return PurgeRawItems(SqlRawArchive(session), self.clock, self.settings.RAW_RETENTION_DAYS)

    def plan_collections(self, session: AsyncSession, send_task: Callable[..., object]) -> PlanCollections:
        return PlanCollections(
            catalog=DirectoryWatchCatalog(build_watch_directory(session)),
            runs=SqlRunRepository(session),
            queue=TaskQueue(send_task),
            clock=self.clock,
            sources=self.collectors.keys(),
        )

    def evaluate_alerts(self, session: AsyncSession) -> EvaluateAlerts:
        return EvaluateAlerts(
            rules=DirectoryAlertRules(build_watch_directory(session)),
            window=MentionsSentimentWindow(build_sentiment_window_reader(session)),
            alerts=SqlAlertRepository(session),
            notifier=LogNotifier(),
            clock=self.clock,
            window_hours=self.settings.ALERT_WINDOW_HOURS,
            cooldown_hours=self.settings.ALERT_COOLDOWN_HOURS,
        )

    async def aclose(self) -> None:
        await self.http.aclose()
        await self.engine.dispose()
