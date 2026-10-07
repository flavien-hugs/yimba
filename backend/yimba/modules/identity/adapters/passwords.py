from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class Argon2PasswordHasher:
    """Argon2id (RFC 9106). Defaults of argon2-cffi: 64 MiB, 3 passes, 4 lanes; hashes record their parameters, so
    raising them later re-hashes each password at its next login."""

    def __init__(self, time_cost: int | None = None, memory_cost: int | None = None, parallelism: int | None = None):
        options = {"time_cost": time_cost, "memory_cost": memory_cost, "parallelism": parallelism}
        self._hasher = PasswordHasher(**{key: value for key, value in options.items() if value is not None})
        self._dummy_hash: str | None = None

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        return self._hasher.check_needs_rehash(password_hash)

    def verify_dummy(self, password: str) -> None:
        if self._dummy_hash is None:
            self._dummy_hash = self._hasher.hash("timing-equaliser-not-a-real-password")
        self.verify(self._dummy_hash, password)
