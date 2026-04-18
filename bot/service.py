"""Business logic — species picker (mock AI), user sessions."""
import random
from asgiref.sync import sync_to_async

from catalog.models import Species


@sync_to_async
def pick_species_for_photo(_photo_bytes: bytes | None = None) -> tuple[Species | None, float]:
    """Mock AI identification.

    Hozir tasodifiy Species qaytaradi. Kelajakda:
      - Plant.id API
      - Custom TensorFlow model
      - iNaturalist computer vision
    """
    candidates = list(Species.objects.all())
    if not candidates:
        return None, 0.0
    picked = random.choice(candidates)
    confidence = round(random.uniform(0.82, 0.99), 2)
    return picked, confidence


@sync_to_async
def get_species(slug: str) -> Species | None:
    return Species.objects.filter(slug=slug).first()
