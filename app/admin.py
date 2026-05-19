"""BioScan admin panel — SQLAdmin (Django admin darajasida).

URL: /admin/   — faqat is_superuser foydalanuvchi (telefon + parol).
Hamma model bo'limlarga ajratilgan: Foydalanuvchilar / Katalog / Shop /
Crops / Incidents / AI / Map.
"""
from __future__ import annotations

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.core.security import create_access_token, decode_token, verify_password
from app.db.session import _get_engine
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


class AdminAuth(AuthenticationBackend):
    """Telefon + parol → faqat is_superuser kira oladi."""

    async def login(self, request: Request) -> bool:
        form = await request.form()
        phone = str(form.get("username", "")).strip()
        password = str(form.get("password", "")).strip()

        from sqlalchemy import select
        from app.db.session import _get_sessionmaker
        sm = _get_sessionmaker()
        async with sm() as db:
            user = await db.scalar(select(User).where(User.phone == phone))
        if not user or not user.is_superuser:
            return False
        if not verify_password(password, user.password):
            return False
        request.session["admin_token"] = create_access_token(user.id, {"admin": True})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("admin_token")
        if not token:
            return False
        payload = decode_token(token)
        return bool(payload and payload.get("admin"))


# ----------------------------------------------------------------------
# Model views — bo'limlarga ajratilgan
# ----------------------------------------------------------------------
class UserAdmin(ModelView, model=User):
    name = "Foydalanuvchi"
    name_plural = "Foydalanuvchilar"
    category = "Foydalanuvchilar"
    icon = "fa-solid fa-user"
    column_list = [User.id, User.phone, User.full_name, User.role, User.account_type, User.is_active, User.is_superuser, User.date_joined]
    column_searchable_list = [User.phone, User.full_name]
    column_sortable_list = [User.id, User.date_joined]
    column_default_sort = ("id", True)
    page_size = 50


class SpeciesAdmin(ModelView, model=Species):
    name = "Tur"
    name_plural = "Turlar (Katalog)"
    category = "Katalog"
    icon = "fa-solid fa-leaf"
    column_list = [Species.id, Species.slug, Species.name, Species.latin, Species.category, Species.red_book, Species.iucn_status]
    column_searchable_list = [Species.name, Species.latin, Species.slug]
    column_sortable_list = [Species.id, Species.name]
    page_size = 50


class ObservationAdmin(ModelView, model=Observation):
    name = "Kuzatuv"
    name_plural = "Kuzatuvlar"
    category = "Katalog"
    icon = "fa-solid fa-binoculars"
    column_list = [Observation.id, Observation.user_id, Observation.species_id, Observation.ai_confidence, Observation.latitude, Observation.longitude, Observation.created_at]
    column_default_sort = ("id", True)
    page_size = 50


class ScanFeedbackAdmin(ModelView, model=ScanFeedback):
    name = "Scan feedback"
    name_plural = "Scan feedback"
    category = "AI"
    icon = "fa-solid fa-comment-dots"
    column_list = [ScanFeedback.id, ScanFeedback.predicted_slug, ScanFeedback.correct_slug, ScanFeedback.is_correct, ScanFeedback.created_at]


class TFLiteModelAdmin(ModelView, model=TFLiteModel):
    name = "TFLite model"
    name_plural = "TFLite modellar (APK)"
    category = "AI"
    icon = "fa-solid fa-microchip"
    column_list = [TFLiteModel.id, TFLiteModel.name, TFLiteModel.version, TFLiteModel.accuracy, TFLiteModel.is_active]


class ConversationAdmin(ModelView, model=Conversation):
    name = "Suhbat"
    name_plural = "AI suhbatlar"
    category = "AI"
    icon = "fa-solid fa-robot"
    column_list = [Conversation.id, Conversation.user_id, Conversation.title, Conversation.created_at]
    column_default_sort = ("id", True)


class MessageAdmin(ModelView, model=Message):
    name = "Xabar"
    name_plural = "Chat xabarlar"
    category = "AI"
    icon = "fa-solid fa-message"
    column_list = [Message.id, Message.conversation_id, Message.role, Message.created_at]


class CategoryAdmin(ModelView, model=Category):
    name = "Kategoriya"
    name_plural = "Shop kategoriyalar"
    category = "Shop"
    icon = "fa-solid fa-tags"
    column_list = [Category.id, Category.name, Category.slug, Category.is_active, Category.order]


