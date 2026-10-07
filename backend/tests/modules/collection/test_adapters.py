import httpx
import pytest

from yimba.modules.collection.adapters.factory import build_collectors
from yimba.modules.collection.adapters.partial import collect_partially
from yimba.modules.collection.adapters.queue import TaskQueue
from yimba.modules.collection.adapters.rss_news import RssNewsCollector, parse_rss
from yimba.modules.collection.domain.model import CollectedItem, CollectionTarget
from yimba.shared.errors import ExternalServiceError
from yimba.shared.source import SourceKind

RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Vaccination : 120 centres ouverts</title><link>https://news.example/a</link><guid>g-a</guid>
<description>&lt;p&gt;Le ministère annonce&lt;/p&gt;</description>
<pubDate>Mon, 05 Oct 2026 08:00:00 GMT</pubDate><source>Fraternité</source></item>
<item><title>Sans date</title><link>https://news.example/b</link></item>
</channel></rss>"""


def test_parse_rss():
    first, second = parse_rss(RSS)
    assert first.external_id == "g-a" and first.author_handle == "Fraternité"
    assert first.text == "Vaccination : 120 centres ouverts. Le ministère annonce"
    assert first.published_at.isoformat() == "2026-10-05T08:00:00+00:00"
    assert second.external_id == "https://news.example/b" and second.published_at is None
    # Where it was found: the publication when the feed names it, else the site of the link.
    assert (first.venue, second.venue) == ("Fraternité", "news.example")


def test_google_news_items_keep_the_title_once():
    feed = """<rss><channel><item>
    <title>Abidjan : coupure d'électricité à Cocody - Abidjan.net News</title><guid>g1</guid>
    <description>&lt;a href="https://news.google.com/x"&gt;Abidjan : coupure d'électricité à Cocody&lt;/a&gt;
    &amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;Abidjan.net News&lt;/font&gt;</description>
    <source url="https://news.abidjan.net">Abidjan.net News</source></item></channel></rss>"""
    (item,) = parse_rss(feed)
    assert item.text == "Abidjan : coupure d'électricité à Cocody" and item.author_handle == "Abidjan.net News"
    assert item.venue == "Abidjan.net News"


def test_a_google_news_link_does_not_name_the_site():
    feed = (
        "<rss><channel><item><title>T</title><link>https://news.google.com/rss/articles/x</link></item></channel></rss>"
    )
    (item,) = parse_rss(feed)
    assert item.venue is None


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


async def test_task_queue_sends_celery_style_calls():
    sent = []
    await TaskQueue(lambda name, args: sent.append((name, args))).enqueue_collection("w1", SourceKind.NEWS)
    assert sent == [("yimba.collect", ["w1", "news"])]


def test_factory_only_registers_configured_sources():
    client = httpx.AsyncClient()
    press = {SourceKind.NEWS, SourceKind.GDELT}  # no key needed
    assert set(build_collectors(http_client=client)) == press
    assert set(build_collectors(http_client=client, gdelt=False)) == {SourceKind.NEWS}
    assert set(build_collectors(http_client=client, youtube_api_key="", bluesky_handle="me")) == press
    registry = build_collectors(
        http_client=client, youtube_api_key="k", bluesky_handle="me.bsky.social", bluesky_app_password="p"
    )
    assert set(registry) == press | {SourceKind.YOUTUBE, SourceKind.BLUESKY}
    # Meta: the token alone enables nothing, each source needs its target (Pages, Instagram account).
    assert set(build_collectors(http_client=client, meta_access_token="t")) == press
    registry = build_collectors(
        http_client=client, meta_access_token="t", facebook_page_ids=("100",), instagram_account_id="ig"
    )
    assert set(registry) == press | {SourceKind.FACEBOOK, SourceKind.INSTAGRAM}


async def test_collect_partially_keeps_what_succeeded_and_fails_only_if_everything_failed():
    async def fetch(keyword):
        if keyword.startswith("bad"):
            raise ExternalServiceError(f"{keyword} failed")
        return [CollectedItem(SourceKind.NEWS, keyword, keyword)]

    items = await collect_partially(["ok", "bad"], fetch, label="test")
    assert [item.external_id for item in items] == ["ok"]
    with pytest.raises(ExternalServiceError, match="bad1 failed"):
        await collect_partially(["bad1", "bad2"], fetch, label="test")
    assert await collect_partially([], fetch, label="test") == []
