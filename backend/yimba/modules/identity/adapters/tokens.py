from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from yimba.modules.identity.application.ports import AccessClaims
from yimba.modules.identity.domain.model import User
from yimba.shared.errors import Unauthorized

ISSUER = "yimba"
AUDIENCE = "yimba-api"


def _invalid() -> Unauthorized:
    return Unauthorized("Invalid or expired token", code="identity/invalid-token")


class JwtAccessTokens:
    """HS256-signed JWT access tokens: user id, token version, issue and expiry times. Expiry is checked against the
    application clock rather than the system clock."""

    def __init__(self, secret: str, lifetime_minutes: int = 15) -> None:
        self._secret = secret
        self._lifetime = timedelta(minutes=lifetime_minutes)

    @property
    def lifetime_seconds(self) -> int:
        return int(self._lifetime.total_seconds())

    def issue(self, user: User, now: datetime) -> str:
        claims = {
            "sub": user.id,
            "ver": user.token_version,
            "typ": "access",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int((now + self._lifetime).timestamp()),
        }
        return jwt.encode(claims, self._secret, algorithm="HS256")

    def read(self, token: str, now: datetime) -> AccessClaims:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                audience=AUDIENCE,
                issuer=ISSUER,
                options={"require": ["sub", "ver", "exp", "iat"], "verify_exp": False, "verify_iat": False},
            )
        except jwt.PyJWTError as exc:
            raise _invalid() from exc
        if claims.get("typ") != "access" or not isinstance(claims.get("ver"), int):
            raise _invalid()
        if datetime.fromtimestamp(claims["exp"], tz=timezone.utc) <= now:
            raise _invalid()
        return AccessClaims(user_id=str(claims["sub"]), token_version=claims["ver"])


class TokenSecrets:
    """Refresh tokens: 256 random bits for the client; only their SHA-256 digest is stored."""

    def new(self) -> str:
        return secrets.token_urlsafe(32)

    def digest(self, secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()
