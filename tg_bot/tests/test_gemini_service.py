from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.services.gemini_service import GeminiService, IntentResult


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.lrange = AsyncMock(return_value=[])
    redis.lpush = AsyncMock(return_value=1)
    redis.ltrim = AsyncMock()
    redis.expire = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def mock_gemini_client():
    client = AsyncMock()
    return client


@pytest.fixture
def gemini_service(mock_gemini_client, mock_redis):
    return GeminiService(client=mock_gemini_client, redis=mock_redis)


class TestExtractIntent:
    @pytest.mark.asyncio
    async def test_extracts_query_and_budget(self, gemini_service, mock_gemini_client):
        raw_response = json.dumps({
            "query": "Samsung Galaxy S24",
            "budget": 200000,
            "preferences": {"brand": "Samsung"},
        })
        mock_gemini_client.generate = AsyncMock(return_value=raw_response)

        intent = await gemini_service.extract_intent(
            telegram_id=123456,
            user_message="Найди Samsung Galaxy S24 до 200000 тенге",
        )

        assert intent.query == "Samsung Galaxy S24"
        assert intent.budget == 200000
        assert intent.preferences.get("brand") == "Samsung"

    @pytest.mark.asyncio
    async def test_handles_null_budget(self, gemini_service, mock_gemini_client):
        raw_response = json.dumps({
            "query": "наушники",
            "budget": None,
            "preferences": {},
        })
        mock_gemini_client.generate = AsyncMock(return_value=raw_response)

        intent = await gemini_service.extract_intent(
            telegram_id=123456,
            user_message="Хочу наушники",
        )

        assert intent.budget is None
        assert intent.query == "наушники"

    @pytest.mark.asyncio
    async def test_graceful_fallback_on_invalid_json(
        self, gemini_service, mock_gemini_client
    ):
        mock_gemini_client.generate = AsyncMock(return_value="не JSON вовсе")

        intent = await gemini_service.extract_intent(
            telegram_id=123456,
            user_message="планшет",
        )

        assert isinstance(intent, IntentResult)
        assert intent.query is not None


class TestParseIntent:
    def test_strips_markdown_fences(self):
        raw = "```json\n{\"query\": \"ноутбук\", \"budget\": null, \"preferences\": {}}\n```"
        result = GeminiService._parse_intent(raw)
        assert result.query == "ноутбук"
        assert result.budget is None

    def test_handles_plain_json(self):
        raw = '{"query": "телефон", "budget": 150000, "preferences": {}}'
        result = GeminiService._parse_intent(raw)
        assert result.query == "телефон"
        assert result.budget == 150000
