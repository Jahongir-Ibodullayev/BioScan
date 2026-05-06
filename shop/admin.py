from django.contrib import admin

from .models import (
    Cart, CartItem, Category, Order, OrderItem, Product, ProductImage,
    Review, Wishlist,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "order")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "category", "price", "stock_quantity", "status", "is_featured", "rating")
    list_filter = ("status", "is_featured", "category")
    search_fields = ("title", "sku", "brand")
    readonly_fields = ("rating", "reviews_count", "views_count", "sales_count", "created_at")
    inlines = [ProductImageInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "title_snapshot", "price_snapshot", "quantity", "subtotal")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer", "status", "payment_method", "total_amount", "created_at")
    list_filter = ("status", "payment_method")
    search_fields = ("order_number", "customer__phone")
    readonly_fields = ("order_number", "subtotal", "total_amount", "created_at", "updated_at")
    inlines = [OrderItemInline]


admin.site.register([Cart, CartItem, Wishlist, Review])
