from __future__ import annotations

import httpx

from yimba.modules.collection.adapters.bluesky import DEFAULT_SERVICE, BlueskyCollector
from yimba.modules.collection.adapters.rss_news import RssNewsCollector
from yimba.modules.collection.adapters.youtube import YouTubeCollector
from yimba.modules.collection.application.ports import CollectorRegistry
from yimba.shared.source import SourceKind


def build_collectors(
    *,
    http_client: httpx.AsyncClient,
    extra_news_feeds: tuple[str, ...] = (),
    youtube_api_key: str | None = None,
    youtube_comment_videos: int = 5,
    bluesky_handle: str | None = None,
    bluesky_app_password: str | None = None,
    bluesky_service: str = DEFAULT_SERVICE,
) -> CollectorRegistry:
    """Build the registry. A source whose credentials are not configured simply has no collector."""
    registry: dict[SourceKind, object] = {SourceKind.NEWS: RssNewsCollector(http_client, extra_news_feeds)}
    if youtube_api_key:
        registry[SourceKind.YOUTUBE] = YouTubeCollector(http_client, youtube_api_key, youtube_comment_videos)
    if bluesky_handle and bluesky_app_password:
        registry[SourceKind.BLUESKY] = BlueskyCollector(
            http_client, bluesky_handle, bluesky_app_password, bluesky_service
        )
    return registry  # type: ignore[return-value]
