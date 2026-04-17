from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.services.search_service import SearchService
from domain.entities.product import Product


def _make_product(title="Test Phone", price=100000.0) -> Product:
    return Product(
        title=title,
        price=price,
        url="https://kaspi.kz/shop/p/test",
        source="kaspi",
    )


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.search = AsyncMock(return_value=[])
    repo.bulk_create = AsyncMock(side_effect=lambda p: p)
    return repo


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.pipeline_incr_expire = AsyncMock(return_value=1)
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def search_service(mock_repo, mock_redis):
    return SearchService(
        product_repository=mock_repo,
        redis=mock_redis,
        scraper_timeout=5,
        scraper_max_retries=1,
    )


class TestSearch:
    @pytest.mark.asyncio
    async def test_returns_db_results_when_available(
        self, search_service, mock_repo
    ):
        products = [_make_product("iPhone 15"), _make_product("Samsung S24")]
        mock_repo.search = AsyncMock(return_value=products)

        results = await search_service.search(query="телефон", use_cache=False)

        assert len(results) == 2
        mock_repo.search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_circuit_open_returns_empty(
        self, search_service, mock_redis, mock_repo
    ):
        mock_redis.get = AsyncMock(return_value="5")
        mock_repo.search = AsyncMock(return_value=[])

        results = await search_service.search(query="телефон", use_cache=False)

        assert results == []
