"""Celery + Beat — Django'ning togai/celery.py va togai/tasks.py teng portasi."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "bioscan",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Tashkent",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=4,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    "warm-species-cache": {
        "task": "app.tasks.warm_species_cache",
        "schedule": crontab(minute="*/5"),
    },
    "weekly-tip": {
        "task": "app.tasks.send_weekly_tip",
        "schedule": crontab(hour=18, minute=0, day_of_week=5),  # juma 18:00
    },
}
