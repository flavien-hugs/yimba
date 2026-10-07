from datetime import timedelta

import httpx
import pytest

from tests.conftest import NOW
from yimba.entrypoints.api.app import create_app
from yimba.modules.collection.domain.model import CollectedItem
from yimba.shared.source import SourceKind

AUTH = {"Authorization": "Bearer user:u1"}
OTHER = {"Authorization": "Bearer user:u2"}


class StaticCollector:
    source = SourceKind.NEWS

    def __init__(self, items):
        self.items = items

    async def collect(self, target):
        return self.items


@pytest.fixture
async def client(container):
    app = create_app(settings=container.settings, container=container)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def create_watch(client, **overrides):
    payload = {"name": "Santé et vaccination", "keywords": ["vaccin"], "sources": ["news"], "alert_min_mentions": 2}
    payload.update(overrides)
    return await client.post("/watches", json=payload, headers=AUTH)


async def test_ping_needs_no_credentials(client):
    assert (await client.get("/@ping")).json() == {"status": "ok"}


async def test_authentication_and_permissions(client):
    assert (await client.get("/watches")).status_code == 401
    assert (await client.get("/watches", headers={"Authorization": "Bearer nope"})).status_code == 401
    denied = await client.get("/watches", headers={"Authorization": "Bearer user:u1|deny=watch:can-read"})
    assert denied.status_code == 403 and denied.json()["code"] == "yimba/forbidden"


async def test_watch_lifecycle(client):
    created = await create_watch(client)
    assert created.status_code == 201
    watch = created.json()
    assert watch["slug"] == "sante-et-vaccination" and watch["frequency_minutes"] == 60

    assert (await create_watch(client)).status_code == 409

    listed = (await client.get("/watches", headers=AUTH)).json()
    assert listed["total"] == 1 and listed["items"][0]["id"] == watch["id"]

    patched = await client.patch(
        f"/watches/{watch['id']}", json={"active": False, "frequency_minutes": 15}, headers=AUTH
    )
    assert patched.json()["active"] is False and patched.json()["frequency_minutes"] == 15

    assert (
        await client.patch(f"/watches/{watch['id']}", json={"frequency_minutes": 7}, headers=AUTH)
    ).status_code == 422
    assert (await client.patch(f"/watches/{watch['id']}", json={"keywords": []}, headers=AUTH)).status_code == 422

    assert (await client.delete(f"/watches/{watch['id']}", headers=AUTH)).status_code == 204
    assert (await client.get(f"/watches/{watch['id']}", headers=AUTH)).status_code == 404


async def test_validation_errors_are_422(client):
    assert (await create_watch(client, keywords=[])).status_code == 422
    assert (await create_watch(client, sources=["myspace"])).status_code == 422
    assert (await create_watch(client, alert_negative_share=1.5)).status_code == 422


async def test_watches_are_private_to_their_owner(client):
    watch = (await create_watch(client)).json()
    for path in (
        f"/watches/{watch['id']}",
        f"/watches/{watch['id']}/mentions",
        f"/watches/{watch['id']}/stats",
        f"/watches/{watch['id']}/alerts",
    ):
        assert (await client.get(path, headers=OTHER)).status_code == 404
    assert (await client.get("/watches", headers=OTHER)).json()["total"] == 0


async def test_collect_then_read_mentions_stats_and_alerts(client, container):
    watch = (await create_watch(client)).json()
    container.collectors = {
        SourceKind.NEWS: StaticCollector(
            [
                CollectedItem(
                    SourceKind.NEWS, "1", "Bravo, super campagne de vaccination", published_at=NOW - timedelta(hours=2)
                ),
                CollectedItem(
                    SourceKind.NEWS,
                    "2",
                    "Honte et scandale: rupture de doses",
                    published_at=NOW - timedelta(hours=1),
                    venue="Fraternité Matin",
                ),
                CollectedItem(
                    SourceKind.NEWS,
                    "3",
                    "Arnaque, la colère monte",
                    author_handle="@awa",
                    published_at=NOW - timedelta(minutes=30),
                ),
            ]
        )
    }

    async with container.session_factory() as session:
        run = await container.collect_for_watch(session).execute(watch["id"], SourceKind.NEWS)
    assert (run.status.value, run.fetched, run.stored) == ("succeeded", 3, 3)
    async with container.session_factory() as session:
        alert = await container.evaluate_alerts(session).execute(watch["id"])
    assert alert and alert.negative == 2

    mentions = (await client.get(f"/watches/{watch['id']}/mentions?sentiment=negative", headers=AUTH)).json()
    assert mentions["total"] == 2
    assert {m["sentiment"] for m in mentions["items"]} == {"negative"}
    assert all("awa" not in str(m["author_ref"]) for m in mentions["items"])
    assert {m["venue"] for m in mentions["items"]} == {None, "Fraternité Matin"}

    places = (await client.get(f"/watches/{watch['id']}/places", headers=AUTH)).json()
    assert [p["district"] for p in places["districts"]][:2] == ["Denguélé", "Savanes"] and len(
        places["districts"]
    ) == 14
    assert (places["located"], places["analyzed"]) == (0, 3)
    themes = (await client.get(f"/watches/{watch['id']}/themes?limit=3", headers=AUTH)).json()
    assert themes == {"themes": [], "analyzed": 3}  # no word comes back in three conversations
    assert (await client.get("/watches/nope/themes", headers=AUTH)).status_code == 404

    assert (await client.get(f"/watches/{watch['id']}/mentions?sentiment=bogus", headers=AUTH)).status_code == 422
    assert (await client.get(f"/watches/{watch['id']}/mentions?q=bravo", headers=AUTH)).json()["total"] == 1

    stats = (await client.get(f"/watches/{watch['id']}/stats?group_by=source", headers=AUTH)).json()
    assert stats["totals"]["total"] == 3 and stats["totals"]["negative_share"] == pytest.approx(0.6667, abs=1e-3)
    assert stats["buckets"][0]["key"] == "news" and stats["emotions"]["anger"] >= 1

    alerts = (await client.get(f"/watches/{watch['id']}/alerts", headers=AUTH)).json()
    assert alerts["total"] == 1 and alerts["items"][0]["status"] == "open"
    ack = await client.post(f"/watches/{watch['id']}/alerts/{alerts['items'][0]['id']}/acknowledge", headers=AUTH)
    assert ack.json()["status"] == "acknowledged"
    assert (await client.post(f"/watches/{watch['id']}/alerts/missing/acknowledge", headers=AUTH)).status_code == 404
