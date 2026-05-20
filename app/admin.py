"""BioScan admin panel — SQLAdmin (Django admin darajasida) + multi-role.

URL: /admin/   — telefon + parol bilan kirish.

Rollar:
- ADMIN (is_superuser=True) — hammasiga to'liq kirish.
- SELLER (account_type='seller' + seller_verified=True + is_active=True)
       — faqat o'z Shop ma'lumotlari (mahsulot, buyurtma, sharh).
       — Foydalanuvchilar / Katalog / AI / Crops / Incidents / Map ko'rinmaydi.

Permission filterlash `list_query()` orqali — sotuvchi o'zganing satrlarini
URL bilan ham ocha olmaydi (404 emas, lekin filterda bo'lmaydi).
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.sql import Select
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.core.security import create_access_token, decode_token, verify_password
from app.db.session import _get_engine, _get_sessionmaker
from app.models.ads import Ad
from app.models.chat import Conversation, Message
from app.models.crops import Crop, CropPlan, Region
from app.models.incident import Incident
from app.models.mapdata import MapMarker
from app.models.observation import Observation, ScanFeedback, TFLiteModel
from app.models.saved import SavedSpecies
from app.models.shop import Cart, Category, Order, OrderItem, Product, Review, Wishlist
from app.models.species import Species
from app.models.user import User


# ----------------------------------------------------------------------
# Role helpers
# ----------------------------------------------------------------------

ROLE_ADMIN = "admin"
ROLE_SELLER = "seller"


def _admin_ctx(request: Request) -> Optional[dict[str, Any]]:
    """Session tokendan rol kontekstini chiqaradi.

    Qaytaradi: {user_id, role, is_admin} yoki None.
    """
    token = request.session.get("admin_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    role = str(payload.get("admin_role") or "")
    if role not in (ROLE_ADMIN, ROLE_SELLER):
        return None
    return {
        "user_id": int(payload.get("sub") or 0),
        "role": role,
        "is_admin": role == ROLE_ADMIN,
        "is_seller": role == ROLE_SELLER,
    }


def _is_admin(request: Request) -> bool:
    ctx = _admin_ctx(request)
    return bool(ctx and ctx["is_admin"])


def _is_seller(request: Request) -> bool:
    ctx = _admin_ctx(request)
    return bool(ctx and ctx["is_seller"])


def _is_admin_or_seller(request: Request) -> bool:
    return _admin_ctx(request) is not None


# ----------------------------------------------------------------------
# Authentication backend
# ----------------------------------------------------------------------

class AdminAuth(AuthenticationBackend):
    """Telefon + parol → admin yoki tasdiqlangan sotuvchi kira oladi."""

    async def login(self, request: Request) -> bool:
        form = await request.form()
        phone = str(form.get("username", "")).strip()
        password = str(form.get("password", "")).strip()

        sm = _get_sessionmaker()
        async with sm() as db:
            user = await db.scalar(select(User).where(User.phone == phone))

        if not user or not user.is_active:
            return False
        if not verify_password(password, user.password):
            return False

        # Rolni aniqlash
        role: Optional[str] = None
        if user.is_superuser:
            role = ROLE_ADMIN
        elif user.account_type == "seller" and user.seller_verified:
            role = ROLE_SELLER

        if not role:
            return False

        request.session["admin_token"] = create_access_token(
            user.id,
            {"admin_role": role},
        )
        request.session["admin_role"] = role  # tezroq UI uchun
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return _admin_ctx(request) is not None


# ----------------------------------------------------------------------
# Mixin'lar — qulaylik uchun
# ----------------------------------------------------------------------

class AdminOnly:
    """Faqat admin (is_superuser) kirishi mumkin bo'lgan view."""

    def is_accessible(self, request: Request) -> bool:  # type: ignore[override]
        return _is_admin(request)

    def is_visible(self, request: Request) -> bool:  # type: ignore[override]
        return _is_admin(request)


class AdminOrSellerReadOnly:
    """Admin to'liq; sotuvchi faqat ko'radi (create/edit/delete yo'q)."""

    def is_accessible(self, request: Request) -> bool:  # type: ignore[override]
        return _is_admin_or_seller(request)

    def is_visible(self, request: Request) -> bool:  # type: ignore[override]
        return _is_admin_or_seller(request)

    # SQLAdmin'da hodisaviy ruxsat metodlari — sotuvchi uchun read-only
    def can_create(self, request: Request) -> bool:  # type: ignore[override]
        return _is_admin(request)

    def can_edit(self, request: Request) -> bool:  # type: ignore[override]
        return _is_admin(request)

    def can_delete(self, request: Request) -> bool:  # type: ignore[override]
        return _is_admin(request)


