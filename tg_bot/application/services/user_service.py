from __future__ import annotations

import json
from typing import Optional

from aiogram.types import User as TelegramUser

from core.logger import get_logger
from domain.entities.user import User
from domain.interfaces.repositories import AbstractUserRepository
from infrastructure.cache.redis_client import RedisClient

logger = get_logger(__name__)

_USER_CACHE_KEY = "user:{telegram_id}"
_USER_CACHE_TTL = 300


class UserService:
    def __init__(
        self,
        user_repository: AbstractUserRepository,
        redis: RedisClient,
    ) -> None:
        self._repo = user_repository
        self._redis = redis

    async def get_or_register(self, tg_user: TelegramUser) -> tuple[User, bool]:
        cache_key = _USER_CACHE_KEY.format(telegram_id=tg_user.id)
        cached = await self._redis.get_json(cache_key)
        if cached is not None:
            return self._deserialize(cached), False

        entity = User.create(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            language_code=tg_user.language_code or "ru",
        )
        user, created = await self._repo.get_or_create(entity)
        await self._redis.set_json(cache_key, self._serialize(user), _USER_CACHE_TTL)

        if created:
            logger.info("user.registered", telegram_id=user.telegram_id, username=user.username)

        return user, created

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        cache_key = _USER_CACHE_KEY.format(telegram_id=telegram_id)
        cached = await self._redis.get_json(cache_key)
        if cached is not None:
            return self._deserialize(cached)
        user = await self._repo.get_by_telegram_id(telegram_id)
        if user:
            await self._redis.set_json(cache_key, self._serialize(user), _USER_CACHE_TTL)
        return user

    async def is_banned(self, telegram_id: int) -> bool:
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            return False
        return user.is_banned

    async def invalidate_cache(self, telegram_id: int) -> None:
        cache_key = _USER_CACHE_KEY.format(telegram_id=telegram_id)
        await self._redis.delete(cache_key)

    @staticmethod
    def _serialize(user: User) -> dict:
        return {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "language_code": user.language_code,
            "is_active": user.is_active,
            "is_banned": user.is_banned,
        }

    @staticmethod
    def _deserialize(data: dict) -> User:
        from datetime import datetime
        return User(
            id=data.get("id"),
            telegram_id=data["telegram_id"],
            username=data.get("username"),
            first_name=data["first_name"],
            last_name=data.get("last_name"),
            language_code=data.get("language_code", "ru"),
            is_active=data.get("is_active", True),
            is_banned=data.get("is_banned", False),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
