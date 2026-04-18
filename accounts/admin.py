from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OTPCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("phone", "full_name", "role", "verified_member", "is_staff", "date_joined")
    list_filter = ("is_staff", "is_superuser", "verified_member", "role")
    search_fields = ("phone", "full_name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Shaxsiy ma'lumot", {"fields": ("full_name", "role", "avatar", "locale", "verified_member")}),
        ("Ruxsatlar", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Muhim sanalar", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("phone", "full_name", "password1", "password2")}),
    )


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ("phone", "code", "used", "created_at")
    list_filter = ("used",)
    search_fields = ("phone",)
    ordering = ("-created_at",)
