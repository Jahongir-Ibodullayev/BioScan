"""Ads endpoint testlari — active ad + click tracking."""
from django.utils import timezone

from rest_framework.test import APITestCase

from .models import Ad


class AdTests(APITestCase):
    def test_active_ad_returns_204_when_none(self):
        resp = self.client.get("/api/ads/active/?slot=splash&platform=web")
        self.assertEqual(resp.status_code, 204)

    def test_active_ad_returns_active_one(self):
        Ad.objects.create(
            title="Test reklama", slot=Ad.SLOT_SPLASH, platform=Ad.PLATFORM_WEB,
            headline="Sotuvi", body="Tezda sotib oling",
            target_url="https://example.com",
            is_active=True, priority=10, starts_at=timezone.now(),
        )
        resp = self.client.get("/api/ads/active/?slot=splash&platform=web")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["headline"], "Sotuvi")

    def test_inactive_ad_not_returned(self):
        Ad.objects.create(
            title="O'chirilgan", slot=Ad.SLOT_SPLASH, platform=Ad.PLATFORM_ALL,
            is_active=False, starts_at=timezone.now(),
        )
        resp = self.client.get("/api/ads/active/?slot=splash&platform=web")
        self.assertEqual(resp.status_code, 204)

    def test_priority_ordering(self):
        Ad.objects.create(
            title="Low priority", slot=Ad.SLOT_SPLASH, platform=Ad.PLATFORM_ALL,
            headline="Low", is_active=True, priority=1, starts_at=timezone.now(),
        )
        Ad.objects.create(
            title="High priority", slot=Ad.SLOT_SPLASH, platform=Ad.PLATFORM_ALL,
            headline="High", is_active=True, priority=99, starts_at=timezone.now(),
        )
        resp = self.client.get("/api/ads/active/?slot=splash&platform=web")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["headline"], "High")

    def test_click_tracking_increments(self):
        ad = Ad.objects.create(
            title="Click test", slot=Ad.SLOT_SPLASH, platform=Ad.PLATFORM_ALL,
            is_active=True, starts_at=timezone.now(),
        )
        self.client.post(f"/api/ads/{ad.id}/click/")
        ad.refresh_from_db()
        self.assertEqual(ad.clicks, 1)

    def test_active_ad_increments_impressions(self):
        ad = Ad.objects.create(
            title="Imp test", slot=Ad.SLOT_SPLASH, platform=Ad.PLATFORM_ALL,
            is_active=True, starts_at=timezone.now(),
        )
        self.client.get("/api/ads/active/?slot=splash&platform=web")
        ad.refresh_from_db()
        self.assertEqual(ad.impressions, 1)
