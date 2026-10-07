from __future__ import annotations

from typing import AsyncIterator, Awaitable, Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from yimba.bootstrap import Container
from yimba.modules.alerts.public import AcknowledgeAlert, ListAlerts, SqlAlertRepository
from yimba.modules.identity.public import AccountService, Principal
from yimba.modules.mentions.adapters.persistence import SqlMentionRepository
from yimba.modules.mentions.application.use_cases import ComputeStats, SearchMentions
from yimba.modules.watches.adapters.persistence import SqlWatchRepository
from yimba.modules.watches.application.use_cases import (
    CreateWatch,
    DeleteWatch,
    GetWatch,
    ListWatches,
    PauseOwnerWatches,
    UpdateWatch,
)
from yimba.shared.errors import Unauthorized


def get_container(request: Request) -> Container:
    return request.app.state.container


async def get_session(container: Container = Depends(get_container)) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as session:
        yield session


_bearer = HTTPBearer(auto_error=False, description="Access token from POST /auth/login")


def bearer_token(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    if credentials is None or not credentials.credentials:
        raise Unauthorized("Missing bearer token", code="identity/missing-token")
    return credentials.credentials


def require(*permissions: str) -> Callable[..., Awaitable[Principal]]:
    """Dependency: authenticate the caller and check that they hold every given permission."""

    async def dependency(
        token: str = Depends(bearer_token), container: Container = Depends(get_container)
    ) -> Principal:
        principal = await container.access_control.authenticate(token)
        if permissions:
            await container.access_control.authorize(principal, token, permissions)
        return principal

    return dependency


# ---- use cases bound to the request's session ---------------------------------------------------------------------


def accounts(c: Container = Depends(get_container), s: AsyncSession = Depends(get_session)) -> AccountService:
    return c.accounts(s)


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


def pause_owner_watches(
    c: Container = Depends(get_container), s: AsyncSession = Depends(get_session)
) -> PauseOwnerWatches:
    return PauseOwnerWatches(SqlWatchRepository(s), c.clock)


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
