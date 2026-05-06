from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from togai.integrations import send_otp_via_telegram, send_sms

from .models import OTPCode
from .serializers import (
    RequestOTPSerializer,
    UserSerializer,
    VerifyOTPSerializer,
    tokens_for,
)

User = get_user_model()


class RequestOTPView(APIView):
    """POST /api/auth/otp/request  {phone}  →  issues OTP (APK uchun, SMS gateway).

    BU APK UCHUN — Eskiz/Play Mobile orqali SMS yuboradi. Webapp uchun
    `TelegramOTPRequestView` (`/api/auth/tg-otp/request/`) ishlatiladi.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = RequestOTPSerializer

    def post(self, request):
        ser = self.serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data["phone"]
        otp = OTPCode.issue(phone)
        if not send_sms(phone, f"Tog'AI tasdiqlash kodi: {otp.code}. Kod 2 daqiqa amal qiladi."):
            return Response(
                {"detail": "SMS yuborilmadi. Keyinroq qayta urinib ko'ring."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        data = {"ok": True, "phone": phone}
        if settings.DEBUG:
            data["dev_code"] = otp.code
        return Response(data, status=status.HTTP_201_CREATED)


class TelegramOTPRequestView(APIView):
    """POST /api/auth/tg-otp/request/  {phone}  →  OTP via Telegram bot (webapp uchun).

    APK'dagi SMS OTP'ga tegmaydi — bu **alohida** webapp endpoint.
    Foydalanuvchi avval botga `/login` qilib telefon raqamini ulashi kerak.
    Telegram_id topilmasa — frontend foydalanuvchini t.me/<bot> ga yo'naltiradi.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = RequestOTPSerializer

    def post(self, request):
        ser = self.serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data["phone"]

        user = User.objects.filter(phone=phone).first()
        # OTP uchun alohida bot — asosiy botdan ajratilgan
        bot_username = (
            getattr(settings, "TELEGRAM_OTP_BOT_USERNAME", "")
            or getattr(settings, "TELEGRAM_BOT_USERNAME", "")
        ).lstrip("@")

        if not user or not user.telegram_id:
            return Response(
                {
                    "detail": (
                        "Telegram orqali kirish uchun avval botga ulaning. "
                        "Botni oching va /login bosib telefon raqamingizni ulashing."
                    ),
                    "telegram_not_linked": True,
                    "bot_username": bot_username or None,
                    "bot_url": f"https://t.me/{bot_username}" if bot_username else None,
                },
                status=status.HTTP_409_CONFLICT,
            )

        otp = OTPCode.issue(phone)
        if not send_otp_via_telegram(user.telegram_id, otp.code):
            return Response(
                {"detail": "Kod yuborilmadi. Botni qayta oching va /login bosing."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        data = {
            "ok": True,
            "phone": phone,
            "channel": "telegram",
            "bot_username": bot_username or None,
        }
        if settings.DEBUG:
            data["dev_code"] = otp.code
        return Response(data, status=status.HTTP_201_CREATED)


class VerifyOTPView(APIView):
    """POST /api/auth/otp/verify  {phone, code, full_name?}
    Agar foydalanuvchi mavjud bo'lmasa, yaratib — JWT qaytaradi."""

    permission_classes = [permissions.AllowAny]
    serializer_class = VerifyOTPSerializer

    def post(self, request):
        ser = self.serializer_class(data=request.data)
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


class QuickAuthView(APIView):
    """POST /api/auth/quick/  {phone, full_name?}
    SMS kod talab qilmaydi — telefon raqami bilan to'g'ridan-to'g'ri JWT beradi.
    SMS gateway integratsiyasi kelgunicha hozirgi vaqtinchalik holat.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = RequestOTPSerializer

    def post(self, request):
        if not settings.QUICK_AUTH_ENABLED:
            return Response(
                {"detail": "Quick auth o'chirilgan. OTP orqali kiring."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = self.serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data["phone"]
        full_name = (request.data.get("full_name") or "").strip()

        user, created = User.objects.get_or_create(phone=phone)
        if full_name and (created or not user.full_name):
            user.full_name = full_name
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
