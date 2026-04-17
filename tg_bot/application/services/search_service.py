from __future__ import annotations

import asyncio
import json
from typing import List, Optional

from core.logger import get_logger
from domain.entities.product import Product
from domain.interfaces.repositories import AbstractProductRepository
from infrastructure.cache.redis_client import RedisClient
from infrastructure.external.kaspi_scraper import KaspiScraper, ScraperError

logger = get_logger(__name__)

_SEARCH_CACHE_KEY = "search:results:{query}:{budget}"
_SEARCH_CACHE_TTL = 600
_CIRCUIT_BREAKER_KEY = "circuit:kaspi_scraper"
_CIRCUIT_BREAKER_THRESHOLD = 5
_CIRCUIT_BREAKER_TTL = 120


class SearchService:
    def __init__(
        self,
        product_repository: AbstractProductRepository,
        redis: RedisClient,
        scraper_timeout: int = 60,
        scraper_max_retries: int = 3,
    ) -> None:
        self._repo = product_repository
        self._redis = redis
        self._scraper = KaspiScraper(
            timeout=scraper_timeout,
            max_retries=scraper_max_retries,
        )

    async def search(
        self,
        query: str,
        budget: Optional[float] = None,
        use_cache: bool = True,
    ) -> List[Product]:
        cache_key = _SEARCH_CACHE_KEY.format(
            query=query.lower().strip(),
            budget=int(budget) if budget else "any",
        )

        if use_cache:
            cached = await self._get_cached(cache_key)
            if cached is not None:
                logger.info("search.cache_hit", query=query)
                return cached

        db_results = await self._repo.search(query=query, budget=budget, limit=10)
        if db_results:
            logger.info("search.db_hit", query=query, count=len(db_results))
            await self._set_cached(cache_key, db_results)
            return db_results

        if await self._is_circuit_open():
            logger.warning("search.circuit_open", query=query)
            return []

        try:
            products = await asyncio.wait_for(
                self._scraper.scrape(query=query, budget=budget),
                timeout=70,
            )
            if products:
                saved = await self._repo.bulk_create(products)
                await self._set_cached(cache_key, saved)
                await self._reset_circuit()
                logger.info("search.scraped", query=query, count=len(saved))
                return saved
            return []
        except (ScraperError, asyncio.TimeoutError) as exc:
            await self._trip_circuit()
            logger.error("search.scrape_failed", query=query, error=str(exc))
            return []

    async def _get_cached(self, key: str) -> Optional[List[Product]]:
        raw = await self._redis.get(key)
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            return [Product(**item) for item in data]
        except Exception:
            return None

    async def _set_cached(self, key: str, products: List[Product]) -> None:
        data = [p.to_dict() for p in products]
        await self._redis.set(key, json.dumps(data, ensure_ascii=False, default=str), _SEARCH_CACHE_TTL)

    async def _is_circuit_open(self) -> bool:
        val = await self._redis.get(_CIRCUIT_BREAKER_KEY)
        if val is None:
            return False
        try:
            return int(val) >= _CIRCUIT_BREAKER_THRESHOLD
        except ValueError:
            return False

    async def _trip_circuit(self) -> None:
        count = await self._redis.pipeline_incr_expire(_CIRCUIT_BREAKER_KEY, _CIRCUIT_BREAKER_TTL)
        logger.warning("search.circuit_tripped", count=count)

    async def _reset_circuit(self) -> None:
        await self._redis.delete(_CIRCUIT_BREAKER_KEY)
