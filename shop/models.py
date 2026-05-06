"""Tog'AI E-commerce models — Mahsulot, Kategoriya, Savat, Buyurtma.

Arxitektura:
  Category (hierarchic) ← Product → ProductImage
                              ↓
                          CartItem ← Cart ← User
                              ↓
                       OrderItem ← Order ← User
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """Mahsulot kategoriyasi — daraxt strukturasi (parent → children)."""

    name = models.CharField("Nom", max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="children",
        null=True, blank=True, verbose_name="Ota kategoriya",
    )
    image = models.ImageField("Rasm", upload_to="shop/categories/", null=True, blank=True)
    description = models.TextField("Tavsif", blank=True)
    is_active = models.BooleanField("Faol", default=True)
    order = models.PositiveIntegerField("Tartib", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ("order", "name")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or f"cat-{self.pk or ''}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """Mahsulot — sotuvchi (User) tomonidan qo'shiladi."""

    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_OUT_OF_STOCK = "out_of_stock"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Qoralama"),
        (STATUS_ACTIVE, "Faol"),
        (STATUS_OUT_OF_STOCK, "Mahsulot tugagan"),
        (STATUS_ARCHIVED, "Arxiv"),
    ]

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="products", verbose_name="Sotuvchi",
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products",
        verbose_name="Kategoriya",
    )

    title = models.CharField("Sarlavha", max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    short_description = models.CharField("Qisqa tavsif", max_length=300, blank=True)
    description = models.TextField("To'liq tavsif", blank=True)
    ai_generated_description = models.BooleanField("AI tavsif", default=False)

    price = models.DecimalField("Narx (so'm)", max_digits=12, decimal_places=2)
    discount_price = models.DecimalField(
        "Chegirmali narx", max_digits=12, decimal_places=2, null=True, blank=True,
    )
    currency = models.CharField("Valyuta", max_length=8, default="UZS")

    stock_quantity = models.PositiveIntegerField("Sondan", default=0)
    sku = models.CharField("SKU", max_length=64, blank=True)
    brand = models.CharField("Brend", max_length=120, blank=True)

    status = models.CharField(
        "Holati", max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT,
    )
    is_featured = models.BooleanField("Tavsiya qilingan", default=False)

    rating = models.DecimalField("Reyting", max_digits=3, decimal_places=2, default=Decimal("0.0"))
    reviews_count = models.PositiveIntegerField("Sharhlar", default=0)
    views_count = models.PositiveIntegerField("Ko'rishlar", default=0)
    sales_count = models.PositiveIntegerField("Sotilgan", default=0)

    related_species = models.ForeignKey(
        "catalog.Species", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="related_products",
        help_text="Tabiat turi bilan bog'liq mahsulot (asal, dorivor giyoh, h.k.)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"
        ordering = ("-is_featured", "-created_at")
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["seller"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "product"
            slug = base
            i = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def in_stock(self) -> bool:
        return self.status == self.STATUS_ACTIVE and self.stock_quantity > 0

    @property
    def effective_price(self) -> Decimal:
        return self.discount_price or self.price

    def __str__(self):
        return self.title


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField("Rasm", upload_to="shop/products/")
    alt_text = models.CharField("Alt matn", max_length=200, blank=True)
    is_main = models.BooleanField("Asosiy rasm", default=False)
    order = models.PositiveIntegerField("Tartib", default=0)

    class Meta:
        ordering = ("-is_main", "order")
        verbose_name = "Mahsulot rasmi"
        verbose_name_plural = "Mahsulot rasmlari"


# ============================================================
# Cart — savatcha (foydalanuvchi sessiyasi)
# ============================================================
class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="cart", verbose_name="Foydalanuvchi",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Savat"
        verbose_name_plural = "Savatlar"

    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self) -> Decimal:
        return sum((item.subtotal for item in self.items.all()), Decimal("0"))


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField("Soni", default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "product")
        ordering = ("-added_at",)

    @property
    def subtotal(self) -> Decimal:
        return self.product.effective_price * self.quantity


# ============================================================
# Orders — buyurtmalar
# ============================================================
class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"
    STATUS_REFUNDED = "refunded"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Kutilmoqda"),
        (STATUS_PAID, "To'langan"),
        (STATUS_SHIPPED, "Yo'lda"),
        (STATUS_DELIVERED, "Yetkazildi"),
        (STATUS_CANCELLED, "Bekor qilindi"),
        (STATUS_REFUNDED, "Qaytarildi"),
    ]

    PAYMENT_CASH = "cash"
    PAYMENT_CARD = "card"
    PAYMENT_CLICK = "click"
    PAYMENT_PAYME = "payme"
    PAYMENT_UZUM = "uzum"
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, "Naqd"),
        (PAYMENT_CARD, "Karta"),
        (PAYMENT_CLICK, "Click"),
        (PAYMENT_PAYME, "Payme"),
        (PAYMENT_UZUM, "Uzum"),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="orders", verbose_name="Mijoz",
    )
    order_number = models.CharField("Buyurtma raqami", max_length=24, unique=True)

    status = models.CharField("Holat", max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_method = models.CharField("To'lov turi", max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_CASH)
    payment_status = models.CharField("To'lov holati", max_length=20, default="unpaid")

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    shipping_full_name = models.CharField("Qabul qiluvchi", max_length=120, blank=True)
    shipping_phone = models.CharField("Telefon", max_length=20, blank=True)
    shipping_address = models.TextField("Manzil", blank=True)
    shipping_city = models.CharField("Shahar", max_length=80, blank=True)
    shipping_notes = models.TextField("Eslatmalar", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["customer", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            import secrets
            self.order_number = "TG-" + secrets.token_hex(4).upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} — {self.customer}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    # Snapshot — buyurtma qabul qilingan paytdagi nom va narx (sotuvchi keyinroq narxni o'zgartirsa, bu o'zgarmaydi)
    title_snapshot = models.CharField(max_length=200)
    price_snapshot = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Buyurtma elementi"

    @property
    def subtotal(self) -> Decimal:
        return self.price_snapshot * self.quantity


# ============================================================
# Wishlist — sevimlilar
# ============================================================
class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        ordering = ("-added_at",)
        verbose_name = "Sevimli mahsulot"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()  # 1-5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "user")
        ordering = ("-created_at",)
