from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.config import Settings, get_settings
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Container:
    settings: Settings = field(default_factory=get_settings)

    _db_session_factory: Optional[object] = field(default=None, init=False, repr=False)
    _redis_client: Optional[object] = field(default=None, init=False, repr=False)
    _gemini_client: Optional[object] = field(default=None, init=False, repr=False)
    _user_repository: Optional[object] = field(default=None, init=False, repr=False)
    _product_repository: Optional[object] = field(default=None, init=False, repr=False)
    _gemini_service: Optional[object] = field(default=None, init=False, repr=False)
    _search_service: Optional[object] = field(default=None, init=False, repr=False)
    _user_service: Optional[object] = field(default=None, init=False, repr=False)

    async def init(self) -> None:
        from infrastructure.db.session import create_session_factory
        from infrastructure.cache.redis_client import RedisClient
        from infrastructure.external.gemini_client import GeminiClient
        from infrastructure.repositories.user_repository import UserRepository
        from infrastructure.repositories.product_repository import ProductRepository
        from application.services.gemini_service import GeminiService
        from application.services.search_service import SearchService
        from application.services.user_service import UserService

        self._db_session_factory = await create_session_factory(self.settings)
        logger.info("database.connected")

        redis = RedisClient(self.settings.redis_url)
        await redis.connect()
        self._redis_client = redis
        logger.info("redis.connected")

        self._gemini_client = GeminiClient(
            api_key=self.settings.gemini_api_key,
            max_retries=self.settings.gemini_max_retries,
            timeout=self.settings.gemini_timeout,
        )

        self._user_repository = UserRepository(self._db_session_factory)
        self._product_repository = ProductRepository(self._db_session_factory)

        self._gemini_service = GeminiService(
            client=self._gemini_client,
            redis=self._redis_client,
        )

        self._search_service = SearchService(
            product_repository=self._product_repository,
            redis=self._redis_client,
            scraper_timeout=self.settings.scraper_timeout,
            scraper_max_retries=self.settings.scraper_max_retries,
        )

        self._user_service = UserService(
            user_repository=self._user_repository,
            redis=self._redis_client,
        )

        logger.info("container.initialized")

    async def close(self) -> None:
        if self._redis_client:
            await self._redis_client.close()
        logger.info("container.closed")

    @property
    def db_session_factory(self) -> object:
        assert self._db_session_factory is not None, "Container not initialized"
        return self._db_session_factory

    @property
    def redis_client(self) -> object:
        assert self._redis_client is not None, "Container not initialized"
        return self._redis_client

    @property
    def gemini_service(self) -> object:
        assert self._gemini_service is not None, "Container not initialized"
        return self._gemini_service

    @property
    def search_service(self) -> object:
        assert self._search_service is not None, "Container not initialized"
        return self._search_service

    @property
    def user_service(self) -> object:
        assert self._user_service is not None, "Container not initialized"
        return self._user_service
