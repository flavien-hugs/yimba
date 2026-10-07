from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from yimba.entrypoints.api import deps
from yimba.entrypoints.api.schemas import LoginIn, PasswordChangeIn, RefreshIn, RegisterIn, TokenOut, UserOut
from yimba.modules.identity.public import AccountService, Principal

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Create an account")
async def register(payload: RegisterIn, accounts: AccountService = Depends(deps.accounts)) -> UserOut:
    return UserOut.of(await accounts.register(payload.email, payload.password, payload.full_name))


@router.post("/login", response_model=TokenOut, summary="Get an access token and a refresh token")
async def login(payload: LoginIn, accounts: AccountService = Depends(deps.accounts)) -> TokenOut:
    return TokenOut.of(await accounts.login(payload.email, payload.password))


@router.post("/refresh", response_model=TokenOut, summary="Exchange a refresh token for a new pair")
async def refresh(payload: RefreshIn, accounts: AccountService = Depends(deps.accounts)) -> TokenOut:
    return TokenOut.of(await accounts.refresh(payload.refresh_token))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="End the session of a refresh token")
async def logout(payload: RefreshIn, accounts: AccountService = Depends(deps.accounts)) -> Response:
    await accounts.logout(payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut, summary="The account of the caller")
async def me(
    principal: Principal = Depends(deps.require()), accounts: AccountService = Depends(deps.accounts)
) -> UserOut:
    return UserOut.of(await accounts.profile(principal.id))


@router.post(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the password (ends every other session)",
)
async def change_password(
    payload: PasswordChangeIn,
    principal: Principal = Depends(deps.require()),
    accounts: AccountService = Depends(deps.accounts),
) -> Response:
    await accounts.change_password(principal.id, payload.current_password, payload.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
