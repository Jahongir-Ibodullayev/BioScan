"""Shop endpoint testlari — Categories, Products, Cart, Orders."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Cart, CartItem, Category, Product

User = get_user_model()


class ShopPublicTests(APITestCase):
    """Anonim foydalanuvchi — kategoriya va mahsulotlarni ko'rish."""

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Chodirlar", slug="chodir")
        cls.seller = User.objects.create_user(
            phone="+998901111100", password="x", full_name="Sotuvchi",
        )
        cls.product = Product.objects.create(
            seller=cls.seller, category=cls.cat,
            title="Test chodir", short_description="2 kishilik",
            price=Decimal("950000"), discount_price=Decimal("800000"),
            stock_quantity=10, status=Product.STATUS_ACTIVE,
            external_url="https://example.com",
        )

    def test_list_categories(self):
        resp = self.client.get("/api/shop/categories/")
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results") if isinstance(resp.data, dict) else resp.data
        self.assertGreaterEqual(len(results), 1)

    def test_list_products(self):
        resp = self.client.get("/api/shop/products/")
        self.assertEqual(resp.status_code, 200)

    def test_product_detail(self):
        resp = self.client.get(f"/api/shop/products/{self.product.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("title"), "Test chodir")

    def test_filter_by_category(self):
        resp = self.client.get(f"/api/shop/products/?category={self.cat.slug}")
        self.assertEqual(resp.status_code, 200)


class ShopCartTests(APITestCase):
    """Cart va order — auth talab qiladi."""

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Test", slug="test-cat")
        cls.seller = User.objects.create_user(phone="+998901111101", password="x")
        cls.product = Product.objects.create(
            seller=cls.seller, category=cls.cat,
            title="Cart test", price=Decimal("100000"),
            stock_quantity=5, status=Product.STATUS_ACTIVE,
        )

    def setUp(self):
        self.user = User.objects.create_user(phone="+998901111102", password="p")
        login = self.client.post(
            "/api/auth/login/",
            {"phone": "+998901111102", "password": "p"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_get_empty_cart(self):
        resp = self.client.get("/api/shop/cart/")
        self.assertEqual(resp.status_code, 200)

    def test_anonymous_cart_blocked(self):
        self.client.credentials()
        resp = self.client.get("/api/shop/cart/")
        self.assertIn(resp.status_code, [401, 403])
