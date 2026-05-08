"""Celery konfiguratsiyasi — fon vazifalari uchun.

Redis broker (.env: CELERY_BROKER_URL=redis://127.0.0.1:6379/3) ishlatadi.
Worker'ni ishga tushirish:
  celery -A togai worker -l info --concurrency=4

Bu loyihada Celery quyidagilar uchun ishlatiladi:
- Yillik PDF kitob generatsiyasi (yearbook)
- Toplu tarjima (translate_batch)
- Periodik ma'lumot yangilanishi (kelajakda Celery Beat)
"""
from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "togai.settings")

app = Celery("togai")

# Sozlamalarni Django settings'dan oladi (CELERY_ prefiks bilan)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Har bir Django app'ning tasks.py'ini avtomatik topish
app.autodiscover_tasks()


# Celery Beat — periodik vazifalar
app.conf.beat_schedule = {
    # Har kun ertalab 7:00 — bugungi ekish/sug'orish eslatmalari
    "crop-plan-reminders": {
        "task": "crops.tasks.send_daily_reminders",
        "schedule": crontab(hour=7, minute=0),
    },
    # Har juma 18:00 — haftalik tabiat ma'lumotlari (broadcast)
    "weekly-nature-tip": {
        "task": "togai.tasks.send_weekly_tip",
        "schedule": crontab(hour=18, minute=0, day_of_week=5),
    },
}
app.conf.timezone = "Asia/Tashkent"


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
