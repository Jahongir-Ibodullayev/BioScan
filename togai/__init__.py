"""BioScan Django package — Celery'ni Django boot paytida yuklaymiz."""
from .celery import app as celery_app

__all__ = ("celery_app",)
