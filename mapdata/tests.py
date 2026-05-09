"""Map markers + bbox + MBTiles testlari."""
from rest_framework.test import APITestCase

from .models import MapMarker


class MapMarkerTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Toshkent atrofida
        MapMarker.objects.create(
            type="danger", label="Test xavf", description="Test",
            latitude=41.31, longitude=69.24, region="Toshkent", active=True,
        )
        # Boshqa joy
        MapMarker.objects.create(
            type="info", label="Test info", description="Test",
            latitude=39.0, longitude=66.0, region="Samarqand", active=True,
        )

    def test_list_all_markers(self):
        resp = self.client.get("/api/map/markers/")
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results") if isinstance(resp.data, dict) else resp.data
        self.assertGreaterEqual(len(results), 2)

    def test_bbox_filter(self):
        # Faqat Toshkent (41.31, 69.24) ichidagi
        resp = self.client.get("/api/map/markers/?bbox=41.0,69.0,42.0,70.0")
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results") if isinstance(resp.data, dict) else resp.data
        for r in results:
            self.assertGreaterEqual(float(r["latitude"]), 41.0)
            self.assertLessEqual(float(r["latitude"]), 42.0)


class MBTilesUrlTests(APITestCase):
    def test_known_region_returns_metadata(self):
        resp = self.client.get("/api/map/regions/tashkent/mbtiles_url/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("region", resp.data)
        self.assertIn("available", resp.data)

    def test_unknown_region_returns_unavailable(self):
        resp = self.client.get("/api/map/regions/marsiya/mbtiles_url/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["available"])
