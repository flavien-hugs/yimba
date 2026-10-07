"""YouTube Data API v3 collector, against the documented response shapes (no network)."""

import httpx
import pytest

from yimba.modules.collection.adapters.youtube import YouTubeCollector
from yimba.modules.collection.domain.model import CollectionTarget
from yimba.shared.errors import ExternalServiceError
from yimba.shared.source import SourceKind

TARGET = CollectionTarget("w1", SourceKind.YOUTUBE, ("vaccin",), ("fr",), ("CI",), limit=10)

SEARCH = {
    "items": [
        {
            "id": {"kind": "youtube#video", "videoId": "v1"},
            "snippet": {
                "publishedAt": "2026-10-05T08:00:00Z",
                "channelId": "UC1",
                "title": "Vaccin : l&#39;avis des m&eacute;decins",
                "description": "Reportage",
            },
        },
        {"id": {"kind": "youtube#video", "videoId": "v2"}, "snippet": {"title": "Sans commentaires"}},
        {"id": {"kind": "youtube#channel", "channelId": "UC9"}, "snippet": {"title": "not a video"}},
    ]
}
STATISTICS = {"items": [{"id": "v1", "statistics": {"viewCount": "1200", "likeCount": "30", "commentCount": "4"}}]}
COMMENTS = {
    "items": [
        {
            "snippet": {
                "totalReplyCount": 2,
                "topLevelComment": {
                    "id": "c1",
                    "snippet": {
                        "textDisplay": "Merci pour ce reportage",
                        "authorDisplayName": "@awa",
                        "authorChannelId": {"value": "UCawa"},
                        "likeCount": 5,
                        "publishedAt": "2026-10-05T09:00:00Z",
                    },
                },
            }
        }
    ]
}
COMMENTS_DISABLED = {"error": {"code": 403, "errors": [{"reason": "commentsDisabled"}]}}
QUOTA_EXCEEDED = {"error": {"code": 403, "errors": [{"reason": "quotaExceeded"}]}}


def client_for(routes, seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        resource = request.url.path.rsplit("/", 1)[-1]
        key = (resource, request.url.params.get("videoId"))
        status, body = routes.get(key) or routes[(resource, None)]
        return httpx.Response(status, json=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_collects_videos_with_statistics_and_their_comments():
    seen = []
    client = client_for(
        {
            ("search", None): (200, SEARCH),
            ("videos", None): (200, STATISTICS),
            ("commentThreads", "v1"): (200, COMMENTS),
            ("commentThreads", "v2"): (403, COMMENTS_DISABLED),
        },
        seen,
    )
    items = await YouTubeCollector(client, "secret-key", comment_videos=5).collect(TARGET)

    video, other, comment = items
    assert (video.external_id, video.text) == ("v1", "Vaccin : l'avis des médecins. Reportage")
    assert (video.views, video.likes, video.comments, video.author_handle) == (1200, 30, 4, "UC1")
    assert video.url == "https://www.youtube.com/watch?v=v1"
    assert video.published_at.isoformat() == "2026-10-05T08:00:00+00:00"
    assert other.external_id == "v2" and other.views == 0
    assert (comment.external_id, comment.text, comment.author_handle) == ("c1", "Merci pour ce reportage", "UCawa")
    assert (comment.likes, comment.comments) == (5, 2)
    assert comment.url == "https://www.youtube.com/watch?v=v1&lc=c1"

    search = seen[0].url.params
    assert (search["q"], search["type"], search["regionCode"]) == ("vaccin", "video", "CI")
    assert search["relevanceLanguage"] == "fr"
    assert search["maxResults"] == "10" and search["key"] == "secret-key"
    assert seen[1].url.params["id"] == "v1,v2"


async def test_reads_comments_of_the_first_videos_only():
    seen = []
    client = client_for(
        {
            ("search", None): (200, SEARCH),
            ("videos", None): (200, STATISTICS),
            ("commentThreads", None): (200, COMMENTS),
        },
        seen,
    )
    await YouTubeCollector(client, "k", comment_videos=1).collect(TARGET)
    assert [r.url.params.get("videoId") for r in seen if r.url.path.endswith("commentThreads")] == ["v1"]


async def test_errors_are_external_and_never_leak_the_api_key():
    client = client_for({("search", None): (403, QUOTA_EXCEEDED)})
    with pytest.raises(ExternalServiceError) as raised:
        await YouTubeCollector(client, "secret-key").collect(TARGET)
    assert "quotaExceeded" in raised.value.message and "secret-key" not in raised.value.message

    def unreachable(request):
        raise httpx.ConnectError("boom", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(unreachable))
    with pytest.raises(ExternalServiceError) as raised:
        await YouTubeCollector(client, "secret-key").collect(TARGET)
    assert "secret-key" not in raised.value.message


async def test_a_failing_keyword_keeps_the_others():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("q") == "broken":
            return httpx.Response(500, json={})
        resource = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, json={"search": SEARCH, "videos": STATISTICS, "commentThreads": COMMENTS}[resource])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    target = CollectionTarget("w1", SourceKind.YOUTUBE, ("broken", "vaccin"), ("fr",), ("CI",), limit=10)
    items = await YouTubeCollector(client, "k").collect(target)
    assert {item.external_id for item in items} == {"v1", "v2", "c1"}
