from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import MeView, QuickAuthView, RequestOTPView, VerifyOTPView

urlpatterns = [
    path("quick/", QuickAuthView.as_view(), name="auth-quick"),
    path("otp/request/", RequestOTPView.as_view(), name="otp-request"),
    path("otp/verify/", VerifyOTPView.as_view(), name="otp-verify"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
]
