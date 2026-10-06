from __future__ import annotations

import httpx

from yimba.modules.collection.adapters import apify_mappers as m
from yimba.modules.collection.adapters.apify import ActorRunner, ApifyCollector
from yimba.modules.collection.adapters.rss_news import RssNewsCollector
from yimba.modules.collection.application.ports import CollectorRegistry
from yimba.shared.source import SourceKind


def build_collectors(
    *,
    runner: ActorRunner | None,
    actors: dict[SourceKind, str],
    http_client: httpx.AsyncClient,
    extra_news_feeds: tuple[str, ...] = (),
) -> CollectorRegistry:
    """Build the registry. A source without a configured actor simply has no collector."""
    registry: dict[SourceKind, object] = {SourceKind.NEWS: RssNewsCollector(http_client, extra_news_feeds)}
    if runner is not None:
        recipes = {
            SourceKind.FACEBOOK: (m.facebook_input, m.facebook_items),
            SourceKind.TIKTOK: (m.tiktok_input, m.tiktok_items),
            SourceKind.TWITTER: (m.twitter_input, m.twitter_items),
            SourceKind.INSTAGRAM: (m.instagram_input, m.instagram_items),
            SourceKind.YOUTUBE: (m.youtube_input, m.youtube_items),
            SourceKind.GOOGLE: (m.google_input, m.google_items),
        }
        for source, (build_input, map_item) in recipes.items():
            actor_id = actors.get(source)
            if actor_id:
                registry[source] = ApifyCollector(source, actor_id, runner, build_input, map_item)
    return registry  # type: ignore[return-value]
