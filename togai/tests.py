"""Backend infra/sanity testlari — health, schema, 404 va h.k."""
from django.test import TestCase
from rest_framework.test import APITestCase


class HealthTests(APITestCase):
    def test_health_endpoint(self):
        resp = self.client.get("/api/health/")
        self.assertEqual(resp.status_code, 200)


class SmokeTests(APITestCase):
    """API entry-point'lar javob beradimi (smoke test)."""

    def test_species_list_open(self):
        resp = self.client.get("/api/species/")
        self.assertIn(resp.status_code, [200, 404])

    def test_shop_categories_open(self):
        resp = self.client.get("/api/shop/categories/")
        self.assertEqual(resp.status_code, 200)

    def test_shop_products_open(self):
        resp = self.client.get("/api/shop/products/")
        self.assertEqual(resp.status_code, 200)

    def test_observations_public_open(self):
        resp = self.client.get("/api/observations/public/")
        self.assertEqual(resp.status_code, 200)

    def test_crops_open(self):
        resp = self.client.get("/api/crops/")
        self.assertEqual(resp.status_code, 200)

    def test_crops_regions_open(self):
        resp = self.client.get("/api/crops/regions/")
        self.assertEqual(resp.status_code, 200)

    def test_404_invalid_url(self):
        resp = self.client.get("/api/nonexistent-url-xyz/")
        self.assertEqual(resp.status_code, 404)
