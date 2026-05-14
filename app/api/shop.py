"""Shop router — /api/shop/products/, /api/shop/categories/, /api/shop/orders/."""
from __future__ import annotations

from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func

from app.api.deps import CurrentUser, DB
from app.models.shop import Category, Order, OrderItem, Product

router = APIRouter(prefix="/shop", tags=["shop"])


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str = ""
    is_active: bool = True
    order: int = 0
    parent_id: int | None = None

    model_config = {"from_attributes": True}


class ProductOut(BaseModel):
    id: int
    seller_id: int
    category_id: int
    title: str
    slug: str
    short_description: str = ""
    description: str = ""
    price: Decimal
    discount_price: Decimal | None = None
    currency: str = "UZS"
    stock_quantity: int = 0
    sku: str = ""
    brand: str = ""
    status: str = "active"
    is_featured: bool = False
    rating: Decimal = Decimal("0")
    reviews_count: int = 0
    image_url: str = ""
    external_url: str = ""
    external_seller: str = ""

    model_config = {"from_attributes": True}


@router.get("/categories/")
async def list_categories(db: DB) -> dict:
    rows = (await db.scalars(
        select(Category).where(Category.is_active == True).order_by(Category.order, Category.name)  # noqa: E712
    )).all()
    return {"results": [CategoryOut.model_validate(r).model_dump() for r in rows]}


@router.get("/products/")
async def list_products(
    db: DB,
    category: str | None = None,
    search: str | None = None,
    featured: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    stmt = select(Product).where(Product.status == "active")
    if category:
        cat = await db.scalar(select(Category).where(Category.slug == category))
        if cat:
            stmt = stmt.where(Product.category_id == cat.id)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(Product.title.ilike(like))
    if featured is not None:
        stmt = stmt.where(Product.is_featured == featured)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(Product.is_featured.desc(), Product.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    rows = (await db.scalars(stmt)).all()
    return {
        "count": total,
        "results": [ProductOut.model_validate(r).model_dump(mode="json") for r in rows],
    }


@router.get("/products/{pk}/")
async def product_detail(pk: int, db: DB) -> dict:
    p = await db.scalar(select(Product).where(Product.id == pk))
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahsulot topilmadi")
    # views count
    p.views_count += 1
    await db.commit()
    return ProductOut.model_validate(p).model_dump(mode="json")


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = 1


class OrderIn(BaseModel):
    items: list[OrderItemIn]
    shipping_full_name: str
    shipping_phone: str
    shipping_address: str
    shipping_city: str = ""
    shipping_notes: str = ""
    payment_method: str = "cash"
    shipping_cost: Decimal = Decimal("0")


def _generate_order_number(user_id: int) -> str:
    """Django'ning order_number formati: BS-<6digit>-<user_id>."""
    import secrets as _s
    return f"BS-{_s.randbelow(900000) + 100000}-{user_id}"


@router.post("/orders/", status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderIn, user: CurrentUser, db: DB) -> dict:
    if not payload.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "items bo'sh bo'lmaslik kerak")

    order = Order(
        customer_id=user.id,
        order_number=_generate_order_number(user.id),
        status="pending",
        payment_method=payload.payment_method,
        payment_status="unpaid",
        shipping_full_name=payload.shipping_full_name,
        shipping_phone=payload.shipping_phone,
        shipping_address=payload.shipping_address,
        shipping_city=payload.shipping_city,
        shipping_notes=payload.shipping_notes,
        shipping_cost=payload.shipping_cost,
    )
    db.add(order)
    await db.flush()  # id

    subtotal = Decimal("0")
    for it in payload.items:
        prod = await db.scalar(select(Product).where(Product.id == it.product_id))
        if not prod:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Mahsulot {it.product_id} yo'q")
        price = prod.discount_price or prod.price
        db.add(OrderItem(
            order_id=order.id,
            product_id=prod.id,
            title_snapshot=prod.title,
            price_snapshot=price,
            quantity=it.quantity,
        ))
        subtotal += price * it.quantity

    order.subtotal = subtotal
    order.total_amount = subtotal + payload.shipping_cost
    await db.commit()
    await db.refresh(order)
    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "subtotal": str(order.subtotal),
        "shipping_cost": str(order.shipping_cost),
        "total_amount": str(order.total_amount),
    }


@router.get("/orders/")
async def my_orders(user: CurrentUser, db: DB) -> dict:
    rows = (await db.scalars(
        select(Order).where(Order.customer_id == user.id).order_by(Order.created_at.desc())
    )).all()
    return {"results": [
        {
            "id": o.id,
            "order_number": o.order_number,
            "status": o.status,
            "payment_status": o.payment_status,
            "total_amount": str(o.total_amount),
            "created_at": o.created_at.isoformat(),
        }
        for o in rows
    ]}
