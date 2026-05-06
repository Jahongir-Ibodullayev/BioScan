"""Shop views — Public catalog + Seller dashboard + Cart/Orders.

Endpoints:
  /api/shop/categories/                       — public list
  /api/shop/products/                         — public list
  /api/shop/products/{id}/                    — public detail
  /api/shop/seller/products/                  — seller CRUD
  /api/shop/seller/products/{id}/ai-generate/ — AI description
  /api/shop/cart/                             — auth user cart
  /api/shop/cart/add/                         — add to cart
  /api/shop/cart/remove/{item_id}/            — remove
  /api/shop/orders/                           — auth user orders
  /api/shop/orders/checkout/                  — savatdan buyurtma
  /api/shop/wishlist/                         — sevimlilar
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from togai.throttles import AIChatThrottle

from .models import (
    Cart, CartItem, Category, Order, OrderItem, Product, Review, Wishlist,
)
from .permissions import IsSellerOrReadOnly
from .serializers import (
    CartItemSerializer, CartSerializer, CategorySerializer, CheckoutSerializer,
    OrderSerializer, ProductDetailSerializer, ProductListSerializer,
    ProductWriteSerializer, ReviewSerializer, WishlistSerializer,
)

log = logging.getLogger(__name__)


# ============================================================
# PUBLIC — Catalog
# ============================================================
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None  # full list


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Ommaviy mahsulot ro'yxati va detali."""
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Product.objects.filter(status=Product.STATUS_ACTIVE).select_related(
            "seller", "category"
        ).prefetch_related("images")
        # Filterlar
        cat = self.request.query_params.get("category")
        if cat:
            qs = qs.filter(category__slug=cat)
        search = self.request.query_params.get("q")
        if search:
            qs = qs.filter(title__icontains=search)
        featured = self.request.query_params.get("featured")
        if featured in ("1", "true"):
            qs = qs.filter(is_featured=True)
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment views
        Product.objects.filter(pk=instance.pk).update(views_count=instance.views_count + 1)
        return super().retrieve(request, *args, **kwargs)


