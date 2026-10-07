import jwt
import pytest

from tests.conftest import NOW, fast_hasher
from yimba.modules.identity.adapters.passwords import Argon2PasswordHasher
from yimba.modules.identity.adapters.tokens import AUDIENCE, ISSUER, JwtAccessTokens, TokenSecrets
from yimba.modules.identity.domain.model import User
from yimba.shared.errors import Unauthorized

SECRET = "test-secret-long-enough-for-hs512-as-well-0123456789abcdefghijklmnop"


def test_argon2_hashes_verify_and_upgrade():
    hasher = fast_hasher()
    password_hash = hasher.hash("correct horse battery")
    assert hasher.verify(password_hash, "correct horse battery")
    assert not hasher.verify(password_hash, "wrong")
    assert not hasher.verify("not a hash", "correct horse battery")
    hasher.verify_dummy("anything")
    # Stronger settings later: old hashes are flagged for re-hashing at the next login.
    assert Argon2PasswordHasher(time_cost=2, memory_cost=2048, parallelism=1).needs_rehash(password_hash)
    assert not hasher.needs_rehash(password_hash)


def test_access_token_claims():
    user = User.register(email="u@example.org", password_hash="h", now=NOW)
    tokens = JwtAccessTokens(SECRET, lifetime_minutes=15)
    token = tokens.issue(user, NOW)
    claims = jwt.decode(token, SECRET, algorithms=["HS256"], audience=AUDIENCE, options={"verify_exp": False})
    assert (claims["sub"], claims["ver"], claims["typ"], claims["iss"]) == (user.id, 0, "access", ISSUER)
    assert claims["exp"] - claims["iat"] == 900
    assert tokens.read(token, NOW).user_id == user.id


def test_tokens_of_another_kind_or_algorithm_are_refused():
    tokens = JwtAccessTokens(SECRET)
    base = {"sub": "u", "ver": 0, "iss": ISSUER, "aud": AUDIENCE, "iat": int(NOW.timestamp())}
    exp = int(NOW.timestamp()) + 600
    for claims, key, algorithm in [
        ({**base, "exp": exp, "typ": "refresh"}, SECRET, "HS256"),
        ({**base, "exp": exp}, SECRET, "HS256"),  # no type
        ({**base, "exp": exp, "typ": "access", "aud": "someone-else"}, SECRET, "HS256"),
        ({**base, "exp": exp, "typ": "access"}, SECRET + "x", "HS256"),
        ({**base, "exp": exp, "typ": "access"}, SECRET, "HS512"),
    ]:
        with pytest.raises(Unauthorized):
            tokens.read(jwt.encode(claims, key, algorithm=algorithm), NOW)
    unsigned = jwt.encode({**base, "exp": exp, "typ": "access"}, None, algorithm="none")
    with pytest.raises(Unauthorized):
        tokens.read(unsigned, NOW)


def test_refresh_secrets_are_random_and_stored_as_digests():
    secrets = TokenSecrets()
    first, second = secrets.new(), secrets.new()
    assert first != second and len(first) >= 43
    assert secrets.digest(first) == secrets.digest(first) and len(secrets.digest(first)) == 64
