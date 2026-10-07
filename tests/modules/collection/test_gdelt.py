"""GDELT DOC 2.0 collector, against the documented ArtList response (no network)."""

import httpx
import pytest

from yimba.modules.collection.adapters.gdelt import GdeltCollector, gdelt_query
from yimba.modules.collection.domain.model import CollectionTarget
from yimba.shared.errors import ExternalServiceError
from yimba.shared.source import SourceKind

ARTICLES = {
    "articles": [
        {
            "url": "https://www.fratmat.info/article/1",
            "url_mobile": "",
            "title": "Campagne de vaccination : les centres pris d'assaut",
            "seendate": "20261005T081500Z",
            "socialimage": "",
            "domain": "fratmat.info",
            "language": "French",
            "sourcecountry": "Ivory Coast",
        }
    ]
}


def target(keywords=("vaccination",), languages=("fr",)):
    return CollectionTarget("w1", SourceKind.GDELT, tuple(keywords), tuple(languages), ("CI",), limit=20)


async def no_sleep(seconds):
    no_sleep.calls.append(seconds)


def test_query_joins_keywords_and_filters_a_single_language():
    assert gdelt_query(["vaccination"], ["fr"]) == "vaccination sourcelang:french"
    assert gdelt_query(["côte d'ivoire", "abidjan"], ["fr"]) == '("côte d\'ivoire" OR abidjan) sourcelang:french'
    assert gdelt_query(['"vaccin"'], ["fr", "en"]) == "vaccin"
    assert gdelt_query(["vaccin"], ["bm"]) == "vaccin"


async def test_maps_articles():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=ARTICLES)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    (item,) = await GdeltCollector(client).collect(target(("vaccination", "santé")))

    assert (item.source, item.external_id, item.author_handle) == (
        SourceKind.GDELT,
        "https://www.fratmat.info/article/1",
        "fratmat.info",
    )
    assert item.text == "Campagne de vaccination : les centres pris d'assaut"
    assert item.published_at.isoformat() == "2026-10-05T08:15:00+00:00" and item.raw["language"] == "French"
    params = seen[0].url.params
    assert (params["mode"], params["format"], params["timespan"], params["maxrecords"]) == (
        "ArtList",
        "json",
        "1d",
        "40",
    )


async def test_no_result_is_an_empty_object():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})))
    assert await GdeltCollector(client).collect(target()) == []


async def test_throttling_is_retried_then_reported():
    answers = iter([httpx.Response(429, text="Please limit requests"), httpx.Response(200, json=ARTICLES)])
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: next(answers)))
    no_sleep.calls = []
    assert len(await GdeltCollector(client, sleep=no_sleep).collect(target())) == 1
    assert no_sleep.calls == [6.0]

    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(429, text="slow down")))
    no_sleep.calls = []
    with pytest.raises(ExternalServiceError, match="429"):
        await GdeltCollector(client, retries=2, sleep=no_sleep).collect(target())
    assert no_sleep.calls == [6.0, 12.0]


async def test_plain_text_errors_are_reported():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="The specified phrase is too short."))
    )
    with pytest.raises(ExternalServiceError, match="too short"):
        await GdeltCollector(client).collect(target())
