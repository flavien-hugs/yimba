"""Facebook Pages and Instagram hashtags through Meta's Graph API: one Meta app, one long-lived token.

What the API gives, and what it does not:

* Facebook: posts of chosen Pages and the comments under them. Pages the token's owner manages need
  ``pages_read_engagement`` and ``pages_read_user_content``; other public Pages need the "Page Public Content
  Access" feature (App Review), and Meta then hides comment ids. There is no keyword search over Facebook:
  posts are filtered on the watch keywords here.
* Instagram: hashtag search with an Instagram professional account (``instagram_basic`` and the "Instagram
  Public Content Access" feature). Media of the last 24 hours only, 30 distinct hashtags per account over a
  rolling 7 days, captions only (no comments, no author).
"""

from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any, Mapping, Sequence

import httpx

from yimba.modules.collection.adapters.parsing import as_int, as_text, iso_datetime
from yimba.modules.collection.adapters.partial import collect_partially
from yimba.modules.collection.domain.model import CollectedItem, CollectionTarget
from yimba.shared.errors import ExternalServiceError
from yimba.shared.source import SourceKind

GRAPH = "https://graph.facebook.com"
DEFAULT_VERSION = "v25.0"
POST_FIELDS = (
    "id,message,created_time,permalink_url,shares,"
    "reactions.summary(total_count).limit(0),comments.summary(total_count).limit(0)"
)
COMMENT_FIELDS = "id,message,created_time,like_count,comment_count,permalink_url,from"
MEDIA_FIELDS = "id,caption,media_type,comments_count,like_count,permalink,timestamp"


class GraphApiError(ExternalServiceError):
    def __init__(self, status_code: int, error_code: Any, message: str) -> None:
        super().__init__(
            f"Graph API answered {status_code} (code {error_code}): {message}", code="collection/meta-error"
        )
        self.error_code = error_code


