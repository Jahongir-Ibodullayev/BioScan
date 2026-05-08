"""Crops Celery tasks — kunlik eslatma yuborish."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from celery import shared_task

log = logging.getLogger(__name__)


@shared_task
def send_daily_reminders():
    """Har kun ertalab 7:00 da — ekish/sug'orish eslatmalari.

    Ko'riladigan rejalar:
      - 3 kun oldin: "3 kundan keyin {ekin} ekish"
      - Ekish kuni: "Bugun {ekin} ekish"
      - Sug'orish kuni (water_freq_days asosida): "Bugun sug'oring"
    """
    from .models import CropPlan
    from togai.services.fcm import send_to_user

    today = date.today()
    sent = 0

    plans = CropPlan.objects.filter(notify=True, completed_at__isnull=True).select_related("user", "crop")
    for plan in plans:
        msg = None
        days_to_plant = (plan.planned_plant_date - today).days

        if days_to_plant == 3:
            msg = (f"⏳ {plan.crop.name_uz} ekishingizga 3 kun qoldi", "Tuproqni tayyorlang.")
        elif days_to_plant == 1:
            msg = (f"📅 Ertaga {plan.crop.name_uz} ekish", "Bugun urug'larni tayyorlang.")
        elif days_to_plant == 0:
            msg = (f"🌱 Bugun {plan.crop.name_uz} ekish vaqti", "Yaxshi hosil!")
        elif days_to_plant < 0 and not plan.expected_harvest_date:
            # Sug'orish jadvali — har water_freq_days kunda eslatma
            days_since_plant = abs(days_to_plant)
            if plan.crop.water_freq_days and days_since_plant % plan.crop.water_freq_days == 0:
                msg = (f"💧 {plan.crop.name_uz}'ni sug'oring", "Sug'orish kuni bugundir.")

        if msg:
            try:
                send_to_user(plan.user, msg[0], msg[1], data={"plan_id": plan.id})
                sent += 1
            except Exception as e:
                log.warning("plan reminder failed pk=%s: %s", plan.pk, e)

    log.info("daily_reminders: %s yuborildi", sent)
    return sent
