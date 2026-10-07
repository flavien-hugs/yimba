from __future__ import annotations

import httpx

from yimba.modules.collection.adapters.bluesky import DEFAULT_SERVICE, BlueskyCollector
from yimba.modules.collection.adapters.gdelt import GdeltCollector
from yimba.modules.collection.adapters.meta import (
    DEFAULT_VERSION,
    FacebookPagesCollector,
    GraphApi,
    InstagramHashtagCollector,
)
from yimba.modules.collection.adapters.rss_news import RssNewsCollector
from yimba.modules.collection.adapters.youtube import YouTubeCollector
from yimba.modules.collection.application.ports import CollectorRegistry
from yimba.shared.source import SourceKind


def build_collectors(
    *,
    http_client: httpx.AsyncClient,
    extra_news_feeds: tuple[str, ...] = (),
    gdelt: bool = True,
    youtube_api_key: str | None = None,
    youtube_comment_videos: int = 5,
    bluesky_handle: str | None = None,
    bluesky_app_password: str | None = None,
    bluesky_service: str = DEFAULT_SERVICE,
    meta_access_token: str | None = None,
    meta_app_secret: str | None = None,
    meta_graph_version: str = DEFAULT_VERSION,
    facebook_page_ids: tuple[str, ...] = (),
    facebook_comment_posts: int = 5,
    instagram_account_id: str | None = None,
) -> CollectorRegistry:
    """Build the registry. A source whose credentials are not configured simply has no collector."""
    registry: dict[SourceKind, object] = {SourceKind.NEWS: RssNewsCollector(http_client, extra_news_feeds)}
    if gdelt:
        registry[SourceKind.GDELT] = GdeltCollector(http_client)
    if youtube_api_key:
        registry[SourceKind.YOUTUBE] = YouTubeCollector(http_client, youtube_api_key, youtube_comment_videos)
    if bluesky_handle and bluesky_app_password:
        registry[SourceKind.BLUESKY] = BlueskyCollector(
            http_client, bluesky_handle, bluesky_app_password, bluesky_service
        )
    if meta_access_token:
        graph = GraphApi(http_client, meta_access_token, meta_graph_version, meta_app_secret or None)
        if facebook_page_ids:
            registry[SourceKind.FACEBOOK] = FacebookPagesCollector(graph, facebook_page_ids, facebook_comment_posts)
        if instagram_account_id:
            registry[SourceKind.INSTAGRAM] = InstagramHashtagCollector(graph, instagram_account_id)
    return registry  # type: ignore[return-value]
