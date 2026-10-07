from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from yimba.entrypoints.api import deps, permissions
from yimba.entrypoints.api.schemas import PageOut, UserOut, UserUpdateIn, page_of
from yimba.modules.identity.public import AccountService, Principal
from yimba.shared.pagination import PageParams

router = APIRouter(prefix="/users", tags=["Users (admin)"])


@router.get("", response_model=PageOut[UserOut], summary="List the accounts")
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Email contains"),
    principal: Principal = Depends(deps.require(permissions.USER_READ)),
    accounts: AccountService = Depends(deps.accounts),
):
    return page_of(await accounts.list_users(PageParams(page, size), search), UserOut.of)


@router.patch("/{user_id}", response_model=UserOut, summary="Change the role of an account, or disable it")
async def update_user(
    user_id: str,
    payload: UserUpdateIn,
    principal: Principal = Depends(deps.require(permissions.USER_MANAGE)),
    accounts: AccountService = Depends(deps.accounts),
) -> UserOut:
    return UserOut.of(await accounts.update_user(user_id, role=payload.role, active=payload.active))
