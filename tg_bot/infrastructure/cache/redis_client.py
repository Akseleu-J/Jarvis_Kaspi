from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as aioredis

from core.logger import get_logger

logger = get_logger(__name__)


class RedisClient:
    def __init__(self, url: str) -> None:
        self._url = url
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        self._client = aioredis.from_url(
            self._url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        await self._client.ping()
        logger.info("redis.ping_ok")

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> aioredis.Redis:
        assert self._client is not None, "Redis not connected"
        return self._client

    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        if ttl:
            await self.client.setex(key, ttl, value)
        else:
            await self.client.set(key, value)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self.client.exists(key))

    async def incr(self, key: str) -> int:
        return await self.client.incr(key)

    async def expire(self, key: str, ttl: int) -> None:
        await self.client.expire(key, ttl)

    async def get_json(self, key: str) -> Optional[Any]:
        raw = await self.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        await self.set(key, json.dumps(value, ensure_ascii=False), ttl)

    async def lpush(self, key: str, *values: str) -> int:
        return await self.client.lpush(key, *values)

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        return await self.client.lrange(key, start, end)

    async def ltrim(self, key: str, start: int, end: int) -> None:
        await self.client.ltrim(key, start, end)

    async def pipeline_incr_expire(self, key: str, ttl: int) -> int:
        async with self.client.pipeline(transaction=True) as pipe:
            await pipe.incr(key)
            await pipe.expire(key, ttl)
            results = await pipe.execute()
        return results[0]
