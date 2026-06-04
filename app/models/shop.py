"""Shop: Category, Product, Order, OrderItem, Review — real Django schema."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import BIGINT_PK


class Category(Base):
    __tablename__ = "shop_category"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True)
    parent_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("shop_category.id", ondelete="CASCADE"), nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Product(Base):
    __tablename__ = "shop_product"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    seller_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("accounts_user.id", ondelete="CASCADE"))
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("shop_category.id", ondelete="RESTRICT"))

    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True)
    short_description: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    ai_generated_description: Mapped[bool] = mapped_column(Boolean, default=False)

    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="UZS")

    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    sku: Mapped[str] = mapped_column(String(64), default="")
    brand: Mapped[str] = mapped_column(String(120), default="")

    status: Mapped[str] = mapped_column(String(20), default="draft")
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)

    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.0"))
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    sales_count: Mapped[int] = mapped_column(Integer, default=0)

    related_species_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("catalog_species.id", ondelete="SET NULL"), nullable=True
    )

    image_url: Mapped[str] = mapped_column(String(500), default="")
    external_url: Mapped[str] = mapped_column(String(600), default="")
    external_seller: Mapped[str] = mapped_column(String(80), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Order(Base):
    """Real Django schema — Order Django jadvalida `customer_id` ishlatadi, `user_id` emas."""
    __tablename__ = "shop_order"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("accounts_user.id", ondelete="CASCADE"))
    order_number: Mapped[str] = mapped_column(String(32), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payment_method: Mapped[str] = mapped_column(String(40), default="cash")
    payment_status: Mapped[str] = mapped_column(String(20), default="unpaid")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    shipping_full_name: Mapped[str] = mapped_column(String(120), default="")
    shipping_phone: Mapped[str] = mapped_column(String(20), default="")
    shipping_address: Mapped[str] = mapped_column(Text, default="")
    shipping_city: Mapped[str] = mapped_column(String(80), default="")
    shipping_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class OrderItem(Base):
    __tablename__ = "shop_orderitem"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("shop_order.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("shop_product.id", ondelete="RESTRICT"))
    title_snapshot: Mapped[str] = mapped_column(String(200), default="")
    price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer, default=1)


class Cart(Base):
    __tablename__ = "shop_cart"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("accounts_user.id", ondelete="CASCADE"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CartItem(Base):
    __tablename__ = "shop_cartitem"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    cart_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("shop_cart.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("shop_product.id", ondelete="CASCADE"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Wishlist(Base):
    __tablename__ = "shop_wishlist"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("accounts_user.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("shop_product.id", ondelete="CASCADE"))
    # Django'da `added_at` deb nomlangan
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Review(Base):
    __tablename__ = "shop_review"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("shop_product.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("accounts_user.id", ondelete="CASCADE"))
    rating: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(140), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
