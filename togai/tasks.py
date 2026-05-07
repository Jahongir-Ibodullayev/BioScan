"""BioScan Celery vazifalari (background jobs)."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def identify_species_async(self, image_b64: str, mime: str = "image/jpeg") -> dict:
    """Background AI vision: rasmni aniqlash. Frontend job_id orqali kuzatadi."""
    import base64
    from togai.integrations import identify_species_from_image
    try:
        image_bytes = base64.b64decode(image_b64)
        return identify_species_from_image(image_bytes, mime=mime)
    except Exception as e:
        log.exception("identify_species_async failed: %s", e)
        # Retry 30s'dan keyin
        raise self.retry(exc=e, countdown=30)


@shared_task
def translate_batch_async(items: list[tuple[str, str]]) -> dict:
    """Background batch translation."""
    from togai.services.translate import translate_batch
    return translate_batch(items)


@shared_task
def warm_cache():
    """Periodik issiqlik vazifasi: hot endpointlarni cache'ga yuklash.
    Celery Beat orqali har 5 daqiqada bir chaqirilishi mumkin.
    """
    from django.core.cache import cache
    from catalog.models import Species
    # Top 50 turlarni cache'ga
    top = list(Species.objects.all()[:50].values("id", "slug", "name", "latin"))
    cache.set("togai:hot:species:top50", top, 600)
    return {"warmed": len(top)}
