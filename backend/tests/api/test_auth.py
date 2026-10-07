"""The authentication routes end to end, with real local accounts and tokens."""

import httpx
import pytest

from yimba.entrypoints.api.app import create_app
from yimba.modules.identity.domain.model import Role

PASSWORD = "correct horse battery"


@pytest.fixture
async def client(local_container):
    app = create_app(settings=local_container.settings, container=local_container)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def register_and_login(client, email):
    assert (await client.post("/auth/register", json={"email": email, "password": PASSWORD})).status_code == 201
    response = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return response.json()


def bearer(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_register_login_and_use_the_api(client):
    created = await client.post(
        "/auth/register", json={"email": "Awa@Example.org", "password": PASSWORD, "full_name": "Awa"}
    )
    assert created.status_code == 201
    assert created.json()["email"] == "awa@example.org" and created.json()["role"] == "user"
    assert "password" not in str(created.json())

    assert (
        await client.post("/auth/register", json={"email": "awa@example.org", "password": PASSWORD})
    ).status_code == 409
    assert (
        await client.post("/auth/register", json={"email": "x@example.org", "password": "short"})
    ).status_code == 422
    assert (await client.post("/auth/login", json={"email": "awa@example.org", "password": "nope"})).status_code == 401

    tokens = (await client.post("/auth/login", json={"email": "awa@example.org", "password": PASSWORD})).json()
    assert set(tokens) == {"access_token", "token_type", "expires_in", "refresh_token"}
    me = await client.get("/auth/me", headers=bearer(tokens))
    assert me.status_code == 200 and me.json()["email"] == "awa@example.org"

    watch = await client.post(
        "/watches", json={"name": "Santé", "keywords": ["vaccin"], "sources": ["news"]}, headers=bearer(tokens)
    )
    assert watch.status_code == 201
    listed = await client.get("/watches", headers=bearer(tokens))
    assert listed.json()["total"] == 1


async def test_missing_or_bad_tokens_are_401(client):
    assert (await client.get("/auth/me")).status_code == 401
    assert (await client.get("/auth/me", headers={"Authorization": "Bearer nope"})).status_code == 401
    assert (await client.get("/watches", headers={"Authorization": "Basic abc"})).status_code == 401


async def test_refresh_logout_and_password_change(client):
    tokens = await register_and_login(client, "u@example.org")

    refreshed = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    replay = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401

    tokens = await register_and_login(client, "v@example.org")
    assert (await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})).status_code == 204
    assert (await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})).status_code == 401

    tokens = (await client.post("/auth/login", json={"email": "v@example.org", "password": PASSWORD})).json()
    wrong = await client.post(
        "/auth/password", json={"current_password": "nope", "new_password": "x" * 12}, headers=bearer(tokens)
    )
    assert wrong.status_code == 403
    changed = await client.post(
        "/auth/password", json={"current_password": PASSWORD, "new_password": "x" * 12}, headers=bearer(tokens)
    )
    assert changed.status_code == 204
    assert (await client.get("/auth/me", headers=bearer(tokens))).status_code == 401


async def test_user_administration_is_for_admins(client, local_container):
    user = await register_and_login(client, "u@example.org")
    assert (await client.get("/users", headers=bearer(user))).status_code == 403

    async with local_container.session_factory() as session:
        await local_container.accounts(session).register("a@example.org", PASSWORD, role=Role.ADMIN, by_admin=True)
    admin = (await client.post("/auth/login", json={"email": "a@example.org", "password": PASSWORD})).json()

    listed = await client.get("/users", params={"search": "u@"}, headers=bearer(admin))
    assert listed.status_code == 200 and [u["email"] for u in listed.json()["items"]] == ["u@example.org"]
    target = listed.json()["items"][0]["id"]

    disabled = await client.patch(f"/users/{target}", json={"active": False}, headers=bearer(admin))
    assert disabled.status_code == 200 and disabled.json()["active"] is False
    assert (await client.get("/auth/me", headers=bearer(user))).status_code == 401

    me = (await client.get("/auth/me", headers=bearer(admin))).json()
    last_admin = await client.patch(f"/users/{me['id']}", json={"role": "user"}, headers=bearer(admin))
    assert last_admin.status_code == 409
    assert (await client.patch("/users/missing", json={"active": False}, headers=bearer(admin))).status_code == 404


async def test_closed_registration(client, local_container):
    local_container.auth_policy = type(local_container.auth_policy)(registration_enabled=False)
    response = await client.post("/auth/register", json={"email": "u@example.org", "password": PASSWORD})
    assert response.status_code == 403 and response.json()["code"] == "identity/registration-closed"


async def test_swagger_offers_bearer_authentication(client):
    schema = (await client.get("/openapi.json")).json()
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"


async def test_admins_soft_delete_accounts_and_pause_their_watches(client, local_container):
    user = await register_and_login(client, "u@example.org")
    watch = await client.post(
        "/watches", json={"name": "Santé", "keywords": ["vaccin"], "sources": ["news"]}, headers=bearer(user)
    )
    user_id = (await client.get("/auth/me", headers=bearer(user))).json()["id"]
    async with local_container.session_factory() as session:
        await local_container.accounts(session).register("a@example.org", PASSWORD, role=Role.ADMIN, by_admin=True)
    admin = (await client.post("/auth/login", json={"email": "a@example.org", "password": PASSWORD})).json()

    assert (await client.delete(f"/users/{user_id}", headers=bearer(user))).status_code == 403
    assert (await client.delete(f"/users/{user_id}", headers=bearer(admin))).status_code == 204
    assert (await client.delete(f"/users/{user_id}", headers=bearer(admin))).status_code == 404
    assert (await client.delete("/users/missing", headers=bearer(admin))).status_code == 404

    assert (await client.get("/auth/me", headers=bearer(user))).status_code == 401
    listed = (await client.get("/users", params={"include_deleted": "true"}, headers=bearer(admin))).json()
    deleted = next(u for u in listed["items"] if u["id"] == user_id)
    assert deleted["deleted_at"] is not None and deleted["active"] is False
    assert user_id not in [u["id"] for u in (await client.get("/users", headers=bearer(admin))).json()["items"]]

    from yimba.modules.watches.adapters.persistence import SqlWatchRepository

    async with local_container.session_factory() as session:
        assert (await SqlWatchRepository(session).get(watch.json()["id"])).active is False
