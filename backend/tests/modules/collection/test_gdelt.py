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
    assert item.venue == "fratmat.info"
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


async def test_timeouts_are_retried_then_reported():
    attempts = []

    def slow(request):
        attempts.append(request)
        if len(attempts) < 2:
            raise httpx.ConnectTimeout("")
        return httpx.Response(200, json=ARTICLES)

    client = httpx.AsyncClient(transport=httpx.MockTransport(slow))
    no_sleep.calls = []
    assert len(await GdeltCollector(client, sleep=no_sleep).collect(target())) == 1
    assert no_sleep.calls == [6.0]

    def down(request):
        raise httpx.ConnectTimeout("")

    client = httpx.AsyncClient(transport=httpx.MockTransport(down))
    with pytest.raises(ExternalServiceError, match=r"ConnectTimeout"):
        await GdeltCollector(client, retries=1, sleep=no_sleep).collect(target())


async def test_retry_after_is_honoured():
    answers = iter([httpx.Response(429, headers={"Retry-After": "25"}), httpx.Response(200, json=ARTICLES)])
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: next(answers)))
    no_sleep.calls = []
    await GdeltCollector(client, sleep=no_sleep).collect(target())
    assert no_sleep.calls == [25.0]


async def test_watches_collected_one_after_the_other_are_spaced():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=ARTICLES)))
    clock = iter([100.0, 102.0, 102.0])  # request 1 at 100; then asked again at 102, and sent at 102
    no_sleep.calls = []
    collector = GdeltCollector(client, sleep=no_sleep, now=lambda: next(clock))
    await collector.collect(target())
    await collector.collect(target())
    assert no_sleep.calls == [4.0]  # 6 s between two requests, 2 s have passed


async def test_plain_text_errors_are_reported():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="The specified phrase is too short."))
    )
    with pytest.raises(ExternalServiceError, match="too short"):
        await GdeltCollector(client).collect(target())
