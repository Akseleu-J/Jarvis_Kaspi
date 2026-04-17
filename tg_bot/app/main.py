from __future__ import annotations

import asyncio
import signal
import sys

import uvloop
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from core.config import get_settings
from core.container import Container
from core.logger import configure_logging, get_logger
from infrastructure.tasks.scheduler import build_scheduler
from presentation.handlers.user_handlers import router as user_router
from presentation.middlewares.error_middleware import ErrorMiddleware
from presentation.middlewares.logging_middleware import LoggingMiddleware
from presentation.middlewares.rate_limit_middleware import RateLimitMiddleware

logger = get_logger(__name__)


def _make_services_injector(container: Container):
    from aiogram import BaseMiddleware
    from aiogram.types import TelegramObject
    from typing import Callable, Awaitable, Any

    class ServicesMiddleware(BaseMiddleware):
        async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any],
        ) -> Any:
            data["gemini_service"] = container.gemini_service
            data["search_service"] = container.search_service
            data["user_service"] = container.user_service
            return await handler(event, data)

    return ServicesMiddleware()


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("bot.starting", environment=settings.environment)

    container = Container(settings=settings)
    await container.init()

    storage = RedisStorage.from_url(
        settings.redis_url,
        key_builder=None,
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=storage)

    dp.message.middleware(ErrorMiddleware())
    dp.callback_query.middleware(ErrorMiddleware())

    dp.message.middleware(
        LoggingMiddleware(session_factory=container.db_session_factory)
    )

    dp.message.middleware(
        RateLimitMiddleware(
            redis=container.redis_client,
            max_requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window,
        )
    )

    services_mw = _make_services_injector(container)
    dp.message.middleware(services_mw)
    dp.callback_query.middleware(services_mw)

    dp.include_router(user_router)

    scheduler = build_scheduler(container)
    scheduler.start()
    logger.info("scheduler.started")

    loop = asyncio.get_event_loop()

    def _shutdown(signum, frame):
        logger.info("bot.shutdown_signal", signal=signum)
        scheduler.shutdown(wait=False)
        loop.create_task(_graceful_shutdown(bot, dp, container))

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        logger.info("bot.polling_start")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            close_bot_session=True,
        )
    finally:
        scheduler.shutdown(wait=False)
        await container.close()
        await bot.session.close()
        logger.info("bot.stopped")


async def _graceful_shutdown(bot, dp, container: Container) -> None:
    await dp.stop_polling()
    await container.close()
    await bot.session.close()
    logger.info("bot.graceful_shutdown_done")


if __name__ == "__main__":
    if sys.platform != "win32":
        uvloop.install()
    asyncio.run(main())
