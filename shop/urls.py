from rest_framework.routers import DefaultRouter

from .views import (
    CartViewSet, CategoryViewSet, OrderViewSet, ProductViewSet, ReviewViewSet,
    SellerProductViewSet, WishlistViewSet,
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="shop-categories")
router.register(r"products", ProductViewSet, basename="shop-products")
router.register(r"seller/products", SellerProductViewSet, basename="shop-seller-products")
router.register(r"cart", CartViewSet, basename="shop-cart")
router.register(r"orders", OrderViewSet, basename="shop-orders")
router.register(r"wishlist", WishlistViewSet, basename="shop-wishlist")
router.register(r"reviews", ReviewViewSet, basename="shop-reviews")

urlpatterns = router.urls