# ----------------------------------------------------------------------
# Model views — bo'limlarga ajratilgan
# ----------------------------------------------------------------------

class UserAdmin(AdminOnly, ModelView, model=User):
    name = "Foydalanuvchi"
    name_plural = "Foydalanuvchilar"
    category = "Foydalanuvchilar"
    icon = "fa-solid fa-user"
    column_list = [User.id, User.phone, User.full_name, User.role, User.account_type, User.seller_verified, User.is_active, User.is_superuser, User.date_joined]
    column_searchable_list = [User.phone, User.full_name]
    column_sortable_list = [User.id, User.date_joined]
    column_default_sort = ("id", True)
    page_size = 50


class SpeciesAdmin(AdminOnly, ModelView, model=Species):
    name = "Tur"
    name_plural = "Turlar (Katalog)"
    category = "Katalog"
    icon = "fa-solid fa-leaf"
    column_list = [Species.id, Species.slug, Species.name, Species.latin, Species.category, Species.red_book, Species.iucn_status]
    column_searchable_list = [Species.name, Species.latin, Species.slug]
    column_sortable_list = [Species.id, Species.name]
    page_size = 50


class ObservationAdmin(AdminOnly, ModelView, model=Observation):
    name = "Kuzatuv"
    name_plural = "Kuzatuvlar"
    category = "Katalog"
    icon = "fa-solid fa-binoculars"
    column_list = [Observation.id, Observation.user_id, Observation.species_id, Observation.ai_confidence, Observation.latitude, Observation.longitude, Observation.created_at]
    column_default_sort = ("id", True)
    page_size = 50


class ScanFeedbackAdmin(AdminOnly, ModelView, model=ScanFeedback):
    name = "Scan feedback"
    name_plural = "Scan feedback"
    category = "AI"
    icon = "fa-solid fa-comment-dots"
    column_list = [ScanFeedback.id, ScanFeedback.predicted_slug, ScanFeedback.correct_slug, ScanFeedback.is_correct, ScanFeedback.created_at]


class TFLiteModelAdmin(AdminOnly, ModelView, model=TFLiteModel):
    name = "TFLite model"
    name_plural = "TFLite modellar (APK)"
    category = "AI"
    icon = "fa-solid fa-microchip"
    column_list = [TFLiteModel.id, TFLiteModel.name, TFLiteModel.version, TFLiteModel.accuracy, TFLiteModel.is_active]


class ConversationAdmin(AdminOnly, ModelView, model=Conversation):
    name = "Suhbat"
    name_plural = "AI suhbatlar"
    category = "AI"
    icon = "fa-solid fa-robot"
    column_list = [Conversation.id, Conversation.user_id, Conversation.title, Conversation.created_at]
    column_default_sort = ("id", True)


class MessageAdmin(AdminOnly, ModelView, model=Message):
    name = "Xabar"
    name_plural = "Chat xabarlar"
    category = "AI"
    icon = "fa-solid fa-message"
    column_list = [Message.id, Message.conversation_id, Message.role, Message.created_at]


class CategoryAdmin(AdminOnly, ModelView, model=Category):
    """Kategoriyalar — faqat admin (sotuvchi yangi kategoriya yarata olmaydi)."""
    name = "Kategoriya"
    name_plural = "Shop kategoriyalar"
    category = "Shop"
    icon = "fa-solid fa-tags"
    column_list = [Category.id, Category.name, Category.slug, Category.is_active, Category.order]


# --- Shop modellari — sotuvchi o'z hududini ko'radi ---

