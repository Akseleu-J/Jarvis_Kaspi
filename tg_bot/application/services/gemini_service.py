from __future__ import annotations

import json
import re
from typing import Optional

from core.logger import get_logger
from infrastructure.cache.redis_client import RedisClient
from infrastructure.external.gemini_client import GeminiClient, GeminiClientError

logger = get_logger(__name__)

_MEMORY_KEY = "gemini:memory:{telegram_id}"
_MEMORY_TTL = 3600
_MEMORY_MAX_MESSAGES = 20

_INTENT_SYSTEM_PROMPT = """
Ты — умный ассистент для поиска товаров на Kaspi.kz.
Твоя задача — извлечь из запроса пользователя структурированный JSON без Markdown, только чистый JSON.

Формат ответа (строго JSON, без пояснений):
{
  "query": "<поисковый запрос на русском>",
  "budget": <число или null>,
  "preferences": {
    "brand": "<бренд или null>",
    "category": "<категория или null>",
    "color": "<цвет или null>",
    "size": "<размер или null>"
  }
}
""".strip()

_CHAT_SYSTEM_PROMPT = """
Ты — дружелюбный помощник по шопингу на Kaspi.kz.
Отвечай кратко и по делу, на русском языке.
Помогай пользователю найти товар, уточнить бюджет и предпочтения.
""".strip()


class IntentResult:
    __slots__ = ("query", "budget", "preferences")

    def __init__(
        self,
        query: str,
        budget: Optional[int],
        preferences: dict,
    ) -> None:
        self.query = query
        self.budget = budget
        self.preferences = preferences

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "budget": self.budget,
            "preferences": self.preferences,
        }


class GeminiService:
    def __init__(
        self,
        client: GeminiClient,
        redis: RedisClient,
    ) -> None:
        self._client = client
        self._redis = redis

    async def extract_intent(self, telegram_id: int, user_message: str) -> IntentResult:
        history = await self._get_history(telegram_id)

        try:
            raw = await self._client.generate(
                prompt=user_message,
                history=history,
                system_prompt=_INTENT_SYSTEM_PROMPT,
            )
            intent = self._parse_intent(raw)
            await self._append_history(telegram_id, "user", user_message)
            await self._append_history(telegram_id, "model", raw)
            logger.info(
                "gemini.intent_extracted",
                telegram_id=telegram_id,
                query=intent.query,
                budget=intent.budget,
            )
            return intent
        except GeminiClientError as exc:
            logger.error("gemini.intent_error", telegram_id=telegram_id, error=str(exc))
            return IntentResult(
                query=user_message,
                budget=None,
                preferences={},
            )

    async def chat(self, telegram_id: int, user_message: str) -> str:
        history = await self._get_history(telegram_id)

        try:
            response = await self._client.generate(
                prompt=user_message,
                history=history,
                system_prompt=_CHAT_SYSTEM_PROMPT,
            )
            await self._append_history(telegram_id, "user", user_message)
            await self._append_history(telegram_id, "model", response)
            return response
        except GeminiClientError as exc:
            logger.error("gemini.chat_error", telegram_id=telegram_id, error=str(exc))
            return "Извините, произошла ошибка. Попробуйте ещё раз."

    async def clear_history(self, telegram_id: int) -> None:
        key = _MEMORY_KEY.format(telegram_id=telegram_id)
        await self._redis.delete(key)
        logger.info("gemini.history_cleared", telegram_id=telegram_id)

    async def _get_history(self, telegram_id: int) -> list[dict]:
        key = _MEMORY_KEY.format(telegram_id=telegram_id)
        raw_messages = await self._redis.lrange(key, 0, -1)
        history = []
        for raw in raw_messages:
            try:
                history.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return history

    async def _append_history(
        self,
        telegram_id: int,
        role: str,
        content: str,
    ) -> None:
        key = _MEMORY_KEY.format(telegram_id=telegram_id)
        entry = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        await self._redis.lpush(key, entry)
        await self._redis.ltrim(key, 0, _MEMORY_MAX_MESSAGES - 1)
        await self._redis.expire(key, _MEMORY_TTL)

    @staticmethod
    def _parse_intent(raw: str) -> IntentResult:
        cleaned = raw.strip()
        cleaned = re.sub(r"```json|```", "", cleaned).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                return IntentResult(query=cleaned, budget=None, preferences={})

        return IntentResult(
            query=data.get("query", cleaned),
            budget=int(data["budget"]) if data.get("budget") else None,
            preferences=data.get("preferences", {}),
        )
