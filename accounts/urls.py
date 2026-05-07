from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .push import register_fcm_token, unregister_fcm_token
from .views import (
    MeView,
    QuickAuthView,
    RequestOTPView,
    TelegramOTPRequestView,
    VerifyOTPView,
)

urlpatterns = [
    path("quick/", QuickAuthView.as_view(), name="auth-quick"),
    path("otp/request/", RequestOTPView.as_view(), name="otp-request"),
    path("otp/verify/", VerifyOTPView.as_view(), name="otp-verify"),
    path("tg-otp/request/", TelegramOTPRequestView.as_view(), name="tg-otp-request"),
    path("tg-otp/verify/", VerifyOTPView.as_view(), name="tg-otp-verify"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    # Firebase Cloud Messaging
    path("fcm/register/", register_fcm_token, name="fcm-register"),
    path("fcm/unregister/", unregister_fcm_token, name="fcm-unregister"),
]
