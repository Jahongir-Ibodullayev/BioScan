import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Phone-based user manager (email optional)."""

    use_in_migrations = True

    def _create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError("Telefon raqam majburiy")
        phone = phone.strip()
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(phone, password, **extra_fields)


class User(AbstractUser):
    username = None  # drop username, use phone
    phone = models.CharField("Telefon", max_length=20, unique=True)
    full_name = models.CharField("To'liq ism", max_length=120, blank=True)
    role = models.CharField(
        "Rol",
        max_length=40,
        default="Turist",
        help_text="O'lkashunos, Biolog, Sherpa, Turist va hokazo",
    )
    avatar = models.ImageField("Avatar", upload_to="avatars/", null=True, blank=True)
    locale = models.CharField("Til", max_length=5, default="uz")
    verified_member = models.BooleanField("Tasdiqlangan a'zo", default=False)

    # E-commerce role: customer (default), seller, super_admin
    ACCOUNT_CUSTOMER = "customer"
    ACCOUNT_SELLER = "seller"
    ACCOUNT_ADMIN = "super_admin"
    ACCOUNT_CHOICES = [
        (ACCOUNT_CUSTOMER, "Mijoz"),
        (ACCOUNT_SELLER, "Sotuvchi"),
        (ACCOUNT_ADMIN, "Super admin"),
    ]
    account_type = models.CharField(
        "Hisob turi", max_length=20, choices=ACCOUNT_CHOICES, default=ACCOUNT_CUSTOMER,
    )
    seller_name = models.CharField("Do'kon nomi", max_length=120, blank=True)
    seller_bio = models.TextField("Sotuvchi haqida", blank=True)
    seller_verified = models.BooleanField("Sotuvchi tasdiqlangan", default=False)

    # Telegram bot OTP — foydalanuvchi botga telefonini ulashganda to'ldiriladi
    telegram_id = models.BigIntegerField(
        "Telegram ID", null=True, blank=True, unique=True, db_index=True,
        help_text="Telegram chat_id — bot orqali OTP yuborish uchun",
    )
    telegram_username = models.CharField(
        "Telegram username", max_length=64, blank=True,
    )

    # Firebase Cloud Messaging — push notification token
    fcm_token = models.CharField(
        "FCM token", max_length=255, blank=True, db_index=True,
        help_text="Firebase Cloud Messaging — push xabarlari uchun",
    )
    fcm_platform = models.CharField(
        "Qurilma platformasi", max_length=20, blank=True,
        help_text="android | ios | web",
    )

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"

    def __str__(self):
        return self.full_name or self.phone


class OTPCode(models.Model):
    """One-time code for phone verification / login."""

    phone = models.CharField(max_length=20, db_index=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)

    @classmethod
    def issue(cls, phone: str) -> "OTPCode":
        code = f"{secrets.randbelow(1_000_000):06d}"
        # Invalidate previous unused OTPs for this phone
        cls.objects.filter(phone=phone, used=False).update(used=True)
        return cls.objects.create(phone=phone, code=code)

    def is_valid(self) -> bool:
        return not self.used and (timezone.now() - self.created_at) < timedelta(minutes=2)

    def __str__(self):
        return f"{self.phone} · ******"
