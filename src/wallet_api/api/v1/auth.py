from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm

from wallet_api.core.database import SessionDb
from wallet_api.dependency import CurrentUser, _clear_token_cookie
from wallet_api.schemas.users import TokenResponse, UserCreate, UserResponse
from wallet_api.services.auth_services import (
    login_user,
    register_new_user,
    update_access_token,
)
from wallet_api.utils.limiter import limiter

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("20/minute")
async def user_register(
    request: Request,
    user: UserCreate,
    db: SessionDb,
):
    user_create = await register_new_user(user, db)

    return user_create


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
async def user_login(
    request: Request,
    response: Response,
    db: SessionDb,
    user: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    login = await login_user(response=response, user=user, db=db)

    return login


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def new_access_token(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
):
    new_token = await update_access_token(response, refresh_token)

    return new_token


@router.get("/me", response_model=UserResponse)
@limiter.limit("10/minute")
async def me(request: Request, user: CurrentUser):
    return user


@router.post("/logout", status_code=204)
async def logout(response: Response, refresh_token: str | None = Cookie(default=None)):
    _clear_token_cookie(response)
