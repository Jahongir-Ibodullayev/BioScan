from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import OTPCode
from .serializers import (
    RequestOTPSerializer,
    UserSerializer,
    VerifyOTPSerializer,
    tokens_for,
)

User = get_user_model()


class RequestOTPView(APIView):
    """POST /api/auth/otp/request  {phone}  →  issues OTP (returned in dev).

    Productionda SMS gateway (Eskiz, Play Mobile va h.k.) orqali yuborish kerak.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = RequestOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data["phone"]
        otp = OTPCode.issue(phone)
        data = {"ok": True, "phone": phone}
        # DEV only — remove in production
        from django.conf import settings as dj_settings
        if dj_settings.DEBUG:
            data["dev_code"] = otp.code
        return Response(data, status=status.HTTP_201_CREATED)


class VerifyOTPView(APIView):
    """POST /api/auth/otp/verify  {phone, code, full_name?}
    Agar foydalanuvchi mavjud bo'lmasa, yaratib — JWT qaytaradi."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = VerifyOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data["phone"]
        code = ser.validated_data["code"]

        otp = OTPCode.objects.filter(phone=phone, code=code, used=False).first()
        if not otp or not otp.is_valid():
            return Response(
                {"detail": "Kod noto'g'ri yoki eskirgan"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        otp.used = True
        otp.save(update_fields=["used"])

        user, created = User.objects.get_or_create(phone=phone)
        if created and ser.validated_data.get("full_name"):
            user.full_name = ser.validated_data["full_name"]
            user.save(update_fields=["full_name"])

        return Response(
            {"user": UserSerializer(user).data, **tokens_for(user), "new": created},
            status=status.HTTP_200_OK,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """GET / PATCH /api/auth/me  — joriy foydalanuvchi profili."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
