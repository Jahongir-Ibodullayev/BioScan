from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    MeView,
    QuickAuthView,
    RequestOTPView,
    TelegramOTPRequestView,
    VerifyOTPView,
)

urlpatterns = [
    path("quick/", QuickAuthView.as_view(), name="auth-quick"),
    # APK uchun — SMS OTP (Eskiz/Play Mobile)
    path("otp/request/", RequestOTPView.as_view(), name="otp-request"),
    path("otp/verify/", VerifyOTPView.as_view(), name="otp-verify"),
    # Webapp uchun — Telegram bot OTP (alohida, APK'ga tegmaydi)
    path("tg-otp/request/", TelegramOTPRequestView.as_view(), name="tg-otp-request"),
    path("tg-otp/verify/", VerifyOTPView.as_view(), name="tg-otp-verify"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
]
