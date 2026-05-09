"""Observations + TFLite + ScanFeedback testlari."""
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Species

from .models import Observation, ScanFeedback, TFLiteModel

User = get_user_model()


class ObservationCRUDTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.species = Species.objects.create(
            slug="test-tur", name="Test", latin="Testus", category="giyoh",
        )

    def setUp(self):
        self.user = User.objects.create_user(phone="+998902222200", password="p")
        login = self.client.post(
            "/api/auth/login/",
            {"phone": "+998902222200", "password": "p"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_list_my_observations_empty(self):
        resp = self.client.get("/api/observations/")
        self.assertEqual(resp.status_code, 200)

    def test_anonymous_blocked(self):
        self.client.credentials()
        resp = self.client.get("/api/observations/")
        self.assertIn(resp.status_code, [401, 403])

    def test_my_observations_filtered_by_user(self):
        Observation.objects.create(user=self.user, species=self.species)
        # Boshqa user'ning kuzatuvi — ko'rinmaslik kerak
        other = User.objects.create_user(phone="+998902222201", password="x")
        Observation.objects.create(user=other, species=self.species)

        resp = self.client.get("/api/observations/")
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results") if isinstance(resp.data, dict) else resp.data
        self.assertEqual(len(results), 1)


class PublicObservationsTests(APITestCase):
    """GET /api/observations/public/ — anonim, GPS markerlar."""

    def test_public_endpoint_anonymous_ok(self):
        resp = self.client.get("/api/observations/public/")
        self.assertEqual(resp.status_code, 200)


class TFLiteEndpointTests(APITestCase):
    def test_active_model_returns_204_when_none(self):
        resp = self.client.get("/api/observations/tflite/active/")
        self.assertIn(resp.status_code, [204, 200])

    def test_scan_feedback_anonymous_allowed(self):
        resp = self.client.post(
            "/api/observations/scan/feedback/",
            {"predicted_slug": "test", "correct_slug": "test2", "is_correct": False},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ScanFeedback.objects.count(), 1)
