"""YouTube through the official Data API v3 (an API key from a Google Cloud project, no OAuth).

Quota: a project gets 10 000 units a day by default. Collecting one keyword costs 100 units (search)
+ 1 (video statistics) + 1 per video whose comments are read: keep YouTube watches at a low frequency.
"""

from __future__ import annotations

import html
from typing import Any, Mapping, Sequence

import httpx

from yimba.modules.collection.adapters.parsing import as_int, as_text, iso_datetime
from yimba.modules.collection.adapters.partial import collect_partially
from yimba.modules.collection.domain.model import CollectedItem, CollectionTarget
from yimba.shared.errors import ExternalServiceError
from yimba.shared.source import SourceKind

API = "https://www.googleapis.com/youtube/v3"
# Comment reading refused for one video: skip that video, not the whole collection.
_UNREADABLE_COMMENTS = {"commentsDisabled", "videoNotFound", "forbidden"}


class YouTubeApiError(ExternalServiceError):
    def __init__(self, status_code: int, reason: str) -> None:
        super().__init__(f"YouTube API answered {status_code} ({reason})", code="collection/youtube-error")
        self.reason = reason


def _reason(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["errors"][0]["reason"])
    except (ValueError, KeyError, IndexError, TypeError):
        return f"http-{response.status_code}"


def _video_item(video: Mapping[str, Any], statistics: Mapping[str, Any]) -> CollectedItem:
    video_id = as_text((video.get("id") or {}).get("videoId"))
    snippet = video.get("snippet") or {}
    # Search snippets are HTML-escaped.
    title = html.unescape(as_text(snippet.get("title")))
    description = html.unescape(as_text(snippet.get("description")))
    return CollectedItem(
        source=SourceKind.YOUTUBE,
        external_id=video_id,
        text=f"{title}. {description}" if description else title,
        author_handle=as_text(snippet.get("channelId")) or None,
        url=f"https://www.youtube.com/watch?v={video_id}",
        published_at=iso_datetime(snippet.get("publishedAt")),
        likes=as_int(statistics.get("likeCount")),
        views=as_int(statistics.get("viewCount")),
        comments=as_int(statistics.get("commentCount")),
        raw={"video": dict(video), "statistics": dict(statistics)},
    )


def _comment_item(video_id: str, thread: Mapping[str, Any]) -> CollectedItem:
    comment = (thread.get("snippet") or {}).get("topLevelComment") or {}
    snippet = comment.get("snippet") or {}
    comment_id = as_text(comment.get("id"))
    return CollectedItem(
        source=SourceKind.YOUTUBE,
        external_id=comment_id,
        text=as_text(snippet.get("textDisplay")),
        author_handle=as_text((snippet.get("authorChannelId") or {}).get("value"))
        or as_text(snippet.get("authorDisplayName"))
        or None,
        url=f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
        published_at=iso_datetime(snippet.get("publishedAt")),
        likes=as_int(snippet.get("likeCount")),
        comments=as_int((thread.get("snippet") or {}).get("totalReplyCount")),
        raw=dict(thread),
    )


class YouTubeCollector:
    """Recent videos matching each keyword, plus the top-level comments of the first ones (where opinion is)."""

    source = SourceKind.YOUTUBE

    def __init__(self, client: httpx.AsyncClient, api_key: str, comment_videos: int = 5) -> None:
        self._client = client
        self._api_key = api_key
        self._comment_videos = comment_videos

    async def collect(self, target: CollectionTarget) -> Sequence[CollectedItem]:
        return await collect_partially(target.keywords, lambda keyword: self._keyword(keyword, target), label="youtube")

    async def _keyword(self, keyword: str, target: CollectionTarget) -> list[CollectedItem]:
        params: dict[str, Any] = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "date",
            "maxResults": min(target.limit, 50),
        }
        if target.countries:
            params["regionCode"] = target.countries[0]
        if target.languages:
            params["relevanceLanguage"] = target.languages[0]
        found = (await self._get("search", params)).get("items") or []
        videos = [video for video in found if (video.get("id") or {}).get("videoId")]
        if not videos:
            return []

        video_ids = [v["id"]["videoId"] for v in videos]
        listed = await self._get("videos", {"part": "statistics", "id": ",".join(video_ids)})
        statistics = {item.get("id"): item.get("statistics") or {} for item in listed.get("items") or []}

        items = [_video_item(video, statistics.get(video["id"]["videoId"], {})) for video in videos]
        for video_id in video_ids[: self._comment_videos]:
            items.extend(await self._comments(video_id, target.limit))
        return items

    async def _comments(self, video_id: str, limit: int) -> list[CollectedItem]:
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(limit, 100),
            "order": "relevance",
            "textFormat": "plainText",
        }
        try:
            payload = await self._get("commentThreads", params)
        except YouTubeApiError as exc:
            if exc.reason in _UNREADABLE_COMMENTS:
                return []
            raise
        return [_comment_item(video_id, thread) for thread in payload.get("items") or []]

    async def _get(self, resource: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.get(
                f"{API}/{resource}", params={**params, "key": self._api_key}, timeout=20.0
            )
        except httpx.HTTPError as exc:
            # Never put the URL in the message: it carries the API key and ends up in collection_runs.error.
            raise ExternalServiceError(
                f"YouTube API unreachable ({type(exc).__name__})", code="collection/youtube-unreachable"
            ) from exc
        if not response.is_success:
            raise YouTubeApiError(response.status_code, _reason(response))
        payload = response.json()
        return payload if isinstance(payload, dict) else {}
