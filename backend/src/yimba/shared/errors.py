from __future__ import annotations


class DomainError(Exception):
    """Base class of every error raised on purpose by the domain or application layers.

    ``code`` is a stable, machine readable identifier exposed to API clients.
    """

    code = "yimba/error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class InvalidInput(DomainError):
    code = "yimba/invalid-input"


class NotFound(DomainError):
    code = "yimba/not-found"


class Conflict(DomainError):
    code = "yimba/conflict"


class Unauthorized(DomainError):
    code = "yimba/unauthorized"


class Forbidden(DomainError):
    code = "yimba/forbidden"


class ExternalServiceError(DomainError):
    """A system we depend on (scraping provider, auth service...) failed."""

    code = "yimba/external-service-error"
