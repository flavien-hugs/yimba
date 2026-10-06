"""Bluesky collector, against the documented AT Protocol response shapes (no network)."""

import json

import httpx
import pytest

from yimba.modules.collection.adapters import bluesky
from yimba.modules.collection.adapters.bluesky import BlueskyCollector
from yimba.modules.collection.domain.model import CollectionTarget
from yimba.shared.errors import ExternalServiceError
from yimba.shared.source import SourceKind

TARGET = CollectionTarget("w1", SourceKind.BLUESKY, ("vaccin",), ("fr",), ("CI",), limit=10)

POST = {
    "uri": "at://did:plc:abc/app.bsky.feed.post/3kxyz",
    "author": {"did": "did:plc:abc", "handle": "awa.bsky.social"},
    "record": {"text": "Campagne de vaccination ratée", "createdAt": "2026-10-05T08:00:00.000Z", "langs": ["fr"]},
    "likeCount": 4,
    "repostCount": 2,
    "quoteCount": 1,
    "replyCount": 3,
}


class FakeBluesky:
    def __init__(self, *, expire_first_token=False, login_status=200):
        self.logins = 0
        self.searches = []
        self.expire_first_token = expire_first_token
        self.login_status = login_status

    def __call__(self, request: httpx.Request) -> httpx.Response:
        method = request.url.path.rsplit("/", 1)[-1]
        if method == "com.atproto.server.createSession":
            self.logins += 1
            assert json.loads(request.content) == {"identifier": "yimba.bsky.social", "password": "app-pass"}
            if self.login_status != 200:
                return httpx.Response(self.login_status, json={"error": "AuthenticationRequired"})
            return httpx.Response(200, json={"accessJwt": f"token-{self.logins}", "did": "did:plc:me"})
        self.searches.append(request)
        if self.expire_first_token and request.headers["Authorization"] == "Bearer token-1":
            return httpx.Response(400, json={"error": "ExpiredToken", "message": "Token has expired"})
        return httpx.Response(200, json={"posts": [POST], "cursor": "1"})


@pytest.fixture(autouse=True)
def no_shared_sessions():
    bluesky._sessions.clear()
    yield
    bluesky._sessions.clear()


def collector(fake):
    client = httpx.AsyncClient(transport=httpx.MockTransport(fake))
    return BlueskyCollector(client, "yimba.bsky.social", "app-pass")


async def test_searches_each_keyword_and_maps_posts():
    fake = FakeBluesky()
    (item,) = await collector(fake).collect(TARGET)

    assert (item.source, item.external_id, item.text) == (
        SourceKind.BLUESKY,
        "at://did:plc:abc/app.bsky.feed.post/3kxyz",
        "Campagne de vaccination ratée",
    )
    assert item.author_handle == "did:plc:abc"
    assert item.url == "https://bsky.app/profile/awa.bsky.social/post/3kxyz"
    assert item.published_at.isoformat() == "2026-10-05T08:00:00+00:00"
    assert (item.likes, item.shares, item.comments) == (4, 3, 3)

    (search,) = fake.searches
    assert search.url.host == "bsky.social" and search.headers["Authorization"] == "Bearer token-1"
    assert dict(search.url.params) == {"q": "vaccin", "sort": "latest", "limit": "10", "lang": "fr"}


async def test_language_filter_only_with_a_single_language():
    fake = FakeBluesky()
    target = CollectionTarget("w1", SourceKind.BLUESKY, ("vaccin",), ("fr", "en"), ("CI",), limit=10)
    await collector(fake).collect(target)
    assert "lang" not in fake.searches[0].url.params


async def test_login_is_reused_across_collectors_and_renewed_when_expired():
    fake = FakeBluesky()
    await collector(fake).collect(TARGET)
    await collector(fake).collect(TARGET)  # a new task builds a new collector: same session
    assert fake.logins == 1

    bluesky._sessions.clear()
    fake = FakeBluesky(expire_first_token=True)
    items = await collector(fake).collect(TARGET)
    assert len(items) == 1 and fake.logins == 2
    assert [r.headers["Authorization"] for r in fake.searches] == ["Bearer token-1", "Bearer token-2"]


async def test_failures_are_external_errors():
    with pytest.raises(ExternalServiceError):
        await collector(FakeBluesky(login_status=401)).collect(TARGET)

    def unreachable(request):
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(ExternalServiceError):
        await collector(unreachable).collect(TARGET)
