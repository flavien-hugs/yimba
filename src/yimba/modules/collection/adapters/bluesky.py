"""Bluesky through the AT Protocol API.

Post search is refused to anonymous callers (the public endpoint answers 403): the collector logs in with
an account handle and an app password (Settings > Privacy and security > App passwords).
"""

from __future__ import annotations

import time
from typing import Any, Callable, Mapping, Sequence

import httpx

from yimba.modules.collection.adapters.parsing import as_int, as_text, iso_datetime
from yimba.modules.collection.adapters.partial import collect_partially
from yimba.modules.collection.domain.model import CollectedItem, CollectionTarget
from yimba.shared.errors import ExternalServiceError
from yimba.shared.source import SourceKind

DEFAULT_SERVICE = "https://bsky.social"
_SESSION_SECONDS = 60 * 60  # renewed hourly; a token that expires sooner is renewed when the API says so
_TOKEN_ERRORS = {"ExpiredToken", "InvalidToken", "AuthenticationRequired"}

# Logins are rate limited per account (a few hundred a day) and the worker builds a new collector for every
# task, so sessions are shared by every collector of the process.
_sessions: dict[tuple[str, str], tuple[str, float]] = {}


def _error_name(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    error = body.get("error") if isinstance(body, dict) else None
    return error if isinstance(error, str) else None


def _payload(response: httpx.Response, method: str) -> dict[str, Any]:
    if not response.is_success:
        raise ExternalServiceError(
            f"Bluesky {method} answered {response.status_code} ({_error_name(response)})",
            code="collection/bluesky-error",
        )
    body = response.json()
    return body if isinstance(body, dict) else {}


def _post_item(post: Mapping[str, Any]) -> CollectedItem:
    uri = as_text(post.get("uri"))
    author = post.get("author") or {}
    record = post.get("record") or {}
    handle = as_text(author.get("handle"))
    return CollectedItem(
        source=SourceKind.BLUESKY,
        external_id=uri,
        text=as_text(record.get("text")),
        author_handle=as_text(author.get("did")) or handle or None,
        url=f"https://bsky.app/profile/{handle}/post/{uri.rsplit('/', 1)[-1]}" if handle and uri else None,
        published_at=iso_datetime(record.get("createdAt")) or iso_datetime(post.get("indexedAt")),
        likes=as_int(post.get("likeCount")),
        shares=as_int(post.get("repostCount")) + as_int(post.get("quoteCount")),
        comments=as_int(post.get("replyCount")),
    )


class BlueskyCollector:
    """Latest posts matching each keyword."""

    source = SourceKind.BLUESKY

    def __init__(
        self,
        client: httpx.AsyncClient,
        handle: str,
        app_password: str,
        service: str = DEFAULT_SERVICE,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._handle = handle
        self._password = app_password
        self._service = service.rstrip("/")
        self._monotonic = monotonic

    @property
    def _session_key(self) -> tuple[str, str]:
        return self._service, self._handle

    async def collect(self, target: CollectionTarget) -> Sequence[CollectedItem]:
        # The API filters on one language only; with several, search them all.
        language = target.languages[0] if len(target.languages) == 1 else None
        return await collect_partially(
            target.keywords, lambda keyword: self._search(keyword, language, target.limit), label="bluesky"
        )

    async def _search(self, keyword: str, language: str | None, limit: int) -> list[CollectedItem]:
        params: dict[str, Any] = {"q": keyword, "sort": "latest", "limit": min(limit, 100)}
        if language:
            params["lang"] = language
        payload = await self._authorized_get("app.bsky.feed.searchPosts", params)
        return [_post_item(post) for post in payload.get("posts") or []]

    async def _authorized_get(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        response = await self._send("GET", method, params=params, token=await self._token())
        if _error_name(response) in _TOKEN_ERRORS:
            _sessions.pop(self._session_key, None)
            response = await self._send("GET", method, params=params, token=await self._token())
        return _payload(response, method)

    async def _token(self) -> str:
        cached = _sessions.get(self._session_key)
        if cached and cached[1] > self._monotonic():
            return cached[0]
        response = await self._send(
            "POST",
            "com.atproto.server.createSession",
            json={"identifier": self._handle, "password": self._password},
        )
        token = _payload(response, "createSession").get("accessJwt")
        if not token:
            raise ExternalServiceError("Bluesky login returned no token", code="collection/bluesky-error")
        _sessions[self._session_key] = (token, self._monotonic() + _SESSION_SECONDS)
        return token

    async def _send(self, http_method: str, method: str, *, token: str | None = None, **kwargs) -> httpx.Response:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            return await self._client.request(
                http_method, f"{self._service}/xrpc/{method}", headers=headers, timeout=20.0, **kwargs
            )
        except httpx.HTTPError as exc:
            raise ExternalServiceError(
                f"Bluesky unreachable ({type(exc).__name__})", code="collection/bluesky-unreachable"
            ) from exc
