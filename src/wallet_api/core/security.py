import hmac
from time import time

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from wallet_api.core.config import settings

ph = PasswordHasher()
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"


def encode_password(password: str) -> str:
    return ph.hash(password)


def verify_password(hash_password: str, origin_password: str) -> bool:
    try:
        return ph.verify(hash_password, origin_password)
    except VerifyMismatchError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password!",
        )


def create_access_token(user_name):
    payload = {
        "sub": user_name,
        "name": user_name,
        "type": "access",
        "exp": time() + settings.MAX_ACCESS_AGE,
        "iat": time(),
    }
    access_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return access_token, payload.get("exp")


def create_refresh_token(user_name):
    payload = {
        "sub": user_name,
        "name": user_name,
        "type": "refresh",
        "exp": time() + settings.MAX_REFRESH_AGE,
        "iat": time(),
    }
    refresh_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return refresh_token


def verify_token(token, expected_token):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token!"
        )
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if data.get("type") != expected_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not expected type token!"
            )
        return data
    except (jwt.exceptions.InvalidTokenError, jwt.exceptions.ExpiredSignatureError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token!"
        )


ALLOW_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost",
    "http://127.0.0.1",
]


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, excluded_paths: frozenset[str] = frozenset()):
        super().__init__(app)
        self.excluded_paths = excluded_paths

    async def dispatch(self, request: Request, call_next):
        if request.method in (
            "GET",
            "HEAD",
            "OPTIONS",
            "TRACE",
        ) or not request.url.path.startswith("/api/"):
            return await call_next(request)
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        if request.url.path == "/api/v1/auth/login":
            origin = request.headers.get("origin")
            if origin is None or origin not in ALLOW_ORIGINS:
                return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
            return await call_next(request)

        header = request.headers.get("X-CSRF-Token")
        cookie = request.cookies.get("__Host-csrf_token")
        if not header or not cookie:
            return JSONResponse({"detail": "missing_token"}, status_code=403)

        if not hmac.compare_digest(header, cookie):
            return JSONResponse({"detail": "token_mismatch"}, status_code=403)

        return await call_next(request)
