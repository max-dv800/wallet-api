import json
import uuid
from datetime import datetime
from decimal import Decimal

import redis
from redis.asyncio import from_url

from wallet_api.core.config import settings

sync_redis_cache = redis.from_url(settings.redis.redis_url, decode_responses=True)


def json_serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, uuid.UUID):
        return obj.hex
    raise TypeError(f"Type {type(obj)} is not serialize")


class RedisCache:
    def __init__(self):
        self._client = from_url(settings.redis.redis_url)

    async def set(self, key, val, ex, nx=False):
        return await self._client.set(
            key, json.dumps(val, default=json_serialize), ex=ex, nx=nx
        )

    async def get(self, key):
        val = await self._client.get(key)
        if val is not None:
            return json.loads(val)

    async def delete(self, key):
        await self._client.delete(key)

    async def exists(self, key):
        return await self._client.exists(key)


cache = RedisCache()
