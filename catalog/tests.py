"""Catalog (Species) endpoint testlari."""
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Species


class SpeciesListTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        Species.objects.create(
            slug="tulipa-greigii", name="Greig lolasi", latin="Tulipa greigii",
            category="gul", red_book=True, iucn_status="VU",
        )
        Species.objects.create(
            slug="alhagi-pseudalhagi", name="Yantoq", latin="Alhagi pseudalhagi",
            category="giyoh", red_book=False, iucn_status="LC",
        )
        Species.objects.create(
            slug="juniperus-seravschanica", name="Zarafshon archasi",
            latin="Juniperus seravschanica", category="daraxt",
            red_book=True, iucn_status="EN",
        )

    def test_list_all_species(self):
        resp = self.client.get("/api/species/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Pagination — count yoki direct list
        results = resp.data.get("results") if isinstance(resp.data, dict) else resp.data
        self.assertGreaterEqual(len(results), 3)

    def test_filter_red_book(self):
        resp = self.client.get("/api/species/?red_book=true")
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results") if isinstance(resp.data, dict) else resp.data
        for r in results:
            self.assertTrue(r.get("red_book"))

    def test_filter_category(self):
        resp = self.client.get("/api/species/?category=gul")
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results") if isinstance(resp.data, dict) else resp.data
        for r in results:
            self.assertEqual(r.get("category"), "gul")

    def test_detail_by_slug(self):
        resp = self.client.get("/api/species/tulipa-greigii/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("name"), "Greig lolasi")
        self.assertEqual(resp.data.get("latin"), "Tulipa greigii")

    def test_detail_404_for_unknown_slug(self):
        resp = self.client.get("/api/species/unknown-slug-xyz/")
        self.assertEqual(resp.status_code, 404)

    def test_search_by_name(self):
        resp = self.client.get("/api/species/?search=Yantoq")
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results") if isinstance(resp.data, dict) else resp.data
        self.assertTrue(any(r.get("name") == "Yantoq" for r in results))
