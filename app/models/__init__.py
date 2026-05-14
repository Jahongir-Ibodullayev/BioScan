"""SQLAlchemy modellari — Django jadvallariga 1:1 mos.

Har bir Django model uchun teng SQLAlchemy model. __tablename__ Django'ning
default jadval nomi (`<app>_<model>`).
"""
from .user import User, OTPCode
from .species import Species
from .observation import Observation, ScanFeedback, TFLiteModel
from .chat import Conversation, Message
from .shop import Category, Product, Order, OrderItem, Review
from .crops import Region, Crop, CropPlan
from .ads import Ad
from .saved import SavedSpecies
from .mapdata import MapMarker

__all__ = [
    "User", "OTPCode",
    "Species",
    "Observation", "ScanFeedback", "TFLiteModel",
    "Conversation", "Message",
    "Category", "Product", "Order", "OrderItem", "Review",
    "Region", "Crop", "CropPlan",
    "Ad",
    "SavedSpecies",
    "MapMarker",
]
