from __future__ import annotations

from celery import Celery

from core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "tg_bot_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Almaty",
    enable_utc=True,
    task_soft_time_limit=90,
    task_time_limit=120,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=200,
    task_routes={
        "infrastructure.tasks.scrape_tasks.scrape_kaspi": {"queue": "scraping"},
        "infrastructure.tasks.scrape_tasks.cleanup_old_products": {"queue": "maintenance"},
    },
)

celery_app.autodiscover_tasks(["infrastructure.tasks"])
