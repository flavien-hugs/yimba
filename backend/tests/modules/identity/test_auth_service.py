import httpx
import pytest

from yimba.modules.identity.adapters.auth_service import AuthServiceAccessControl
from yimba.modules.identity.domain.model import Principal
from yimba.shared.errors import ExternalServiceError, Forbidden, Unauthorized

PRINCIPAL = Principal(id="u1")


def access(handler):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AuthServiceAccessControl(client, "http://auth/userinfo", "http://auth/check-access")


async def test_authenticate_returns_the_principal():
    seen = {}

    def handler(request):
        seen["query"] = dict(request.url.params)
        return httpx.Response(200, json={"active": True, "user_info": {"_id": "u1", "email": "a@b.ci"}})

    principal = await access(handler).authenticate("tok")
    assert (principal.id, principal.email) == ("u1", "a@b.ci")
    assert seen["query"] == {"token": "tok"}


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401),
        httpx.Response(403),
        httpx.Response(200, json={"active": False}),
        httpx.Response(200, json={"active": True}),
    ],
)
async def test_authenticate_rejects_invalid_tokens(response):
    with pytest.raises(Unauthorized):
        await access(lambda request: response).authenticate("tok")


async def test_auth_service_outages_are_external_errors():
    with pytest.raises(ExternalServiceError):
        await access(lambda request: httpx.Response(500)).authenticate("tok")

    def down(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(ExternalServiceError):
        await access(down).authorize(PRINCIPAL, "tok", ["watch:can-read"])


async def test_authorize_forwards_token_and_permissions():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["permissions"] = request.url.params.get_list("permission")
        return httpx.Response(200)

    await access(handler).authorize(PRINCIPAL, "tok", ["a:b", "c:d"])
    assert seen == {"auth": "Bearer tok", "permissions": ["a:b", "c:d"]}


async def test_authorize_maps_denials():
    with pytest.raises(Forbidden):
        await access(lambda request: httpx.Response(403)).authorize(PRINCIPAL, "tok", ["a:b"])
    with pytest.raises(Unauthorized):
        await access(lambda request: httpx.Response(401)).authorize(PRINCIPAL, "tok", ["a:b"])
