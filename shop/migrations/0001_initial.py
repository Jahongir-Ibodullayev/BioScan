from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalog", "0001_initial"),
        ("accounts", "0002_account_type"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="Nom")),
                ("slug", models.SlugField(max_length=140, unique=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="shop/categories/", verbose_name="Rasm")),
                ("description", models.TextField(blank=True, verbose_name="Tavsif")),
                ("is_active", models.BooleanField(default=True, verbose_name="Faol")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Tartib")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="shop.category", verbose_name="Ota kategoriya")),
            ],
            options={"verbose_name": "Kategoriya", "verbose_name_plural": "Kategoriyalar", "ordering": ("order", "name")},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200, verbose_name="Sarlavha")),
                ("slug", models.SlugField(max_length=220, unique=True)),
                ("short_description", models.CharField(blank=True, max_length=300, verbose_name="Qisqa tavsif")),
                ("description", models.TextField(blank=True, verbose_name="To'liq tavsif")),
                ("ai_generated_description", models.BooleanField(default=False, verbose_name="AI tavsif")),
                ("price", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Narx (so'm)")),
                ("discount_price", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="Chegirmali narx")),
                ("currency", models.CharField(default="UZS", max_length=8, verbose_name="Valyuta")),
                ("stock_quantity", models.PositiveIntegerField(default=0, verbose_name="Sondan")),
                ("sku", models.CharField(blank=True, max_length=64, verbose_name="SKU")),
                ("brand", models.CharField(blank=True, max_length=120, verbose_name="Brend")),
                ("status", models.CharField(choices=[("draft", "Qoralama"), ("active", "Faol"), ("out_of_stock", "Mahsulot tugagan"), ("archived", "Arxiv")], default="draft", max_length=20, verbose_name="Holati")),
                ("is_featured", models.BooleanField(default=False, verbose_name="Tavsiya qilingan")),
                ("rating", models.DecimalField(decimal_places=2, default=Decimal("0.0"), max_digits=3, verbose_name="Reyting")),
                ("reviews_count", models.PositiveIntegerField(default=0, verbose_name="Sharhlar")),
                ("views_count", models.PositiveIntegerField(default=0, verbose_name="Ko'rishlar")),
                ("sales_count", models.PositiveIntegerField(default=0, verbose_name="Sotilgan")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="shop.category", verbose_name="Kategoriya")),
                ("related_species", models.ForeignKey(blank=True, help_text="Tabiat turi bilan bog'liq mahsulot (asal, dorivor giyoh, h.k.)", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="related_products", to="catalog.species")),
                ("seller", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="products", to=settings.AUTH_USER_MODEL, verbose_name="Sotuvchi")),
            ],
            options={"verbose_name": "Mahsulot", "verbose_name_plural": "Mahsulotlar", "ordering": ("-is_featured", "-created_at")},
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["status", "-created_at"], name="shop_produc_status_idx"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["category", "status"], name="shop_produc_categ_idx"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["seller"], name="shop_produc_seller_idx"),
        ),
        migrations.CreateModel(
            name="ProductImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="shop/products/", verbose_name="Rasm")),
                ("alt_text", models.CharField(blank=True, max_length=200, verbose_name="Alt matn")),
                ("is_main", models.BooleanField(default=False, verbose_name="Asosiy rasm")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Tartib")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="shop.product")),
            ],
            options={"verbose_name": "Mahsulot rasmi", "verbose_name_plural": "Mahsulot rasmlari", "ordering": ("-is_main", "order")},
        ),
        migrations.CreateModel(
            name="Cart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="cart", to=settings.AUTH_USER_MODEL, verbose_name="Foydalanuvchi")),
            ],
            options={"verbose_name": "Savat", "verbose_name_plural": "Savatlar"},
        ),
        migrations.CreateModel(
            name="CartItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1, verbose_name="Soni")),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("cart", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="shop.cart")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="shop.product")),
            ],
            options={"unique_together": {("cart", "product")}, "ordering": ("-added_at",)},
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_number", models.CharField(max_length=24, unique=True, verbose_name="Buyurtma raqami")),
                ("status", models.CharField(choices=[("pending", "Kutilmoqda"), ("paid", "To'langan"), ("shipped", "Yo'lda"), ("delivered", "Yetkazildi"), ("cancelled", "Bekor qilindi"), ("refunded", "Qaytarildi")], default="pending", max_length=20, verbose_name="Holat")),
                ("payment_method", models.CharField(choices=[("cash", "Naqd"), ("card", "Karta"), ("click", "Click"), ("payme", "Payme"), ("uzum", "Uzum")], default="cash", max_length=20, verbose_name="To'lov turi")),
                ("payment_status", models.CharField(default="unpaid", max_length=20, verbose_name="To'lov holati")),
                ("subtotal", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=12)),
                ("shipping_cost", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=12)),
                ("total_amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=12)),
                ("shipping_full_name", models.CharField(blank=True, max_length=120, verbose_name="Qabul qiluvchi")),
                ("shipping_phone", models.CharField(blank=True, max_length=20, verbose_name="Telefon")),
                ("shipping_address", models.TextField(blank=True, verbose_name="Manzil")),
                ("shipping_city", models.CharField(blank=True, max_length=80, verbose_name="Shahar")),
                ("shipping_notes", models.TextField(blank=True, verbose_name="Eslatmalar")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="orders", to=settings.AUTH_USER_MODEL, verbose_name="Mijoz")),
            ],
            options={"verbose_name": "Buyurtma", "verbose_name_plural": "Buyurtmalar", "ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(fields=["customer", "-created_at"], name="shop_order_cust_idx"),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(fields=["status"], name="shop_order_status_idx"),
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title_snapshot", models.CharField(max_length=200)),
                ("price_snapshot", models.DecimalField(decimal_places=2, max_digits=12)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="shop.order")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="shop.product")),
            ],
            options={"verbose_name": "Buyurtma elementi"},
        ),
        migrations.CreateModel(
            name="Wishlist",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="wishlisted_by", to="shop.product")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="wishlist", to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("user", "product")}, "ordering": ("-added_at",), "verbose_name": "Sevimli mahsulot"},
        ),
        migrations.CreateModel(
            name="Review",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.PositiveSmallIntegerField()),
                ("comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="shop.product")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("product", "user")}, "ordering": ("-created_at",)},
        ),
    ]
