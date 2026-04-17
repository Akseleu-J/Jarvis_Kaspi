from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from core.logger import get_logger

logger = get_logger(__name__)


def build_scheduler(container) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Almaty")

    scheduler.add_job(
        _cleanup_old_products,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_old_products",
        replace_existing=True,
        kwargs={"container": container},
    )

    scheduler.add_job(
        _warmup_cache,
        trigger=IntervalTrigger(hours=6),
        id="warmup_cache",
        replace_existing=True,
        kwargs={"container": container},
    )

    return scheduler


async def _cleanup_old_products(container) -> None:
    try:
        from infrastructure.tasks.scrape_tasks import cleanup_old_products
        cleanup_old_products.delay(older_than_hours=24)
        logger.info("scheduler.cleanup_triggered")
    except Exception as exc:
        logger.error("scheduler.cleanup_error", error=str(exc))


async def _warmup_cache(container) -> None:
    try:
        popular_queries = ["телефон", "наушники", "ноутбук", "планшет"]
        from application.services.search_service import SearchService
        service: SearchService = container.search_service
        for query in popular_queries:
            await service.search(query=query, use_cache=False)
        logger.info("scheduler.warmup_done", queries=popular_queries)
    except Exception as exc:
        logger.error("scheduler.warmup_error", error=str(exc))
