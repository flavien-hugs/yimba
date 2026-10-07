from __future__ import annotations

from typing import AsyncIterator, Awaitable, Callable

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from yimba.bootstrap import Container
from yimba.modules.alerts.public import AcknowledgeAlert, ListAlerts, SqlAlertRepository
from yimba.modules.identity.public import Principal
from yimba.modules.mentions.adapters.persistence import SqlMentionRepository
from yimba.modules.mentions.application.use_cases import ComputeStats, SearchMentions
from yimba.modules.watches.adapters.persistence import SqlWatchRepository
from yimba.modules.watches.application.use_cases import CreateWatch, DeleteWatch, GetWatch, ListWatches, UpdateWatch
from yimba.shared.errors import Unauthorized


def get_container(request: Request) -> Container:
    return request.app.state.container


async def get_session(container: Container = Depends(get_container)) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as session:
        yield session


def bearer_token(authorization: str | None = Header(default=None)) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise Unauthorized("Missing bearer token", code="identity/missing-token")
    return token


def require(*permissions: str) -> Callable[..., Awaitable[Principal]]:
    """Dependency: authenticate the caller and check that they hold every given permission."""

    async def dependency(
        token: str = Depends(bearer_token), container: Container = Depends(get_container)
    ) -> Principal:
        principal = await container.access_control.authenticate(token)
        if permissions:
            await container.access_control.authorize(token, permissions)
        return principal

    return dependency


# ---- use cases bound to the request's session ---------------------------------------------------------------------


def create_watch(c: Container = Depends(get_container), s: AsyncSession = Depends(get_session)) -> CreateWatch:
    return CreateWatch(SqlWatchRepository(s), c.clock)


def get_watch(s: AsyncSession = Depends(get_session)) -> GetWatch:
    return GetWatch(SqlWatchRepository(s))


def list_watches(s: AsyncSession = Depends(get_session)) -> ListWatches:
    return ListWatches(SqlWatchRepository(s))


def update_watch(c: Container = Depends(get_container), s: AsyncSession = Depends(get_session)) -> UpdateWatch:
    return UpdateWatch(SqlWatchRepository(s), c.clock)


def delete_watch(s: AsyncSession = Depends(get_session)) -> DeleteWatch:
    return DeleteWatch(SqlWatchRepository(s))


def search_mentions(s: AsyncSession = Depends(get_session)) -> SearchMentions:
    return SearchMentions(SqlMentionRepository(s))


def compute_stats(s: AsyncSession = Depends(get_session)) -> ComputeStats:
    return ComputeStats(SqlMentionRepository(s))


def list_alerts(s: AsyncSession = Depends(get_session)) -> ListAlerts:
    return ListAlerts(SqlAlertRepository(s))


def acknowledge_alert(
    c: Container = Depends(get_container), s: AsyncSession = Depends(get_session)
) -> AcknowledgeAlert:
    return AcknowledgeAlert(SqlAlertRepository(s), c.clock)
