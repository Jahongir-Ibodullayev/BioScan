from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import MeView, RequestOTPView, VerifyOTPView

urlpatterns = [
    path("otp/request/", RequestOTPView.as_view(), name="otp-request"),
    path("otp/verify/", VerifyOTPView.as_view(), name="otp-verify"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
]
