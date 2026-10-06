import httpx
import pytest

from yimba.modules.collection.adapters import apify_mappers as m
from yimba.modules.collection.adapters.apify import ApifyCollector
from yimba.modules.collection.adapters.factory import build_collectors
from yimba.modules.collection.adapters.queue import TaskQueue
from yimba.modules.collection.adapters.rss_news import RssNewsCollector, parse_rss
from yimba.modules.collection.domain.model import CollectionTarget
from yimba.shared.errors import ExternalServiceError
from yimba.shared.source import SourceKind

TARGET = CollectionTarget("w1", SourceKind.FACEBOOK, ("vaccin", "santé"), ("fr",), ("CI",), limit=5)

RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Vaccination : 120 centres ouverts</title><link>https://news.example/a</link><guid>g-a</guid>
<description>&lt;p&gt;Le ministère annonce&lt;/p&gt;</description>
<pubDate>Mon, 05 Oct 2026 08:00:00 GMT</pubDate><source>Fraternité</source></item>
<item><title>Sans date</title><link>https://news.example/b</link></item>
</channel></rss>"""


class FakeRunner:
    def __init__(self, items):
        self.items, self.calls = items, []

    async def run(self, actor_id, run_input):
        self.calls.append((actor_id, run_input))
        return self.items


def test_facebook_mapper():
    (item,) = m.facebook_items(
        {
            "postId": "p1",
            "text": " Bravo ",
            "user": {"id": "u9", "name": "Awa"},
            "url": "https://fb/p1",
            "date": "2026-10-05T08:00:00.000Z",
            "likesCount": 4,
            "commentsCount": "2",
            "sharesCount": None,
        }
    )
    assert (item.external_id, item.text, item.author_handle, item.likes, item.comments, item.shares) == (
        "p1",
        "Bravo",
        "u9",
        4,
        2,
        0,
    )
    assert item.published_at.isoformat() == "2026-10-05T08:00:00+00:00"


def test_tiktok_twitter_youtube_mappers():
    (tt,) = m.tiktok_items(
        {
            "id": "1",
            "text": "t",
            "authorMeta": {"name": "dj"},
            "diggCount": 3,
            "playCount": 90,
            "createTimeISO": "2026-10-05T08:00:00Z",
        }
    )
    assert (tt.author_handle, tt.likes, tt.views) == ("dj", 3, 90)
    (tw,) = m.twitter_items({"id_str": "7", "full_text": "salut", "user": {"screen_name": "ab"}, "favorite_count": 2})
    assert (tw.external_id, tw.text, tw.author_handle, tw.likes) == ("7", "salut", "ab", 2)
    (yt,) = m.youtube_items(
        {"id": "v", "title": "Titre", "text": "Description", "viewCount": 10, "channelName": "Chaîne"}
    )
    assert yt.text == "Titre. Description" and yt.views == 10


def test_instagram_mapper_flattens_hashtag_records():
    items = m.instagram_items({"topPosts": [{"id": "a", "caption": "x"}], "latestPosts": [{"id": "b", "caption": "y"}]})
    assert [i.external_id for i in items] == ["a", "b"]


def test_google_mapper_one_item_per_organic_result():
    items = m.google_items(
        {"organicResults": [{"url": "https://a", "title": "T", "description": "D"}, {"url": "https://b", "title": "U"}]}
    )
    assert [(i.external_id, i.text) for i in items] == [("https://a", "T. D"), ("https://b", "U")]


def test_mappers_tolerate_garbage():
    (item,) = m.facebook_items({"postId": "p", "likesCount": "n/a", "date": "not a date"})
    assert item.likes == 0 and item.published_at is None and item.text == ""


async def test_apify_collector_runs_once_per_keyword_and_maps_items():
    runner = FakeRunner([{"postId": "p1", "text": "Bravo"}])
    collector = ApifyCollector(SourceKind.FACEBOOK, "actor/fb", runner, m.facebook_input, m.facebook_items)
    items = await collector.collect(TARGET)
    assert [call[1]["keywordList"] for call in runner.calls] == [["vaccin"], ["santé"]]
    assert all(call[0] == "actor/fb" and call[1]["resultsLimit"] == 5 for call in runner.calls)
    assert len(items) == 2


def test_parse_rss():
    first, second = parse_rss(RSS)
    assert first.external_id == "g-a" and first.author_handle == "Fraternité"
    assert first.text == "Vaccination : 120 centres ouverts. Le ministère annonce"
    assert first.published_at.isoformat() == "2026-10-05T08:00:00+00:00"
    assert second.external_id == "https://news.example/b" and second.published_at is None


def test_parse_rss_rejects_invalid_xml_and_entity_bombs():
    with pytest.raises(ExternalServiceError):
        parse_rss("<rss><oops>")
    bomb = (
        '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;">]>'
        "<rss><channel><item><title>&b;</title></item></channel></rss>"
    )
    with pytest.raises(Exception):
        parse_rss(bomb)


async def test_rss_collector_queries_google_news_per_keyword_and_filters_extra_feeds():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "extra.example" in str(request.url):
            body = RSS.replace("Sans date", "Rien à voir")
            return httpx.Response(200, text=body)
        return httpx.Response(200, text=RSS)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    collector = RssNewsCollector(client, extra_feeds=("https://extra.example/feed",))
    target = CollectionTarget("w1", SourceKind.NEWS, ("vaccination",), ("fr",), ("CI",))
    items = await collector.collect(target)

    assert any("news.google.com/rss/search?q=vaccination&hl=fr&gl=CI" in url for url in seen)
    extra_items = [i for i in items if i.text.startswith("Rien")]
    assert extra_items == []  # extra feeds only keep items mentioning a keyword
    assert len([i for i in items if "Vaccination" in i.text]) == 2  # one from each feed


async def test_rss_collector_wraps_network_errors():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(503)))
    with pytest.raises(ExternalServiceError):
        await RssNewsCollector(client).collect(CollectionTarget("w", SourceKind.NEWS, ("x",), ("fr",), ("CI",)))


def test_factory_only_registers_configured_sources():
    client = httpx.AsyncClient()
    registry = build_collectors(runner=FakeRunner([]), actors={SourceKind.FACEBOOK: "a/b"}, http_client=client)
    assert set(registry) == {SourceKind.NEWS, SourceKind.FACEBOOK}
    assert set(build_collectors(runner=None, actors={}, http_client=client)) == {SourceKind.NEWS}


async def test_task_queue_sends_celery_style_calls():
    sent = []
    await TaskQueue(lambda name, args: sent.append((name, args))).enqueue_collection("w1", SourceKind.NEWS)
    assert sent == [("yimba.collect", ["w1", "news"])]
