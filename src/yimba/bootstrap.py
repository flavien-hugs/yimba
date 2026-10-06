"""Composition root: the only place where ports are bound to concrete adapters."""

from __future__ import annotations

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
    ApifyActorRunner,
    CollectForWatch,
    DirectoryWatchCatalog,
    MentionsItemSink,
    PlanCollections,
    SqlRunRepository,
    TaskQueue,
    build_collectors,
)
from yimba.modules.identity.public import AccessControl, AuthServiceAccessControl
from yimba.modules.mentions.public import build_mention_ingestor, build_sentiment_window_reader
from yimba.modules.watches.public import build_watch_directory
from yimba.shared.clock import Clock, SystemClock
from yimba.shared.source import SourceKind


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
    ) -> None:
        self.settings = settings
        self.clock: Clock = clock or SystemClock()
        self.http = http_client or httpx.AsyncClient(timeout=15.0)
        self.engine = engine or make_engine(settings.database_url, **(engine_kwargs or {}))
        self.session_factory: async_sessionmaker[AsyncSession] = make_session_factory(self.engine)
        self.analyzer = analyzer or build_text_analyzer(settings.analysis_engine, settings.analysis_model)
        self.access_control = access_control or AuthServiceAccessControl(
            self.http, settings.userinfo_url, settings.access_check_url
        )
        self.collectors: CollectorRegistry = collectors if collectors is not None else self._build_collectors()

    def _build_collectors(self) -> CollectorRegistry:
        s = self.settings
        actors = {
            SourceKind.FACEBOOK: s.apify_facebook_actor,
            SourceKind.TIKTOK: s.apify_tiktok_actor,
            SourceKind.TWITTER: s.apify_twitter_actor,
            SourceKind.INSTAGRAM: s.apify_instagram_actor,
            SourceKind.YOUTUBE: s.apify_youtube_actor,
            SourceKind.GOOGLE: s.apify_google_actor,
        }
        runner = ApifyActorRunner(s.apify_token) if s.apify_token else None
        return build_collectors(
            runner=runner,
            actors={source: actor for source, actor in actors.items() if actor},
            http_client=self.http,
            extra_news_feeds=s.extra_news_feeds,
        )

    # ---- use cases bound to a session --------------------------------------------------------------------------

    def collect_for_watch(self, session: AsyncSession) -> CollectForWatch:
        return CollectForWatch(
            catalog=DirectoryWatchCatalog(build_watch_directory(session)),
            collectors=self.collectors,
            sink=MentionsItemSink(
                build_mention_ingestor(session, self.analyzer, self.clock, self.settings.author_hash_salt)
            ),
            runs=SqlRunRepository(session),
            clock=self.clock,
            limit=self.settings.collection_limit,
        )

    def plan_collections(self, session: AsyncSession, send_task: Callable[..., object]) -> PlanCollections:
        return PlanCollections(
            catalog=DirectoryWatchCatalog(build_watch_directory(session)),
            runs=SqlRunRepository(session),
            queue=TaskQueue(send_task),
            clock=self.clock,
        )

    def evaluate_alerts(self, session: AsyncSession) -> EvaluateAlerts:
        return EvaluateAlerts(
            rules=DirectoryAlertRules(build_watch_directory(session)),
            window=MentionsSentimentWindow(build_sentiment_window_reader(session)),
            alerts=SqlAlertRepository(session),
            notifier=LogNotifier(),
            clock=self.clock,
            window_hours=self.settings.alert_window_hours,
            cooldown_hours=self.settings.alert_cooldown_hours,
        )

    async def aclose(self) -> None:
        await self.http.aclose()
        await self.engine.dispose()
