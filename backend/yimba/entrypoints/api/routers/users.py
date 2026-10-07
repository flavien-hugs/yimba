from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from yimba.entrypoints.api import deps, permissions
from yimba.entrypoints.api.schemas import PageOut, UserOut, UserUpdateIn, page_of
from yimba.modules.identity.public import AccountService, Principal
from yimba.modules.watches.application.use_cases import PauseOwnerWatches
from yimba.shared.pagination import PageParams

router = APIRouter(prefix="/users", tags=["Users (admin)"])


@router.get("", response_model=PageOut[UserOut], summary="List the accounts")
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Email contains"),
    include_deleted: bool = Query(False, description="Also list the deleted accounts"),
    principal: Principal = Depends(deps.require(permissions.USER_READ)),
    accounts: AccountService = Depends(deps.accounts),
):
    return page_of(await accounts.list_users(PageParams(page, size), search, include_deleted), UserOut.of)


@router.patch("/{user_id}", response_model=UserOut, summary="Change the role of an account, or disable it")
async def update_user(
    user_id: str,
    payload: UserUpdateIn,
    principal: Principal = Depends(deps.require(permissions.USER_MANAGE)),
    accounts: AccountService = Depends(deps.accounts),
) -> UserOut:
    return UserOut.of(await accounts.update_user(user_id, role=payload.role, active=payload.active))


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an account (soft delete: kept in the database, its watches paused)",
)
async def delete_user(
    user_id: str,
    principal: Principal = Depends(deps.require(permissions.USER_MANAGE)),
    accounts: AccountService = Depends(deps.accounts),
    pause_watches: PauseOwnerWatches = Depends(deps.pause_owner_watches),
) -> Response:
    await accounts.delete_user(user_id)
    await pause_watches.execute(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