class ProductAdmin(ModelView, model=Product):
    """Mahsulot — admin hammasini, sotuvchi faqat o'z mahsulotlarini ko'radi."""
    name = "Mahsulot"
    name_plural = "Mahsulotlar"
    category = "Shop"
    icon = "fa-solid fa-box"
    column_list = [Product.id, Product.seller_id, Product.title, Product.price, Product.discount_price, Product.stock_quantity, Product.status, Product.is_featured]
    column_searchable_list = [Product.title, Product.slug]
    column_sortable_list = [Product.id, Product.price, Product.created_at]
    page_size = 50

    def is_accessible(self, request: Request) -> bool:
        return _is_admin_or_seller(request)

    def is_visible(self, request: Request) -> bool:
        return _is_admin_or_seller(request)

    def list_query(self, request: Request) -> Select:
        q = super().list_query(request)
        ctx = _admin_ctx(request)
        if ctx and ctx["is_seller"]:
            q = q.where(Product.seller_id == ctx["user_id"])
        return q

    # Sotuvchi o'z mahsulotini qo'sha/o'zgartira oladi.
    # Lekin u boshqaning satrini list_query orqali umuman ko'rmaydi.


class OrderAdmin(ModelView, model=Order):
    """Buyurtma — admin hammasini; sotuvchi: o'z mahsulotlari kirgan buyurtmalar."""
    name = "Buyurtma"
    name_plural = "Buyurtmalar"
    category = "Shop"
    icon = "fa-solid fa-receipt"
    column_list = [Order.id, Order.order_number, Order.customer_id, Order.status, Order.payment_status, Order.total_amount, Order.created_at]
    column_default_sort = ("id", True)

    def is_accessible(self, request: Request) -> bool:
        return _is_admin_or_seller(request)

    def is_visible(self, request: Request) -> bool:
        return _is_admin_or_seller(request)

    # Sotuvchi buyurtma yarata/o'zgartira olmaydi — read-only.
    def can_create(self, request: Request) -> bool:
        return _is_admin(request)

    def can_delete(self, request: Request) -> bool:
        return _is_admin(request)

    def list_query(self, request: Request) -> Select:
        q = super().list_query(request)
        ctx = _admin_ctx(request)
        if ctx and ctx["is_seller"]:
            # Buyurtma sotuvchi mahsulotini o'z ichiga olsa — ko'rinadi.
            sub = select(OrderItem.order_id).join(Product, Product.id == OrderItem.product_id).where(Product.seller_id == ctx["user_id"])
            q = q.where(Order.id.in_(sub))
        return q


class OrderItemAdmin(ModelView, model=OrderItem):
    """Buyurtma itemlari — sotuvchi: o'z mahsulotlari itemlari."""
    name = "Buyurtma item"
    name_plural = "Buyurtma itemlari"
    category = "Shop"
    icon = "fa-solid fa-list"
    column_list = [OrderItem.id, OrderItem.order_id, OrderItem.product_id, OrderItem.quantity, OrderItem.price_snapshot]

    def is_accessible(self, request: Request) -> bool:
        return _is_admin_or_seller(request)

    def is_visible(self, request: Request) -> bool:
        return _is_admin_or_seller(request)

    def can_create(self, request: Request) -> bool:
        return _is_admin(request)

    def can_edit(self, request: Request) -> bool:
        return _is_admin(request)

    def can_delete(self, request: Request) -> bool:
        return _is_admin(request)

    def list_query(self, request: Request) -> Select:
        q = super().list_query(request)
        ctx = _admin_ctx(request)
        if ctx and ctx["is_seller"]:
            sub = select(Product.id).where(Product.seller_id == ctx["user_id"])
            q = q.where(OrderItem.product_id.in_(sub))
        return q


class ReviewAdmin(ModelView, model=Review):
    """Sharhlar — admin hammasini; sotuvchi: o'z mahsulotlariga sharh."""
    name = "Sharh"
    name_plural = "Sharhlar"
    category = "Shop"
    icon = "fa-solid fa-star"
    column_list = [Review.id, Review.product_id, Review.user_id, Review.rating, Review.created_at]

    def is_accessible(self, request: Request) -> bool:
        return _is_admin_or_seller(request)

    def is_visible(self, request: Request) -> bool:
        return _is_admin_or_seller(request)

    def can_create(self, request: Request) -> bool:
        return _is_admin(request)

    def can_edit(self, request: Request) -> bool:
        return _is_admin(request)

    # Sotuvchi yomon sharhni o'chira olmaydi — faqat admin
    def can_delete(self, request: Request) -> bool:
        return _is_admin(request)

    def list_query(self, request: Request) -> Select:
        q = super().list_query(request)
        ctx = _admin_ctx(request)
        if ctx and ctx["is_seller"]:
            sub = select(Product.id).where(Product.seller_id == ctx["user_id"])
            q = q.where(Review.product_id.in_(sub))
        return q


