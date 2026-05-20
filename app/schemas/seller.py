"""Seller dashboard schemas — sotuvchi paneliga API javoblari."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, computed_field, field_validator


class SellerProductOut(BaseModel):
    """GET /seller/products — sotuvchining mahsulot kartochkasi."""

    id: int
    title: str
    slug: str
    price: Decimal
    discount_price: Optional[Decimal] = None
    currency: str = "UZS"
    stock_quantity: int = 0
    status: str = "draft"
    is_featured: bool = False
    image_url: str = ""
    rating: Decimal = Decimal("0.0")
    reviews_count: int = 0
    views_count: int = 0
    sales_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SellerProductCreate(BaseModel):
    """POST /seller/products — yangi mahsulot yaratish."""

    title: str
    category_id: int
    price: Decimal
    short_description: str = ""
    description: str = ""
    stock_quantity: int = 0
    sku: str = ""
    brand: str = ""
    image_url: str = ""
    status: str = "draft"
    discount_price: Optional[Decimal] = None

    @field_validator("price")
    @classmethod
    def _price_positive(cls, v: Decimal) -> Decimal:
        if v is None or v <= 0:
            raise ValueError("price must be > 0")
        return v

    @field_validator("stock_quantity")
    @classmethod
    def _stock_non_negative(cls, v: int) -> int:
        if v is None or v < 0:
            raise ValueError("stock_quantity must be >= 0")
        return v

    @field_validator("discount_price")
    @classmethod
    def _discount_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("discount_price must be >= 0")
        return v


class SellerProductUpdate(BaseModel):
    """PATCH /seller/products/{id} — barcha maydonlar ixtiyoriy."""

    title: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[Decimal] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    stock_quantity: Optional[int] = None
    sku: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = None
    discount_price: Optional[Decimal] = None

    @field_validator("price")
    @classmethod
    def _price_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("price must be > 0")
        return v

    @field_validator("stock_quantity")
    @classmethod
    def _stock_non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("stock_quantity must be >= 0")
        return v

    @field_validator("discount_price")
    @classmethod
    def _discount_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("discount_price must be >= 0")
        return v


class SellerOrderItemOut(BaseModel):
    """Order item — sotuvchi uchun boyitilgan ko'rinish."""

    id: int
    product_id: int
    title_snapshot: str = ""
    price_snapshot: Decimal
    quantity: int = 1

    @computed_field  # type: ignore[misc]
    @property
    def subtotal(self) -> Decimal:
        return Decimal(self.price_snapshot) * Decimal(self.quantity)

    model_config = {"from_attributes": True}


class SellerOrderOut(BaseModel):
    """GET /seller/orders — sotuvchining buyurtma kartochkasi."""

    id: int
    order_number: str
    customer_id: int
    status: str = "pending"
    payment_status: str = "unpaid"
    total_amount: Decimal = Decimal("0")
    shipping_city: str = ""
    created_at: datetime
    items: list[SellerOrderItemOut] = []
    seller_revenue: Decimal = Decimal("0")

    model_config = {"from_attributes": True}


class SellerStatsOut(BaseModel):
    """GET /seller/stats — sotuvchi paneli umumiy ko'rsatkichlari."""

    total_products: int = 0
    active_products: int = 0
    total_orders: int = 0
    total_revenue: Decimal = Decimal("0")
    top_products: list[dict] = Field(default_factory=list)


class PaginatedSellerProducts(BaseModel):
    count: int
    results: list[SellerProductOut] = []


class PaginatedSellerOrders(BaseModel):
    count: int
    results: list[SellerOrderOut] = []
