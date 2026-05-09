"""Auth endpoint testlari — SimpleAuth, OTP, Me."""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class SimpleAuthTests(APITestCase):
    """POST /api/auth/login/ — telefon+parol auto-register/login."""

    def test_register_new_user(self):
        """Yangi telefon → yangi hisob yaratiladi va JWT keladi."""
        resp = self.client.post(
            "/api/auth/login/",
            {"phone": "+998901112233", "password": "testpass1", "full_name": "Test User"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["new"])
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["phone"], "+998901112233")
        self.assertEqual(resp.data["user"]["full_name"], "Test User")

    def test_login_existing_user_correct_password(self):
        """Mavjud telefon + to'g'ri parol → kirish."""
        u = User.objects.create_user(phone="+998901112244", password="mypass1")
        resp = self.client.post(
            "/api/auth/login/",
            {"phone": "+998901112244", "password": "mypass1"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["new"])
        self.assertEqual(resp.data["user"]["id"], u.id)

    def test_login_wrong_password_returns_401(self):
        User.objects.create_user(phone="+998901112255", password="goodpass")
        resp = self.client.post(
            "/api/auth/login/",
            {"phone": "+998901112255", "password": "wrongpass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_short_password_rejected(self):
        resp = self.client.post(
            "/api/auth/login/",
            {"phone": "+998901112266", "password": "abc"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_fields_rejected(self):
        resp = self.client.post("/api/auth/login/", {"phone": "+998901112277"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class MeViewTests(APITestCase):
    """GET/PATCH /api/auth/me/ — profil ko'rish va yangilash."""

    def setUp(self):
        self.user = User.objects.create_user(phone="+998901112288", password="pass", full_name="Old Name")
        login = self.client.post(
            "/api/auth/login/",
            {"phone": "+998901112288", "password": "pass"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_get_me_returns_profile(self):
        resp = self.client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["phone"], "+998901112288")

    def test_patch_me_updates_full_name(self):
        resp = self.client.patch("/api/auth/me/", {"full_name": "New Name"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "New Name")

    def test_me_requires_auth(self):
        self.client.credentials()
        resp = self.client.get("/api/auth/me/")
        self.assertIn(resp.status_code, [401, 403])


class TokenRefreshTests(APITestCase):
    def test_refresh_token_works(self):
        User.objects.create_user(phone="+998901112299", password="pass")
        login = self.client.post(
            "/api/auth/login/",
            {"phone": "+998901112299", "password": "pass"},
            format="json",
        )
        refresh = login.data["refresh"]
        resp = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