# ============================================================
# SELLER — own products CRUD
# ============================================================
class SellerProductViewSet(viewsets.ModelViewSet):
    """Sotuvchi o'z mahsulotlarini boshqaradi."""
    permission_classes = [permissions.IsAuthenticated, IsSellerOrReadOnly]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Product.objects.none()
        return Product.objects.filter(seller=self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProductWriteSerializer
        return ProductDetailSerializer

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

    @action(detail=True, methods=["post"], throttle_classes=[AIChatThrottle], url_path="ai-generate")
    def ai_generate(self, request, pk=None):
        """AI yordamida mahsulot tavsifi yaratadi."""
        product = self.get_object()
        if product.seller != request.user:
            return Response({"detail": "Faqat o'z mahsulotingiz"}, status=status.HTTP_403_FORBIDDEN)

        try:
            from togai.integrations import groq_chat
            system = (
                "Siz e-commerce yozish bo'yicha tajribali kopirayter. "
                "Mahsulot tavsifini O'ZBEK tilida, qiziqarli va SEO-friendly tarzda yozing. "
                "3-5 jumla. Foyda va xususiyatlarni ta'kidlang."
            )
            prompt = (
                f"Mahsulot nomi: {product.title}\n"
                f"Kategoriya: {product.category.name}\n"
                f"Brend: {product.brand or 'kiritilmagan'}\n"
                f"Narx: {product.price} {product.currency}\n\n"
                "Mahsulot tavsifini yozing. Faqat tavsif matnini qaytaring, izohsiz."
            )
            description = groq_chat(prompt, system=system)
            if description and len(description) > 20:
                product.description = description.strip()
                product.ai_generated_description = True
                product.save(update_fields=["description", "ai_generated_description", "updated_at"])
                return Response({
                    "description": product.description,
                    "ai_generated": True,
                })
            return Response({"detail": "AI javob bo'sh keldi"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            log.exception("ai_generate failed")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# CART
# ============================================================
class CartViewSet(viewsets.ViewSet):
    """Foydalanuvchi savatchasi."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_cart(self, user):
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    def list(self, request):
        cart = self._get_cart(request.user)
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=["post"])
    def add(self, request):
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))
        if not product_id:
            return Response({"detail": "product_id majburiy"}, status=400)
        product = get_object_or_404(Product, pk=product_id, status=Product.STATUS_ACTIVE)
        if quantity < 1 or quantity > product.stock_quantity:
            return Response({"detail": "Yaroqsiz son"}, status=400)
        cart = self._get_cart(request.user)
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, defaults={"quantity": quantity},
        )
        if not created:
            item.quantity = min(item.quantity + quantity, product.stock_quantity)
            item.save()
        return Response(CartItemSerializer(item).data)

    @action(detail=False, methods=["post"], url_path="update")
    def update_quantity(self, request):
        item_id = request.data.get("item_id")
        quantity = int(request.data.get("quantity", 1))
        if not item_id:
            return Response({"detail": "item_id majburiy"}, status=400)
        item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
        if quantity <= 0:
            item.delete()
            return Response({"deleted": True})
        item.quantity = min(quantity, item.product.stock_quantity)
        item.save()
        return Response(CartItemSerializer(item).data)

    @action(detail=False, methods=["post"])
    def clear(self, request):
        cart = self._get_cart(request.user)
        cart.items.all().delete()
        return Response({"cleared": True})


# ============================================================
# ORDERS
# ============================================================
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Foydalanuvchi buyurtmalari."""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()
        return Order.objects.filter(customer=self.request.user).prefetch_related("items")

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def checkout(self, request):
        """Savatchadan buyurtma yaratadi (atomic — barcha yoki hech qaysisi)."""
        ser = CheckoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        cart = Cart.objects.filter(user=request.user).prefetch_related("items__product").first()
        if not cart or not cart.items.exists():
            return Response({"detail": "Savat bo'sh"}, status=400)

        items = list(cart.items.select_related("product").all())
        # Validate stock
        for item in items:
            if item.quantity > item.product.stock_quantity:
                return Response({
                    "detail": f"{item.product.title} — yetarli emas (mavjud: {item.product.stock_quantity})",
                }, status=400)

        subtotal = sum((it.subtotal for it in items), Decimal("0"))
        shipping = Decimal("20000")  # bepul yetkazib berish > 200K so'm
        if subtotal >= Decimal("200000"):
            shipping = Decimal("0")
        total = subtotal + shipping

        order = Order.objects.create(
            customer=request.user,
            **ser.validated_data,
            subtotal=subtotal,
            shipping_cost=shipping,
            total_amount=total,
        )
        for it in items:
            OrderItem.objects.create(
                order=order,
                product=it.product,
                title_snapshot=it.product.title,
                price_snapshot=it.product.effective_price,
                quantity=it.quantity,
            )
            # Stock kamaytirish
            Product.objects.filter(pk=it.product.pk).update(
                stock_quantity=it.product.stock_quantity - it.quantity,
                sales_count=it.product.sales_count + it.quantity,
            )

        # Savatni tozalash
        cart.items.all().delete()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


# ============================================================
# WISHLIST + REVIEWS
# ============================================================
class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Wishlist.objects.none()
        return Wishlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Review.objects.select_related("user", "product")
        product_id = self.request.query_params.get("product")
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs

    def perform_create(self, serializer):
        review = serializer.save(user=self.request.user)
        # Update product rating
        prod = review.product
        all_reviews = prod.reviews.all()
        avg = sum(r.rating for r in all_reviews) / max(len(all_reviews), 1)
        prod.rating = round(avg, 2)
        prod.reviews_count = len(all_reviews)
        prod.save(update_fields=["rating", "reviews_count", "updated_at"])
