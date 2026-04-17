from __future__ import annotations

import uuid
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from core.logger import get_logger, set_correlation_id
from infrastructure.db.base import LogModel
from infrastructure.db.session import get_session

logger = get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        cid = str(uuid.uuid4())
        set_correlation_id(cid)

        telegram_id: int | None = None
        username: str | None = None
        action = "unknown"

        if isinstance(event, Message):
            if event.from_user:
                telegram_id = event.from_user.id
                username = event.from_user.username
            action = event.text or event.content_type or "message"

        logger.info(
            "request.received",
            telegram_id=telegram_id,
            action=action[:200] if action else None,
            handler=data.get("handler", {}).get("__name__", "unknown"),
        )

        try:
            result = await handler(event, data)
            return result
        finally:
            await self._persist_log(
                telegram_id=telegram_id,
                username=username,
                action=action[:255] if action else "unknown",
                correlation_id=cid,
            )

    async def _persist_log(
        self,
        telegram_id: int | None,
        username: str | None,
        action: str,
        correlation_id: str,
    ) -> None:
        try:
            async with get_session(self._session_factory) as session:
                log = LogModel(
                    telegram_id=telegram_id,
                    username=username,
                    action=action,
                    correlation_id=correlation_id,
                )
                session.add(log)
        except Exception as exc:
            logger.error("logging_middleware.persist_error", error=str(exc))