class ProductAdmin(ModelView, model=Product):
    name = "Mahsulot"
    name_plural = "Mahsulotlar"
    category = "Shop"
    icon = "fa-solid fa-box"
    column_list = [Product.id, Product.title, Product.price, Product.discount_price, Product.stock_quantity, Product.status, Product.is_featured]
    column_searchable_list = [Product.title, Product.slug]
    column_sortable_list = [Product.id, Product.price, Product.created_at]
    page_size = 50


class OrderAdmin(ModelView, model=Order):
    name = "Buyurtma"
    name_plural = "Buyurtmalar"
    category = "Shop"
    icon = "fa-solid fa-receipt"
    column_list = [Order.id, Order.order_number, Order.customer_id, Order.status, Order.payment_status, Order.total_amount, Order.created_at]
    column_default_sort = ("id", True)


class OrderItemAdmin(ModelView, model=OrderItem):
    name = "Buyurtma item"
    name_plural = "Buyurtma itemlari"
    category = "Shop"
    icon = "fa-solid fa-list"
    column_list = [OrderItem.id, OrderItem.order_id, OrderItem.product_id, OrderItem.quantity, OrderItem.price_snapshot]


class ReviewAdmin(ModelView, model=Review):
    name = "Sharh"
    name_plural = "Sharhlar"
    category = "Shop"
    icon = "fa-solid fa-star"
    column_list = [Review.id, Review.product_id, Review.user_id, Review.rating, Review.created_at]


class CartAdmin(ModelView, model=Cart):
    name = "Savat"
    name_plural = "Savatlar"
    category = "Shop"
    icon = "fa-solid fa-cart-shopping"
    column_list = [Cart.id, Cart.user_id, Cart.created_at]


class WishlistAdmin(ModelView, model=Wishlist):
    name = "Wishlist"
    name_plural = "Wishlist"
    category = "Shop"
    icon = "fa-solid fa-heart"
    column_list = [Wishlist.id, Wishlist.user_id, Wishlist.product_id, Wishlist.added_at]


class RegionAdmin(ModelView, model=Region):
    name = "Viloyat"
    name_plural = "Viloyatlar"
    category = "Crops"
    icon = "fa-solid fa-map-location"
    column_list = [Region.id, Region.slug, Region.name_uz, Region.avg_last_frost_doy, Region.annual_rainfall_mm]


class CropAdmin(ModelView, model=Crop):
    name = "Ekin"
    name_plural = "Ekinlar"
    category = "Crops"
    icon = "fa-solid fa-seedling"
    column_list = [Crop.id, Crop.slug, Crop.name_uz, Crop.category, Crop.water_freq_days]
    column_searchable_list = [Crop.name_uz, Crop.slug]


class CropPlanAdmin(ModelView, model=CropPlan):
    name = "Ekish rejasi"
    name_plural = "Ekish rejalari"
    category = "Crops"
    icon = "fa-solid fa-calendar-check"
    column_list = [CropPlan.id, CropPlan.user_id, CropPlan.crop_id, CropPlan.planned_plant_date, CropPlan.irrigation]


class IncidentAdmin(ModelView, model=Incident):
    name = "Hodisa"
    name_plural = "Xavf hodisalari"
    category = "Incidents"
    icon = "fa-solid fa-triangle-exclamation"
    column_list = [Incident.id, Incident.code, Incident.category, Incident.severity, Incident.status, Incident.created_at]
    column_default_sort = ("id", True)


class AdAdmin(ModelView, model=Ad):
    name = "Reklama"
    name_plural = "Reklamalar"
    category = "Marketing"
    icon = "fa-solid fa-bullhorn"
    column_list = [Ad.id, Ad.title, Ad.slot, Ad.platform, Ad.is_active, Ad.impressions, Ad.clicks]


class MapMarkerAdmin(ModelView, model=MapMarker):
    name = "Xarita marker"
    name_plural = "Xarita markerlari"
    category = "Map"
    icon = "fa-solid fa-location-dot"
    column_list = [MapMarker.id, MapMarker.type, MapMarker.label, MapMarker.latitude, MapMarker.longitude, MapMarker.active]


class SavedSpeciesAdmin(ModelView, model=SavedSpecies):
    name = "Saqlangan tur"
    name_plural = "Saqlangan turlar"
    category = "Katalog"
    icon = "fa-solid fa-bookmark"
    column_list = [SavedSpecies.id, SavedSpecies.user_id, SavedSpecies.species_id, SavedSpecies.created_at]


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
