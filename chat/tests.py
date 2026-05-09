"""Chat (AI conversation) testlari."""
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class ConversationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="+998904444400", password="p")
        login = self.client.post(
            "/api/auth/login/",
            {"phone": "+998904444400", "password": "p"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_list_my_conversations_empty(self):
        resp = self.client.get("/api/chat/conversations/")
        self.assertEqual(resp.status_code, 200)

    def test_anonymous_blocked(self):
        self.client.credentials()
        resp = self.client.get("/api/chat/conversations/")
        self.assertIn(resp.status_code, [401, 403])
