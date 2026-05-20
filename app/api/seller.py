"""Seller dashboard router — /api/seller/*."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select

from app.api.deps import DB, get_current_seller
from app.models.shop import Order, OrderItem, Product
from app.models.user import User
from app.schemas.seller import (
    PaginatedSellerOrders,
    PaginatedSellerProducts,
    SellerOrderItemOut,
    SellerOrderOut,
    SellerProductCreate,
    SellerProductOut,
    SellerProductUpdate,
    SellerStatsOut,
)

router = APIRouter(prefix="/seller", tags=["seller"])


# ============================================================================
# Helpers
# ============================================================================
_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    """Sodda kebab-case slugify (ASCII)."""
    text = (text or "").strip().lower()
    text = _SLUG_NON_ALNUM.sub("-", text).strip("-")
    return text or "product"


async def _unique_slug(db, base: str) -> str:
    """Bazi slug; agar band bo'lsa `-2`, `-3` ... tarzida uniquify."""
    candidate = base
    suffix = 2
    while True:
        exists = await db.scalar(select(Product.id).where(Product.slug == candidate))
        if not exists:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


# ============================================================================
# Products
# ============================================================================
@router.get("/products", response_model=PaginatedSellerProducts)
async def list_seller_products(
    db: DB,
    seller: User = Depends(get_current_seller),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedSellerProducts:
    stmt = select(Product).where(Product.seller_id == seller.id)
    if status_filter:
        stmt = stmt.where(Product.status == status_filter)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(Product.title.ilike(like))

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = (
        stmt.order_by(Product.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.scalars(stmt)).all()
    return PaginatedSellerProducts(
        count=total,
        results=[SellerProductOut.model_validate(r) for r in rows],
    )


@router.post(
    "/products",
    response_model=SellerProductOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_seller_product(
    payload: SellerProductCreate,
    db: DB,
    seller: User = Depends(get_current_seller),
) -> SellerProductOut:
    base_slug = _slugify(payload.title)
    slug = await _unique_slug(db, base_slug)

    now = datetime.now(timezone.utc)
    product = Product(
        seller_id=seller.id,
        category_id=payload.category_id,
        title=payload.title,
        slug=slug,
        short_description=payload.short_description,
        description=payload.description,
        price=payload.price,
        discount_price=payload.discount_price,
        stock_quantity=payload.stock_quantity,
        sku=payload.sku,
        brand=payload.brand,
        image_url=payload.image_url,
        status=payload.status,
        created_at=now,
        updated_at=now,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return SellerProductOut.model_validate(product)


@router.get("/products/{product_id}", response_model=SellerProductOut)
async def get_seller_product(
    product_id: int,
    db: DB,
    seller: User = Depends(get_current_seller),
) -> SellerProductOut:
    product = await db.scalar(
        select(Product).where(
            Product.id == product_id, Product.seller_id == seller.id
        )
    )
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahsulot topilmadi")
    return SellerProductOut.model_validate(product)


@router.patch("/products/{product_id}", response_model=SellerProductOut)
async def update_seller_product(
    product_id: int,
    payload: SellerProductUpdate,
    db: DB,
    seller: User = Depends(get_current_seller),
) -> SellerProductOut:
    product = await db.scalar(
        select(Product).where(
            Product.id == product_id, Product.seller_id == seller.id
        )
    )
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahsulot topilmadi")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(product, field, value)
    product.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(product)
    return SellerProductOut.model_validate(product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seller_product(
    product_id: int,
    db: DB,
    seller: User = Depends(get_current_seller),
) -> None:
    product = await db.scalar(
        select(Product).where(
            Product.id == product_id, Product.seller_id == seller.id
        )
    )
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahsulot topilmadi")
    await db.delete(product)
    await db.commit()
    return None


# ============================================================================
# Orders
# ============================================================================
@router.get("/orders", response_model=PaginatedSellerOrders)
async def list_seller_orders(
    db: DB,
    seller: User = Depends(get_current_seller),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedSellerOrders:
    # Sotuvchining mahsulotlarini o'z ichiga olgan buyurtmalar
    seller_product_ids = select(Product.id).where(Product.seller_id == seller.id)
    order_ids_subq = (
        select(OrderItem.order_id)
        .where(OrderItem.product_id.in_(seller_product_ids))
        .distinct()
    )

    base = select(Order).where(Order.id.in_(order_ids_subq))
    if status_filter:
        base = base.where(Order.status == status_filter)

    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = (
        base.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    orders = (await db.scalars(stmt)).all()

    results: list[SellerOrderOut] = []
    for order in orders:
        # Faqat sotuvchining itemlari
        items_stmt = (
            select(OrderItem)
            .where(
                and_(
                    OrderItem.order_id == order.id,
                    OrderItem.product_id.in_(seller_product_ids),
                )
            )
        )
        items = (await db.scalars(items_stmt)).all()
        items_out = [SellerOrderItemOut.model_validate(it) for it in items]
        revenue = sum(
            (Decimal(it.price_snapshot) * Decimal(it.quantity) for it in items),
            Decimal("0"),
        )
        order_dict = {
            "id": order.id,
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "status": order.status,
            "payment_status": order.payment_status,
            "total_amount": order.total_amount,
            "shipping_city": order.shipping_city,
            "created_at": order.created_at,
            "items": items_out,
            "seller_revenue": revenue,
        }
        results.append(SellerOrderOut.model_validate(order_dict))

    return PaginatedSellerOrders(count=total, results=results)


# ============================================================================
# Stats
# ============================================================================
@router.get("/stats", response_model=SellerStatsOut)
async def seller_stats(
    db: DB,
    seller: User = Depends(get_current_seller),
) -> SellerStatsOut:
    # total_products
    total_products = await db.scalar(
        select(func.count(Product.id)).where(Product.seller_id == seller.id)
    ) or 0

    # active_products
    active_products = await db.scalar(
        select(func.count(Product.id)).where(
            Product.seller_id == seller.id, Product.status == "active"
        )
    ) or 0

    seller_product_ids = select(Product.id).where(Product.seller_id == seller.id)

    # total_orders — distinct orderlar
    total_orders = await db.scalar(
        select(func.count(func.distinct(OrderItem.order_id))).where(
            OrderItem.product_id.in_(seller_product_ids)
        )
    ) or 0

    # total_revenue
    revenue_expr = func.coalesce(
        func.sum(OrderItem.price_snapshot * OrderItem.quantity), 0
    )
    total_revenue = await db.scalar(
        select(revenue_expr).where(OrderItem.product_id.in_(seller_product_ids))
    ) or Decimal("0")

    # top_products — top 5 by revenue
    top_stmt = (
        select(
            OrderItem.product_id,
            func.sum(OrderItem.price_snapshot * OrderItem.quantity).label("revenue"),
            func.sum(OrderItem.quantity).label("units"),
        )
        .where(OrderItem.product_id.in_(seller_product_ids))
        .group_by(OrderItem.product_id)
        .order_by(func.sum(OrderItem.price_snapshot * OrderItem.quantity).desc())
        .limit(5)
    )
    top_rows = (await db.execute(top_stmt)).all()

    top_products: list[dict] = []
    for product_id, revenue, units in top_rows:
        prod = await db.scalar(select(Product).where(Product.id == product_id))
        top_products.append({
            "product_id": product_id,
            "title": prod.title if prod else "",
            "image_url": prod.image_url if prod else "",
            "revenue": str(revenue or Decimal("0")),
            "units_sold": int(units or 0),
        })

    return SellerStatsOut(
        total_products=int(total_products),
        active_products=int(active_products),
        total_orders=int(total_orders),
        total_revenue=Decimal(total_revenue),
        top_products=top_products,
    )
