from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from yimba import __version__
from yimba.bootstrap import Container
from yimba.config import Settings, get_settings
from yimba.entrypoints.api.routers import alerts, auth, health, mentions, users, watches
from yimba.infrastructure.error_tracking import init_error_tracking
from yimba.shared.errors import (
    Conflict,
    DomainError,
    ExternalServiceError,
    Forbidden,
    InvalidInput,
    NotFound,
    Unauthorized,
)

logger = logging.getLogger(__name__)

_STATUS = {
    NotFound: 404,
    Conflict: 409,
    InvalidInput: 422,
    Unauthorized: 401,
    Forbidden: 403,
    ExternalServiceError: 502,
}


def _status_for(error: DomainError) -> int:
    for error_type, status_code in _STATUS.items():
        if isinstance(error, error_type):
            return status_code
    return 400


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()
    init_error_tracking(settings.SENTRY_DSN, settings.APP_ENV, "api")
    owns_container = container is None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container or Container(settings)
        try:
            yield
        finally:
            if owns_container:
                await app.state.container.aclose()

    app = FastAPI(
        title="Yimba API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/yimba/docs" if settings.APP_ENV not in ("production", "prod") else None,
        redoc_url="/yimba/redoc" if settings.APP_ENV in ("production", "prod") else None,
    )
    if container is not None:
        app.state.container = container

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials="*" not in settings.cors_origins,
    )

    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, error: DomainError) -> JSONResponse:
        if isinstance(error, ExternalServiceError):
            logger.error("External service error: %s", error.message)
        return JSONResponse(status_code=_status_for(error), content={"code": error.code, "message": error.message})

    for module in (health, auth, users, watches, mentions, alerts):
        app.include_router(module.router)
    return app