class CartAdmin(AdminOnly, ModelView, model=Cart):
    """Savatlar — faqat admin (sotuvchiga kerak emas, foydalanuvchi shaxsiy)."""
    name = "Savat"
    name_plural = "Savatlar"
    category = "Shop"
    icon = "fa-solid fa-cart-shopping"
    column_list = [Cart.id, Cart.user_id, Cart.created_at]


class WishlistAdmin(AdminOnly, ModelView, model=Wishlist):
    """Wishlist — faqat admin."""
    name = "Wishlist"
    name_plural = "Wishlist"
    category = "Shop"
    icon = "fa-solid fa-heart"
    column_list = [Wishlist.id, Wishlist.user_id, Wishlist.product_id, Wishlist.added_at]


# --- Sotuvchidan ko'rinmaydigan bo'limlar ---

class RegionAdmin(AdminOnly, ModelView, model=Region):
    name = "Viloyat"
    name_plural = "Viloyatlar"
    category = "Crops"
    icon = "fa-solid fa-map-location"
    column_list = [Region.id, Region.slug, Region.name_uz, Region.avg_last_frost_doy, Region.annual_rainfall_mm]


class CropAdmin(AdminOnly, ModelView, model=Crop):
    name = "Ekin"
    name_plural = "Ekinlar"
    category = "Crops"
    icon = "fa-solid fa-seedling"
    column_list = [Crop.id, Crop.slug, Crop.name_uz, Crop.category, Crop.water_freq_days]
    column_searchable_list = [Crop.name_uz, Crop.slug]


class CropPlanAdmin(AdminOnly, ModelView, model=CropPlan):
    name = "Ekish rejasi"
    name_plural = "Ekish rejalari"
    category = "Crops"
    icon = "fa-solid fa-calendar-check"
    column_list = [CropPlan.id, CropPlan.user_id, CropPlan.crop_id, CropPlan.planned_plant_date, CropPlan.irrigation]


class IncidentAdmin(AdminOnly, ModelView, model=Incident):
    name = "Hodisa"
    name_plural = "Xavf hodisalari"
    category = "Incidents"
    icon = "fa-solid fa-triangle-exclamation"
    column_list = [Incident.id, Incident.code, Incident.category, Incident.severity, Incident.status, Incident.created_at]
    column_default_sort = ("id", True)


class AdAdmin(AdminOnly, ModelView, model=Ad):
    name = "Reklama"
    name_plural = "Reklamalar"
    category = "Marketing"
    icon = "fa-solid fa-bullhorn"
    column_list = [Ad.id, Ad.title, Ad.slot, Ad.platform, Ad.is_active, Ad.impressions, Ad.clicks]


class MapMarkerAdmin(AdminOnly, ModelView, model=MapMarker):
    name = "Xarita marker"
    name_plural = "Xarita markerlari"
    category = "Map"
    icon = "fa-solid fa-location-dot"
    column_list = [MapMarker.id, MapMarker.type, MapMarker.label, MapMarker.latitude, MapMarker.longitude, MapMarker.active]


class SavedSpeciesAdmin(AdminOnly, ModelView, model=SavedSpecies):
    name = "Saqlangan tur"
    name_plural = "Saqlangan turlar"
    category = "Katalog"
    icon = "fa-solid fa-bookmark"
    column_list = [SavedSpecies.id, SavedSpecies.user_id, SavedSpecies.species_id, SavedSpecies.created_at]


# ----------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------

def setup_admin(app, secret_key: str) -> Admin:
    """main.py'dan chaqiriladi — admin'ni FastAPI'ga ulaydi."""
    admin = Admin(
        app,
        engine=_get_engine(),
        title="BioScan Admin",
        authentication_backend=AdminAuth(secret_key=secret_key),
        base_url="/admin",
    )
    for view in [
        UserAdmin, SpeciesAdmin, ObservationAdmin, SavedSpeciesAdmin,
        ScanFeedbackAdmin, TFLiteModelAdmin, ConversationAdmin, MessageAdmin,
        CategoryAdmin, ProductAdmin, OrderAdmin, OrderItemAdmin, ReviewAdmin,
        CartAdmin, WishlistAdmin,
        RegionAdmin, CropAdmin, CropPlanAdmin,
        IncidentAdmin, AdAdmin, MapMarkerAdmin,
    ]:
        admin.add_view(view)
    return admin
