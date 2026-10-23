from fastapi import Request
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from wallet_api.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis.redis_url,
    default_limits=["200/minute"],
)


def rate_limit_handler(request: Request, exc: Exception) -> Response:
    if isinstance(exc, RateLimitExceeded):
        return _rate_limit_exceeded_handler(request, exc)
    return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
