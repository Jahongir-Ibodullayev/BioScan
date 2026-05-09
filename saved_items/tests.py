"""Saved species (kolleksiya) testlari."""
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from catalog.models import Species

from .models import SavedSpecies

User = get_user_model()


class SavedSpeciesTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.species = Species.objects.create(
            slug="ot-tur", name="Test", latin="X", category="giyoh",
        )

    def setUp(self):
        self.user = User.objects.create_user(phone="+998905555500", password="p")
        login = self.client.post(
            "/api/auth/login/",
            {"phone": "+998905555500", "password": "p"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_save_species(self):
        resp = self.client.post(
            "/api/collections/",
            {"species": self.species.id, "note": "Test eslatma"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(SavedSpecies.objects.filter(user=self.user).count(), 1)

    def test_list_my_saved_only(self):
        SavedSpecies.objects.create(user=self.user, species=self.species)
        # Boshqa user
        other = User.objects.create_user(phone="+998905555501", password="x")
        SavedSpecies.objects.create(user=other, species=self.species)
        resp = self.client.get("/api/collections/")
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results") if isinstance(resp.data, dict) else resp.data
        self.assertEqual(len(results), 1)

    def test_anonymous_blocked(self):
        self.client.credentials()
        resp = self.client.get("/api/collections/")
        self.assertIn(resp.status_code, [401, 403])
