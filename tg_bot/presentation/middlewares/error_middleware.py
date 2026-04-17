from __future__ import annotations

import traceback
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from core.logger import get_logger

logger = get_logger(__name__)

_USER_ERROR_TEXT = (
    "⚠️ Произошла внутренняя ошибка. Мы уже работаем над её устранением.\n"
    "Попробуйте снова через несколько секунд."
)


class ErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as exc:
            tb = traceback.format_exc()
            telegram_id = None
            if isinstance(event, Message) and event.from_user:
                telegram_id = event.from_user.id

            logger.error(
                "unhandled_exception",
                telegram_id=telegram_id,
                error=str(exc),
                traceback=tb,
            )

            try:
                if isinstance(event, Message):
                    await event.answer(_USER_ERROR_TEXT)
            except Exception:
                pass

            return None
