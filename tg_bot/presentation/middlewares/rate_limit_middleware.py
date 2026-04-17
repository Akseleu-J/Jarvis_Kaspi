from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from core.logger import get_logger
from infrastructure.cache.redis_client import RedisClient

logger = get_logger(__name__)

_RATE_KEY = "rate:{telegram_id}"


class RateLimitMiddleware(BaseMiddleware):
    def __init__(
        self,
        redis: RedisClient,
        max_requests: int = 10,
        window_seconds: int = 60,
    ) -> None:
        self._redis = redis
        self._max_requests = max_requests
        self._window = window_seconds
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        telegram_id = event.from_user.id
        key = _RATE_KEY.format(telegram_id=telegram_id)

        count = await self._redis.pipeline_incr_expire(key, self._window)

        if count > self._max_requests:
            logger.warning(
                "rate_limit.exceeded",
                telegram_id=telegram_id,
                count=count,
                max=self._max_requests,
            )
            await event.answer(
                f"⏳ Слишком много запросов. Подождите немного.",
                parse_mode=None,
            )
            return None

        return await handler(event, data)
