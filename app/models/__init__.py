"""SQLAlchemy modellari — Django jadvallariga 1:1 mos.

Har bir Django model uchun teng SQLAlchemy model. __tablename__ Django'ning
default jadval nomi (`<app>_<model>`).
"""
from .ads import Ad
from .chat import Conversation, Message
from .crops import Crop, CropPlan, Region
from .incident import Incident
from .mapdata import MapMarker
from .observation import Observation, ScanFeedback, TFLiteModel
from .saved import SavedSpecies
from .shop import Cart, CartItem, Category, Order, OrderItem, Product, Review, Wishlist
from .species import Species
from .user import User

__all__ = [
    "User",
    "Species",
    "Observation", "ScanFeedback", "TFLiteModel",
    "Conversation", "Message",
    "Category", "Product", "Order", "OrderItem", "Review", "Cart", "CartItem", "Wishlist",
    "Region", "Crop", "CropPlan",
    "Ad",
    "SavedSpecies",
    "MapMarker",
    "Incident",
]
