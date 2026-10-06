"""Platform specific bits for the Apify actors: how to call them and how to read their output.

The field names come from the legacy implementation and the public actor schemas. They MUST be
checked against recorded payloads of the actors actually configured in production (see
``tests/modules/collection/test_apify_mappers.py`` for the shapes assumed here).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from yimba.modules.collection.domain.model import CollectedItem, CollectionTarget
from yimba.shared.source import SourceKind


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _date(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _author(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = value.get("id") or value.get("name") or value.get("userName") or value.get("screen_name")
    return str(value) if value else None


# ---- actor inputs -----------------------------------------------------------------------------------------------


def facebook_input(target: CollectionTarget, keyword: str) -> dict[str, Any]:
    return {"keywordList": [keyword], "resultsLimit": target.limit}


def tiktok_input(target: CollectionTarget, keyword: str) -> dict[str, Any]:
    return {
        "hashtags": [keyword],
        "resultsPerPage": target.limit,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
        "shouldDownloadSlideshowImages": False,
    }


def twitter_input(target: CollectionTarget, keyword: str) -> dict[str, Any]:
    return {
        "handles": [keyword],
        "tweetsDesired": target.limit,
        "addUserInfo": True,
        "startUrls": [],
        "proxyConfig": {"useApifyProxy": True},
    }


def instagram_input(target: CollectionTarget, keyword: str) -> dict[str, Any]:
    return {
        "search": keyword,
        "resultsType": "posts",
        "resultsLimit": target.limit,
        "searchType": "hashtag",
        "searchLimit": 1,
    }


def youtube_input(target: CollectionTarget, keyword: str) -> dict[str, Any]:
    return {
        "searchKeywords": keyword,
        "maxResults": target.limit,
        "maxResultsShorts": 0,
        "maxResultStreams": 0,
    }


def google_input(target: CollectionTarget, keyword: str) -> dict[str, Any]:
    country = (target.countries[0] if target.countries else "CI").lower()
    language = target.languages[0] if target.languages else "fr"
    return {
        "queries": keyword,
        "maxPagesPerQuery": 1,
        "resultsPerPage": min(target.limit, 100),
        "countryCode": country,
        "languageCode": language,
    }


# ---- output mappers ---------------------------------------------------------------------------------------------


def facebook_items(raw: Mapping[str, Any]) -> Sequence[CollectedItem]:
    return [
        CollectedItem(
            source=SourceKind.FACEBOOK,
            external_id=str(raw.get("postId") or raw.get("id") or ""),
            text=_text(raw.get("text")),
            author_handle=_author(raw.get("user")),
            url=raw.get("url"),
            published_at=_date(raw.get("date")),
            likes=_int(raw.get("likesCount")),
            shares=_int(raw.get("sharesCount")),
            views=_int(raw.get("viewsCount")),
            comments=_int(raw.get("commentsCount")),
        )
    ]


def tiktok_items(raw: Mapping[str, Any]) -> Sequence[CollectedItem]:
    return [
        CollectedItem(
            source=SourceKind.TIKTOK,
            external_id=str(raw.get("id") or ""),
            text=_text(raw.get("text")),
            author_handle=_author(raw.get("authorMeta")),
            url=raw.get("webVideoUrl"),
            published_at=_date(raw.get("createTimeISO") or raw.get("createTime")),
            likes=_int(raw.get("diggCount")),
            shares=_int(raw.get("shareCount")),
            views=_int(raw.get("playCount")),
            comments=_int(raw.get("commentCount")),
        )
    ]


def twitter_items(raw: Mapping[str, Any]) -> Sequence[CollectedItem]:
    return [
        CollectedItem(
            source=SourceKind.TWITTER,
            external_id=str(raw.get("id_str") or raw.get("id") or ""),
            text=_text(raw.get("full_text") or raw.get("text")),
            author_handle=_author(raw.get("user")),
            url=raw.get("url"),
            published_at=_date(raw.get("created_at")),
            likes=_int(raw.get("favorite_count")),
            shares=_int(raw.get("retweet_count")),
            views=_int(raw.get("view_count")),
            comments=_int(raw.get("reply_count")),
        )
    ]


def instagram_items(raw: Mapping[str, Any]) -> Sequence[CollectedItem]:
    """The hashtag scraper returns one record per hashtag holding ``topPosts`` and ``latestPosts``."""
    posts = [*(raw.get("topPosts") or []), *(raw.get("latestPosts") or [])] or [raw]
    return [
        CollectedItem(
            source=SourceKind.INSTAGRAM,
            external_id=str(post.get("id") or ""),
            text=_text(post.get("caption")),
            author_handle=_author(post.get("ownerUsername") or post.get("ownerId")),
            url=post.get("url"),
            published_at=_date(post.get("timestamp")),
            likes=_int(post.get("likesCount")),
            comments=_int(post.get("commentsCount")),
            views=_int(post.get("videoViewCount")),
        )
        for post in posts
    ]


def youtube_items(raw: Mapping[str, Any]) -> Sequence[CollectedItem]:
    title, description = _text(raw.get("title")), _text(raw.get("text") or raw.get("description"))
    return [
        CollectedItem(
            source=SourceKind.YOUTUBE,
            external_id=str(raw.get("id") or ""),
            text=f"{title}. {description}".strip(". ") if description else title,
            author_handle=_author(raw.get("channelName") or raw.get("channelId")),
            url=raw.get("url"),
            published_at=_date(raw.get("date") or raw.get("uploadDate")),
            likes=_int(raw.get("likes")),
            views=_int(raw.get("viewCount")),
            comments=_int(raw.get("commentsCount")),
        )
    ]


def google_items(raw: Mapping[str, Any]) -> Sequence[CollectedItem]:
    results = raw.get("organicResults") or []
    return [
        CollectedItem(
            source=SourceKind.GOOGLE,
            external_id=str(result.get("url") or ""),
            text=". ".join(part for part in (_text(result.get("title")), _text(result.get("description"))) if part),
            author_handle=None,
            url=result.get("url"),
        )
        for result in results
    ]
