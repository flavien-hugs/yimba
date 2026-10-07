"""World press coverage through the GDELT DOC 2.0 API (free, no key).

GDELT answers 429 to more than one request every 5 seconds per IP address: one collection sends a single query
(keywords joined with OR) and waits before retrying when throttled.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Mapping, Sequence

import httpx

from yimba.modules.collection.adapters.parsing import as_text
from yimba.modules.collection.domain.model import CollectedItem, CollectionTarget
from yimba.shared.errors import ExternalServiceError
from yimba.shared.source import SourceKind

API = "https://api.gdeltproject.org/api/v2/doc/doc"
MAX_RECORDS = 250
# GDELT filters on language names.
_LANGUAGES = {"fr": "french", "en": "english", "ar": "arabic", "pt": "portuguese", "es": "spanish"}


def gdelt_query(keywords: Sequence[str], languages: Sequence[str]) -> str:
    terms = [f'"{keyword}"' if " " in keyword else keyword for keyword in (k.replace('"', "") for k in keywords)]
    query = terms[0] if len(terms) == 1 else "(" + " OR ".join(terms) + ")"
    # Filter only on a single known language; with several, search them all.
    if len(languages) == 1 and languages[0] in _LANGUAGES:
        query += f" sourcelang:{_LANGUAGES[languages[0]]}"
    return query


def _seen_date(value: Any) -> datetime | None:
    try:
        return datetime.strptime(as_text(value), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _article_item(article: Mapping[str, Any]) -> CollectedItem:
    url = as_text(article.get("url"))
    return CollectedItem(
        source=SourceKind.GDELT,
        external_id=url,
        text=as_text(article.get("title")),
        author_handle=as_text(article.get("domain")) or None,
        venue=as_text(article.get("domain")) or None,
        url=url or None,
        published_at=_seen_date(article.get("seendate")),
        raw=dict(article),
    )


class GdeltCollector:
    """Articles of the last ``timespan`` matching any keyword, from GDELT's worldwide press monitoring."""

    source = SourceKind.GDELT

    def __init__(
        self,
        client: httpx.AsyncClient,
        timespan: str = "1d",
        retries: int = 3,
        retry_delay: float = 6.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._timespan = timespan
        self._retries = retries
        self._retry_delay = retry_delay
        self._sleep = sleep

    async def collect(self, target: CollectionTarget) -> Sequence[CollectedItem]:
        if not target.keywords:
            return []
        params = {
            "query": gdelt_query(target.keywords, target.languages),
            "mode": "ArtList",
            "format": "json",
            "sort": "DateDesc",
            "timespan": self._timespan,
            "maxrecords": min(MAX_RECORDS, target.limit * len(target.keywords)),
        }
        response = await self._get(params)
        try:
            payload = response.json()
        except ValueError as exc:
            # Query errors come back as plain text with a 200 status.
            raise ExternalServiceError(
                f"GDELT rejected the query: {response.text.strip()[:200]}", code="collection/gdelt-error"
            ) from exc
        articles = payload.get("articles") if isinstance(payload, dict) else None
        return [_article_item(article) for article in articles or [] if isinstance(article, Mapping)]

    async def _get(self, params: dict[str, Any]) -> httpx.Response:
        for attempt in range(self._retries + 1):
            try:
                response = await self._client.get(API, params=params, timeout=30.0)
            except httpx.HTTPError as exc:
                raise ExternalServiceError(
                    f"GDELT unreachable ({type(exc).__name__})", code="collection/gdelt-unreachable"
                ) from exc
            if response.status_code != 429:
                break
            if attempt < self._retries:
                await self._sleep(self._retry_delay * (attempt + 1))
        if not response.is_success:
            raise ExternalServiceError(f"GDELT answered {response.status_code}", code="collection/gdelt-error")
        return response
