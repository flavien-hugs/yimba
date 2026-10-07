"""Facebook Pages and Instagram hashtag collectors, against the documented Graph API shapes (no network)."""

import hashlib
import hmac

import httpx
import pytest

from yimba.modules.collection.adapters.meta import (
    FacebookPagesCollector,
    GraphApi,
    InstagramHashtagCollector,
    hashtag_of,
)
from yimba.modules.collection.domain.model import CollectionTarget
from yimba.shared.errors import ExternalServiceError
from yimba.shared.source import SourceKind

POSTS = {
    "data": [
        {
            "id": "100_1",
            "message": "Lancement de la campagne de VACCINATION à Abidjan",
            "created_time": "2026-10-05T08:00:00+0000",
            "permalink_url": "https://www.facebook.com/100/posts/1",
            "shares": {"count": 3},
            "reactions": {"data": [], "summary": {"total_count": 40}},
            "comments": {"data": [], "summary": {"total_count": 2}},
        },
        {"id": "100_2", "message": "Résultats du match", "created_time": "2026-10-05T09:00:00+0000"},
    ]
}
COMMENTS = {
    "data": [
        {
            "id": "1_c1",
            "message": "Enfin !",
            "created_time": "2026-10-05T08:30:00+0000",
            "like_count": 5,
            "from": {"id": "u42"},
        },
        {"message": "Où sont les centres ?", "created_time": "2026-10-05T08:40:00+0000"},  # no id (PPCA)
    ]
}
HASHTAG = {"data": [{"id": "17843857450040591"}]}
MEDIA = {
    "data": [
        {
            "id": "m1",
            "caption": "#vaccination au centre de santé",
            "like_count": 12,
            "comments_count": 1,
            "permalink": "https://www.instagram.com/p/abc/",
            "timestamp": "2026-10-05T07:00:00+0000",
        }
    ]
}


def graph_for(routes, seen, **kwargs):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path.split("/", 2)[2]  # drop "/v25.0/"
        status, body = routes[path]
        return httpx.Response(status, json=body)

    return GraphApi(httpx.AsyncClient(transport=httpx.MockTransport(handler)), "main-token", **kwargs)


def target(source, *keywords):
    return CollectionTarget("w1", source, keywords, ("fr",), ("CI",), limit=10)


def test_hashtags_are_single_words():
    assert hashtag_of("#Côte d'Ivoire") == "côtedivoire"
    assert hashtag_of("vaccination") == "vaccination"
    assert hashtag_of("!!") == ""


async def test_facebook_keeps_posts_mentioning_a_keyword_with_their_comments():
    seen = []
    graph = graph_for(
        {
            "100": (200, {"access_token": "page-token", "id": "100", "name": "Santé Info CI"}),
            "100/posts": (200, POSTS),
            "100_1/comments": (200, COMMENTS),
        },
        seen,
    )
    items = await FacebookPagesCollector(graph, ["100"]).collect(target(SourceKind.FACEBOOK, "vaccination"))

    post, first, second = items
    assert (post.external_id, post.author_handle, post.likes, post.shares, post.comments) == ("100_1", "100", 40, 3, 2)
    assert post.published_at.isoformat() == "2026-10-05T08:00:00+00:00" and post.raw["id"] == "100_1"
    assert (first.external_id, first.text, first.author_handle, first.likes) == ("1_c1", "Enfin !", "u42", 5)
    assert first.url == "https://www.facebook.com/100/posts/1"  # falls back to the post link
    # Where it was found: the Page, for its posts and for the comments under them.
    assert (post.venue, first.venue, second.venue) == ("Santé Info CI",) * 3
    assert second.external_id.startswith("100_1:") and second.author_handle is None
    # The derived id is stable from one collection to the next.
    assert (
        second.external_id
        == "100_1:" + hashlib.sha256("2026-10-05T08:40:00+0000|Où sont les centres ?".encode()).hexdigest()[:24]
    )

    # A managed Page is read with its own Page token.
    assert seen[0].url.params["fields"] == "access_token,name" and seen[0].url.params["access_token"] == "main-token"
    assert {r.url.params["access_token"] for r in seen[1:]} == {"page-token"}
    assert seen[2].url.params["filter"] == "toplevel"


async def test_facebook_public_pages_are_read_with_the_main_token():
    seen = []
    graph = graph_for(
        {
            "200": (400, {"error": {"message": "(#200) Missing permissions", "code": 200}}),
            "200/posts": (200, {"data": []}),
        },
        seen,
    )
    assert await FacebookPagesCollector(graph, ["200"]).collect(target(SourceKind.FACEBOOK, "vaccination")) == []
    assert seen[1].url.params["access_token"] == "main-token"


async def test_instagram_searches_each_hashtag_once():
    seen = []
    graph = graph_for({"ig_hashtag_search": (200, HASHTAG), "17843857450040591/recent_media": (200, MEDIA)}, seen)
    collector = InstagramHashtagCollector(graph, "ig-account")
    (item,) = await collector.collect(target(SourceKind.INSTAGRAM, "Vaccination", "#vaccination"))

    assert (item.source, item.external_id, item.text) == (SourceKind.INSTAGRAM, "m1", "#vaccination au centre de santé")
    assert (item.likes, item.comments, item.author_handle) == (12, 1, None)
    assert item.venue == "#vaccination"  # where it was found: the hashtag
    assert item.url == "https://www.instagram.com/p/abc/"
    search, media = seen
    assert dict(search.url.params) | {"access_token": "-"} == {
        "user_id": "ig-account",
        "q": "vaccination",
        "access_token": "-",
    }
    assert media.url.params["user_id"] == "ig-account" and media.url.params["limit"] == "10"


async def test_graph_errors_are_external_and_never_leak_the_token():
    graph = graph_for(
        {"ig_hashtag_search": (400, {"error": {"message": "Invalid OAuth access token", "code": 190}})}, []
    )
    with pytest.raises(ExternalServiceError) as raised:
        await InstagramHashtagCollector(graph, "ig").collect(target(SourceKind.INSTAGRAM, "vaccin"))
    assert "190" in raised.value.message and "main-token" not in raised.value.message


async def test_app_secret_proof_is_sent_when_configured():
    seen = []
    graph = graph_for({"ig_hashtag_search": (200, {"data": []})}, seen, app_secret="s3cret")
    await InstagramHashtagCollector(graph, "ig").collect(target(SourceKind.INSTAGRAM, "vaccin"))
    expected = hmac.new(b"s3cret", b"main-token", hashlib.sha256).hexdigest()
    assert seen[0].url.params["appsecret_proof"] == expected
