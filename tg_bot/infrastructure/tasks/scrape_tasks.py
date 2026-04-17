from __future__ import annotations

import asyncio
from typing import Optional

from celery import Task
from celery.utils.log import get_task_logger

from infrastructure.tasks.celery_app import celery_app

logger = get_task_logger(__name__)


class AsyncTask(Task):
    abstract = True
    _loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="infrastructure.tasks.scrape_tasks.scrape_kaspi",
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def scrape_kaspi(
    self,
    query: str,
    budget: Optional[float] = None,
) -> dict:
    logger.info(f"scrape_kaspi.start query={query} budget={budget}")

    async def _run():
        from core.config import get_settings
        from infrastructure.external.kaspi_scraper import KaspiScraper
        from infrastructure.db.session import create_session_factory
        from infrastructure.repositories.product_repository import ProductRepository

        settings = get_settings()
        scraper = KaspiScraper(
            timeout=settings.scraper_timeout,
            max_retries=settings.scraper_max_retries,
        )
        products = await scraper.scrape(query=query, budget=budget)

        if products:
            session_factory = await create_session_factory(settings)
            repo = ProductRepository(session_factory)
            saved = await repo.bulk_create(products)
            logger.info(f"scrape_kaspi.saved count={len(saved)}")
            return {"status": "ok", "count": len(saved)}

        return {"status": "ok", "count": 0}

    return self.run_async(_run())


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="infrastructure.tasks.scrape_tasks.cleanup_old_products",
    max_retries=2,
)
def cleanup_old_products(self, older_than_hours: int = 24) -> dict:
    logger.info(f"cleanup_old_products.start older_than_hours={older_than_hours}")

    async def _run():
        from core.config import get_settings
        from infrastructure.db.session import create_session_factory
        from infrastructure.repositories.product_repository import ProductRepository

        settings = get_settings()
        session_factory = await create_session_factory(settings)
        repo = ProductRepository(session_factory)
        deleted = await repo.delete_old_scrapes(older_than_hours=older_than_hours)
        return {"status": "ok", "deleted": deleted}

    return self.run_async(_run())
