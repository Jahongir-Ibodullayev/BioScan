from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OTPCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "phone", "full_name", "role", "account_type",
        "verified_member", "has_telegram", "has_fcm",
        "is_staff", "date_joined",
    )
    list_filter = (
        "is_staff", "is_superuser", "verified_member",
        "role", "account_type", "fcm_platform",
    )
    search_fields = ("phone", "full_name", "telegram_username", "seller_name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Shaxsiy ma'lumot", {"fields": (
            "full_name", "role", "avatar", "locale", "verified_member",
        )}),
        ("E-commerce", {"fields": (
            "account_type", "seller_name", "seller_bio", "seller_verified",
        )}),
        ("Telegram", {"fields": ("telegram_id", "telegram_username")}),
        ("Push notifications (Firebase)", {"fields": (
            "fcm_token", "fcm_platform",
        )}),
        ("Ruxsatlar", {"fields": (
            "is_active", "is_staff", "is_superuser",
            "groups", "user_permissions",
        )}),
        ("Muhim sanalar", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": (
            "phone", "full_name", "password1", "password2",
        )}),
    )

    @admin.display(description="Telegram", boolean=True)
    def has_telegram(self, obj):
        return bool(obj.telegram_id)

    @admin.display(description="Push", boolean=True)
    def has_fcm(self, obj):
        return bool(obj.fcm_token)


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ("phone", "code", "used", "created_at")
    list_filter = ("used",)
    search_fields = ("phone",)
    ordering = ("-created_at",)
