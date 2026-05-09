"""Crop Advisor testlari — Crop, Region, advice, plans."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Crop, CropPlan, Region

User = get_user_model()


class CropListTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.kart = Crop.objects.create(
            slug="kartoshka", name_uz="Kartoshka", name_lat="Solanum tuberosum",
            category="sabzavot", icon_name="sprout",
            min_soil_temp_c=7, optimal_soil_temp_c=12, frost_sensitive=True,
            plant_window_start_month=3, plant_window_end_month=5,
            days_to_harvest_min=80, days_to_harvest_max=120,
            water_freq_days=5,
        )
        cls.tashkent = Region.objects.create(
            slug="tashkent", name_uz="Toshkent",
            lat_min=40.8, lat_max=41.6, lon_min=68.7, lon_max=70.0,
            avg_last_frost_doy=78, avg_first_frost_doy=295,
        )

    def test_list_crops_anonymous(self):
        resp = self.client.get("/api/crops/")
        self.assertEqual(resp.status_code, 200)

    def test_crop_detail_by_slug(self):
        resp = self.client.get("/api/crops/kartoshka/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["name_uz"], "Kartoshka")

    def test_regions_endpoint(self):
        resp = self.client.get("/api/crops/regions/")
        self.assertEqual(resp.status_code, 200)
        names = [r.get("name_uz") for r in resp.data]
        self.assertIn("Toshkent", names)


class AdviceTests(APITestCase):
    """POST /api/crops/advice/ — GPS + ekin → maslahat."""

    @classmethod
    def setUpTestData(cls):
        Crop.objects.create(
            slug="pomidor", name_uz="Pomidor", category="sabzavot",
            min_soil_temp_c=13, optimal_soil_temp_c=18, frost_sensitive=True,
            plant_window_start_month=4, plant_window_end_month=6,
            days_to_harvest_min=65, days_to_harvest_max=90, water_freq_days=4,
        )
        Region.objects.create(
            slug="tashkent", name_uz="Toshkent",
            lat_min=40.8, lat_max=41.6, lon_min=68.7, lon_max=70.0,
            avg_last_frost_doy=78, avg_first_frost_doy=295,
        )

    def test_advice_for_known_crop_and_location(self):
        resp = self.client.post(
            "/api/crops/advice/",
            {"crop_slug": "pomidor", "lat": 41.31, "lon": 69.24, "irrigation": "drip"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["crop"], "Pomidor")
        self.assertEqual(resp.data["region"], "Toshkent")
        self.assertIn("watering_schedule", resp.data)
        self.assertIn("best_plant_dates", resp.data)

    def test_advice_unknown_crop_404(self):
        resp = self.client.post(
            "/api/crops/advice/",
            {"crop_slug": "yo'q-ekin", "lat": 41.31, "lon": 69.24},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_advice_invalid_coords(self):
        resp = self.client.post(
            "/api/crops/advice/",
            {"crop_slug": "pomidor", "lat": "abc", "lon": "xyz"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)


class CropPlanTests(APITestCase):
    """Foydalanuvchi rejalari — auth talab qiladi."""

    @classmethod
    def setUpTestData(cls):
        cls.crop = Crop.objects.create(
            slug="bodring", name_uz="Bodring", category="sabzavot",
            water_freq_days=3,
        )

    def setUp(self):
        self.user = User.objects.create_user(phone="+998903333300", password="p")
        login = self.client.post(
            "/api/auth/login/",
            {"phone": "+998903333300", "password": "p"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_create_plan(self):
        resp = self.client.post(
            "/api/crops/plans/",
            {
                "crop": self.crop.id, "lat": 41.31, "lon": 69.24,
                "irrigation": "drip", "planned_plant_date": str(date.today() + timedelta(days=10)),
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(CropPlan.objects.filter(user=self.user).count(), 1)

    def test_list_my_plans_only(self):
        CropPlan.objects.create(
            user=self.user, crop=self.crop, lat=41.31, lon=69.24,
            irrigation="drip", planned_plant_date=date.today(),
        )
        # Boshqa user uchun reja
        other = User.objects.create_user(phone="+998903333301", password="x")
        CropPlan.objects.create(
            user=other, crop=self.crop, lat=41.0, lon=69.0,
            irrigation="manual", planned_plant_date=date.today(),
        )
        resp = self.client.get("/api/crops/plans/")
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results") if isinstance(resp.data, dict) else resp.data
        self.assertEqual(len(results), 1)

    def test_anonymous_blocked(self):
        self.client.credentials()
        resp = self.client.get("/api/crops/plans/")
        self.assertIn(resp.status_code, [401, 403])
