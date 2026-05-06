from rest_framework import serializers

from .models import (
    Cart, CartItem, Category, Order, OrderItem, Product, ProductImage,
    Review, Wishlist,
)


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(source="products.count", read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "image", "description",
                  "is_active", "order", "product_count")


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text", "is_main", "order")


class ProductListSerializer(serializers.ModelSerializer):
    """Yengil — list view uchun (savatcha, katalog)."""
    seller_name = serializers.CharField(source="seller.seller_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    thumbnail = serializers.SerializerMethodField()
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id", "title", "slug", "short_description",
            "price", "discount_price", "currency",
            "category_name", "seller_name", "thumbnail",
            "rating", "reviews_count", "is_featured", "in_stock",
        )

    def get_thumbnail(self, obj):
        # 1) External URL (seed'dan kelgan Unsplash) eng birinchi
        if obj.image_url:
            return obj.image_url
        # 2) ProductImage uploads
        main = obj.images.filter(is_main=True).first() or obj.images.first()
        if main and main.image:
            request = self.context.get("request")
            url = main.image.url
            return request.build_absolute_uri(url) if request else url
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Batafsil — product detail page uchun."""
    seller_name = serializers.CharField(source="seller.seller_name", read_only=True)
    seller_id = serializers.IntegerField(source="seller.id", read_only=True)
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id", "title", "slug", "short_description", "description",
            "ai_generated_description",
            "price", "discount_price", "currency",
            "stock_quantity", "sku", "brand",
            "status", "is_featured",
            "rating", "reviews_count", "views_count", "sales_count",
            "category", "seller_id", "seller_name", "images",
            "related_species",
            "in_stock", "created_at",
        )


class ProductWriteSerializer(serializers.ModelSerializer):
    """Sotuvchi mahsulot yaratish/yangilash uchun."""
    class Meta:
        model = Product
        fields = (
            "title", "short_description", "description",
            "price", "discount_price", "currency",
            "stock_quantity", "sku", "brand",
            "category", "status", "related_species",
        )


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ("id", "product", "product_id", "quantity", "subtotal", "added_at")
        read_only_fields = ("id", "subtotal", "added_at")


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ("id", "items", "total_items", "total_price", "created_at", "updated_at")


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "product_id", "title_snapshot", "price_snapshot", "quantity", "subtotal")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id", "order_number", "status", "payment_method", "payment_status",
            "subtotal", "shipping_cost", "total_amount",
            "shipping_full_name", "shipping_phone", "shipping_address",
            "shipping_city", "shipping_notes",
            "items", "customer_phone",
            "created_at", "updated_at", "delivered_at",
        )
        read_only_fields = ("order_number", "subtotal", "total_amount", "created_at", "updated_at", "delivered_at")


class CheckoutSerializer(serializers.Serializer):
    """Savatdan buyurtma yaratish uchun input."""
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_CHOICES, default=Order.PAYMENT_CASH)
    shipping_full_name = serializers.CharField(max_length=120)
    shipping_phone = serializers.CharField(max_length=20)
    shipping_address = serializers.CharField()
    shipping_city = serializers.CharField(max_length=80, required=False, allow_blank=True)
    shipping_notes = serializers.CharField(required=False, allow_blank=True)


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Review
        fields = ("id", "product", "user_name", "rating", "comment", "created_at")
        read_only_fields = ("user_name", "created_at")


class WishlistSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Wishlist
        fields = ("id", "product", "product_id", "added_at")
        read_only_fields = ("id", "added_at")
