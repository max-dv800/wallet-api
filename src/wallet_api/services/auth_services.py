from fastapi import HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from wallet_api.core.security import (
    create_access_token,
    create_refresh_token,
    encode_password,
    verify_password,
    verify_token,
)
from wallet_api.dependency import _set_token_cookie
from wallet_api.models.users import User
from wallet_api.schemas.users import UserCreate


async def register_new_user(
    user: UserCreate,
    db: AsyncSession,
):
    exists_user = await db.scalar(select(User).where(User.email == user.email))
    if exists_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already exists!"
        )
    hash_password = encode_password(user.password_hash)
    user.password_hash = hash_password
    data = User(**user.model_dump())
    db.add(data)
    await db.commit()
    await db.refresh(data)
    return data


async def login_user(
    response: Response,
    user: OAuth2PasswordRequestForm,
    db: AsyncSession,
):
    user_exists = await db.scalar(select(User).where(User.email == user.username))
    if not user_exists or not verify_password(user_exists.password_hash, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password!",
        )

    access_token, expires = create_access_token(user.username)
    refresh_token = create_refresh_token(user.username)

    _set_token_cookie(response, access_token, refresh_token)

    return {"expires_in": expires}


async def update_access_token(
    response: Response,
    refresh_token: str | None,
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token!"
        )
    data = verify_token(refresh_token, "refresh")

    user = data.get("name")

    response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh_token")

    new_access_token, expires = create_access_token(user)
    new_refresh_token = create_refresh_token(user)

    _set_token_cookie(response, new_access_token, new_refresh_token)

    return {"expires_in": expires}
