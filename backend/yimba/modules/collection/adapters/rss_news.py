from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Sequence
from urllib.parse import quote_plus, urlparse

import httpx
from defusedxml import ElementTree

from yimba.modules.collection.domain.model import CollectedItem, CollectionTarget
from yimba.shared.errors import ExternalServiceError
from yimba.shared.source import SourceKind

# Google News has no edition for these countries (it answers with another one) and finds a keyword in the news of the
# whole world: naming the country keeps the results about it ("réforme électorale" alone finds India and Italy).
COUNTRY_NAMES = {"CI": "Côte d'Ivoire"}
GOOGLE_NEWS_SEARCH = "https://news.google.com/rss/search?q={query}&hl={lang}&gl={country}&ceid={country}:{lang}"
_TAGS = re.compile(r"<[^>]+>")


def _clean(value: str | None) -> str:
    return " ".join(html.unescape(_TAGS.sub(" ", value or "")).split())


def _site_of(link: str) -> str | None:
    """The site of an article link; Google News links only point at Google, which says nothing about the article."""
    host = (urlparse(link).hostname or "").removeprefix("www.")
    return None if not host or host.endswith("google.com") else host


def parse_rss(xml_text: str) -> list[CollectedItem]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise ExternalServiceError(f"Invalid RSS feed: {exc}", code="collection/rss-invalid") from exc

    items: list[CollectedItem] = []
    for node in root.iter("item"):
        link = (node.findtext("link") or "").strip()
        guid = (node.findtext("guid") or link).strip()
        title, description = _clean(node.findtext("title")), _clean(node.findtext("description"))
        publisher = _clean(node.findtext("source"))
        # Google News titles end with " - <publisher>" and its descriptions only repeat the title: keep the title,
        # otherwise every word (sentiment cues included) would be counted twice.
        if publisher and title.endswith(f" - {publisher}"):
            title = title[: -len(publisher) - 3]
        repeats_title = not description or description in title or description.startswith(title)
        text = title if repeats_title else f"{title}. {description}"
        published: datetime | None = None
        raw_date = node.findtext("pubDate")
        if raw_date:
            try:
                published = parsedate_to_datetime(raw_date)
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                published = None
        items.append(
            CollectedItem(
                source=SourceKind.NEWS,
                external_id=guid,
                text=text,
                author_handle=publisher or None,
                venue=publisher or _site_of(link),
                url=link or None,
                published_at=published,
                raw={child.tag: (child.text or "").strip() for child in node},
            )
        )
    return items


def _query(keyword: str, country: str) -> str:
    name = COUNTRY_NAMES.get(country)
    return f'{keyword} "{name}"' if name else keyword


class RssNewsCollector:
    """Press coverage through Google News RSS (no API key) plus any extra feeds configured by the operator."""

    source = SourceKind.NEWS

    def __init__(self, client: httpx.AsyncClient, extra_feeds: Sequence[str] = ()) -> None:
        self._client = client
        self._extra_feeds = tuple(extra_feeds)

    async def collect(self, target: CollectionTarget) -> Sequence[CollectedItem]:
        language = target.languages[0] if target.languages else "fr"
        country = (target.countries[0] if target.countries else "CI").upper()
        urls = [
            GOOGLE_NEWS_SEARCH.format(query=quote_plus(_query(keyword, country)), lang=language, country=country)
            for keyword in target.keywords
        ] + list(self._extra_feeds)

        keywords = [keyword.lower() for keyword in target.keywords]
        collected: list[CollectedItem] = []
        for url in urls:
            try:
                response = await self._client.get(url, timeout=20.0, follow_redirects=True)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ExternalServiceError(f"Cannot read feed {url}: {exc}", code="collection/rss-unreachable") from exc
            for item in parse_rss(response.text):
                # Extra feeds are not keyword searches: keep only what mentions a keyword.
                if url in self._extra_feeds and not any(k in item.text.lower() for k in keywords):
                    continue
                collected.append(item)
        return collected[: target.limit * max(1, len(target.keywords))]
