from __future__ import annotations

import logging
from typing import Sequence

import httpx

from yimba.modules.identity.domain.model import Principal
from yimba.shared.errors import ExternalServiceError, Forbidden, Unauthorized

logger = logging.getLogger(__name__)


class AuthServiceAccessControl:
    """Talks to the auth microservice.

    Contract kept from the legacy code:
      * ``GET {userinfo_url}?token=<jwt>`` -> ``{"active": bool, "user_info": {"_id": str, "email": str, ...}}``
      * ``GET {check_access_url}`` with the caller's ``Authorization`` header and one ``permission`` query
        parameter per required permission -> 2xx when allowed, 401/403 otherwise.

    The second call was implemented in a private shared library that is not part of this repository:
    confirm its exact parameters against the auth service before going to production. This is the only
    place that needs to change if they differ.
    """

    def __init__(self, client: httpx.AsyncClient, userinfo_url: str, check_access_url: str) -> None:
        self._client = client
        self._userinfo_url = userinfo_url
        self._check_access_url = check_access_url

    async def authenticate(self, token: str) -> Principal:
        try:
            response = await self._client.get(self._userinfo_url, params={"token": token})
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Auth service unreachable", code="identity/auth-unreachable") from exc
        if response.status_code in (401, 403):
            raise Unauthorized("Invalid or expired token", code="identity/invalid-token")
        if not response.is_success:
            raise ExternalServiceError(f"Auth service answered {response.status_code}", code="identity/auth-error")
        payload = response.json()
        user = payload.get("user_info") or {}
        if not payload.get("active") or not user.get("_id"):
            raise Unauthorized("Invalid or expired token", code="identity/invalid-token")
        return Principal(id=str(user["_id"]), email=user.get("email"))

    async def authorize(self, token: str, permissions: Sequence[str]) -> None:
        try:
            response = await self._client.get(
                self._check_access_url,
                headers={"Authorization": f"Bearer {token}"},
                params=[("permission", p) for p in permissions],
            )
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Auth service unreachable", code="identity/auth-unreachable") from exc
        if response.status_code == 401:
            raise Unauthorized("Invalid or expired token", code="identity/invalid-token")
        if response.status_code == 403:
            raise Forbidden("Missing permission", code="identity/forbidden")
        if not response.is_success:
            raise ExternalServiceError(f"Auth service answered {response.status_code}", code="identity/auth-error")
