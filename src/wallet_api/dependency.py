import secrets
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from wallet_api.core.config import settings
from wallet_api.core.database import db_session
from wallet_api.core.security import verify_token
from wallet_api.models.users import User


async def get_currency_user(
    db: Annotated[AsyncSession, Depends(db_session)],
    access_token: str | None = Cookie(default=None),
):

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No authenticate!"
        )

    try:
        decode_token = verify_token(access_token, "access")
        user_email = decode_token.get("name")
    except (TypeError, ValueError, HTTPException):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token!"
        )
    user = await db.scalar(select(User).where(User.email == user_email))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found!"
        )
    return user


def _set_token_cookie(response: Response, access: str, refresh: str):
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=settings.MAX_ACCESS_AGE,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/v1/auth/refresh",
        max_age=settings.MAX_REFRESH_AGE,
    )

    response.set_cookie(
        key="__Host-csrf_token",
        value=secrets.token_urlsafe(32),
        httponly=False,
        secure=True,
        samesite="lax",
        path="/",
        max_age=settings.MAX_REFRESH_AGE,
    )


def _clear_token_cookie(response: Response):

    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")
    response.delete_cookie(key="__Host-csrf_token", path="/")


CurrentUser = Annotated[User, Depends(get_currency_user)]
