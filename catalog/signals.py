"""Auto-bust the species view cache whenever the data changes.

Without this, admins editing a species would see stale data for up
to 10 minutes (the cache TTL). Wildcard delete via Redis SCAN keeps
DB write paths fast (~1 ms).
"""
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Species


def _bust():
    try:
        # Redis backend supports delete_pattern via django-redis;
        # fall back to clear() on plain backends.
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern("species:v2:*")
        else:
            # Iterate keys ourselves on django.core.cache.backends.redis.RedisCache
            client = getattr(cache, "_cache", None)
            redis = client and getattr(client, "get_client", lambda: None)()
            if redis is not None:
                for k in redis.scan_iter("*species:v2:*"):
                    redis.delete(k)
            else:
                cache.clear()
    except Exception:
        pass


@receiver(post_save, sender=Species)
def _on_species_save(sender, **kwargs):
    _bust()


@receiver(post_delete, sender=Species)
def _on_species_delete(sender, **kwargs):
    _bust()