class GraphApi:
    """Minimal Graph API client. The token never appears in error messages (they end up in collection_runs)."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        version: str = DEFAULT_VERSION,
        app_secret: str | None = None,
    ) -> None:
        self._client = client
        self._token = access_token
        self._version = version
        self._app_secret = app_secret

    async def get(self, path: str, params: Mapping[str, Any], *, token: str | None = None) -> dict[str, Any]:
        token = token or self._token
        query = {**params, "access_token": token}
        if self._app_secret:
            # Required when the app enables "Require App Secret": proves the call comes from the app's server.
            query["appsecret_proof"] = hmac.new(self._app_secret.encode(), token.encode(), hashlib.sha256).hexdigest()
        try:
            response = await self._client.get(f"{GRAPH}/{self._version}/{path}", params=query, timeout=20.0)
        except httpx.HTTPError as exc:
            raise ExternalServiceError(
                f"Graph API unreachable ({type(exc).__name__})", code="collection/meta-unreachable"
            ) from exc
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        payload = payload if isinstance(payload, dict) else {}
        if not response.is_success or "error" in payload:
            error = payload.get("error") or {}
            raise GraphApiError(response.status_code, error.get("code"), str(error.get("message") or "")[:300])
        return payload


def hashtag_of(keyword: str) -> str:
    """Instagram hashtags are a single word: "Côte d'Ivoire" is searched as "côtedivoire"."""
    return re.sub(r"\W+", "", keyword.lstrip("#").lower())


def _media_item(media: Mapping[str, Any]) -> CollectedItem:
    return CollectedItem(
        source=SourceKind.INSTAGRAM,
        external_id=as_text(media.get("id")),
        text=as_text(media.get("caption")),
        url=as_text(media.get("permalink")) or None,
        published_at=iso_datetime(media.get("timestamp")),
        likes=as_int(media.get("like_count")),
        comments=as_int(media.get("comments_count")),
        raw=dict(media),
    )


class InstagramHashtagCollector:
    """Recent public media (last 24 hours) carrying each keyword as a hashtag."""

    source = SourceKind.INSTAGRAM

    def __init__(self, graph: GraphApi, account_id: str) -> None:
        self._graph = graph
        self._account_id = account_id

    async def collect(self, target: CollectionTarget) -> Sequence[CollectedItem]:
        hashtags = list(dict.fromkeys(tag for tag in map(hashtag_of, target.keywords) if tag))
        return await collect_partially(hashtags, lambda tag: self._hashtag(tag, target.limit), label="instagram")

    async def _hashtag(self, hashtag: str, limit: int) -> list[CollectedItem]:
        found = await self._graph.get("ig_hashtag_search", {"user_id": self._account_id, "q": hashtag})
        hashtag_ids = [entry["id"] for entry in found.get("data") or [] if entry.get("id")]
        if not hashtag_ids:
            return []
        media = await self._graph.get(
            f"{hashtag_ids[0]}/recent_media",
            {"user_id": self._account_id, "fields": MEDIA_FIELDS, "limit": min(limit, 50)},
        )
        return [_media_item(entry) for entry in media.get("data") or []]


def _summary_total(value: Any) -> int:
    return as_int(((value or {}).get("summary") or {}).get("total_count")) if isinstance(value, Mapping) else 0


def _post_item(page_id: str, post: Mapping[str, Any]) -> CollectedItem:
    return CollectedItem(
        source=SourceKind.FACEBOOK,
        external_id=as_text(post.get("id")),
        text=as_text(post.get("message")),
        author_handle=page_id,
        url=as_text(post.get("permalink_url")) or None,
        published_at=iso_datetime(post.get("created_time")),
        likes=_summary_total(post.get("reactions")),
        shares=as_int((post.get("shares") or {}).get("count")),
        comments=_summary_total(post.get("comments")),
        raw=dict(post),
    )


def _comment_item(post: Mapping[str, Any], comment: Mapping[str, Any]) -> CollectedItem:
    text = as_text(comment.get("message"))
    created = as_text(comment.get("created_time"))
    # Comment ids are withheld for Pages read through "Page Public Content Access": derive a stable one.
    comment_id = as_text(comment.get("id")) or (
        f"{as_text(post.get('id'))}:" + hashlib.sha256(f"{created}|{text}".encode("utf-8")).hexdigest()[:24]
    )
    return CollectedItem(
        source=SourceKind.FACEBOOK,
        external_id=comment_id,
        text=text,
        author_handle=as_text((comment.get("from") or {}).get("id")) or None,
        url=as_text(comment.get("permalink_url")) or as_text(post.get("permalink_url")) or None,
        published_at=iso_datetime(created),
        likes=as_int(comment.get("like_count")),
        comments=as_int(comment.get("comment_count")),
        raw=dict(comment),
    )


class FacebookPagesCollector:
    """Recent posts of the configured Pages that mention a keyword, and the comments under the first ones."""

    source = SourceKind.FACEBOOK

    def __init__(self, graph: GraphApi, page_ids: Sequence[str], comment_posts: int = 5) -> None:
        self._graph = graph
        self._page_ids = tuple(page_ids)
        self._comment_posts = comment_posts

    async def collect(self, target: CollectionTarget) -> Sequence[CollectedItem]:
        keywords = [keyword.lower() for keyword in target.keywords]
        return await collect_partially(
            self._page_ids, lambda page_id: self._page(page_id, keywords, target.limit), label="facebook"
        )

    async def _page(self, page_id: str, keywords: list[str], limit: int) -> list[CollectedItem]:
        token = await self._page_token(page_id)
        found = await self._graph.get(
            f"{page_id}/posts", {"fields": POST_FIELDS, "limit": min(limit, 100)}, token=token
        )
        posts = [
            post
            for post in found.get("data") or []
            if post.get("id") and any(keyword in as_text(post.get("message")).lower() for keyword in keywords)
        ]
        items = [_post_item(page_id, post) for post in posts]
        for post in posts[: self._comment_posts]:
            comments = await self._graph.get(
                f"{post['id']}/comments",
                {
                    "fields": COMMENT_FIELDS,
                    "filter": "toplevel",
                    "order": "reverse_chronological",
                    "limit": min(limit, 100),
                },
                token=token,
            )
            items.extend(_comment_item(post, comment) for comment in comments.get("data") or [])
        return items

    async def _page_token(self, page_id: str) -> str | None:
        """A Page the token's owner manages is read with its own Page token; any other Page with the main token."""
        try:
            page = await self._graph.get(page_id, {"fields": "access_token"})
        except GraphApiError:
            return None
        return as_text(page.get("access_token")) or None
