"""Shop router — /api/shop/products/, /api/shop/categories/, /api/shop/orders/."""
from __future__ import annotations

from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func

from app.api.deps import CurrentUser, DB
from app.models.shop import Cart, CartItem, Category, Order, OrderItem, Product, Review, Wishlist
from sqlalchemy import delete

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


# ----------------------------------------------------------------------
# Cart
# ----------------------------------------------------------------------
async def _get_or_create_cart(user_id: int, db) -> Cart:
    cart = await db.scalar(select(Cart).where(Cart.user_id == user_id))
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
    return cart


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = 1


@router.get("/cart/")
async def get_cart(user: CurrentUser, db: DB) -> dict:
    cart = await _get_or_create_cart(user.id, db)
    rows = (await db.scalars(select(CartItem).where(CartItem.cart_id == cart.id))).all()
    items, total = [], Decimal("0")
    for it in rows:
        p = await db.scalar(select(Product).where(Product.id == it.product_id))
        if not p:
            continue
        price = p.discount_price or p.price
        subtotal = price * it.quantity
        total += subtotal
        items.append({
            "id": it.id, "product_id": p.id, "title": p.title,
            "price": str(price), "quantity": it.quantity,
            "subtotal": str(subtotal), "image_url": p.image_url,
        })
    return {"items": items, "total": str(total), "count": len(items)}


@router.post("/cart/add/", status_code=status.HTTP_201_CREATED)
async def cart_add(payload: CartItemIn, user: CurrentUser, db: DB) -> dict:
    cart = await _get_or_create_cart(user.id, db)
    existing = await db.scalar(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == payload.product_id)
    )
    if existing:
        existing.quantity += payload.quantity
    else:
        db.add(CartItem(cart_id=cart.id, product_id=payload.product_id, quantity=payload.quantity))
    await db.commit()
    return {"ok": True}


@router.patch("/cart/update/")
async def cart_update(payload: CartItemIn, user: CurrentUser, db: DB) -> dict:
    cart = await _get_or_create_cart(user.id, db)
    item = await db.scalar(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == payload.product_id)
    )
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahsulot savatda yo'q")
    if payload.quantity <= 0:
        await db.delete(item)
    else:
        item.quantity = payload.quantity
    await db.commit()
    return {"ok": True}


@router.post("/cart/clear/")
async def cart_clear(user: CurrentUser, db: DB) -> dict:
    cart = await _get_or_create_cart(user.id, db)
    await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
    await db.commit()
    return {"ok": True}


# ----------------------------------------------------------------------
# Wishlist
# ----------------------------------------------------------------------
class WishIn(BaseModel):
    product_id: int


@router.get("/wishlist/")
async def list_wishlist(user: CurrentUser, db: DB) -> dict:
    stmt = (
        select(Wishlist, Product)
        .join(Product, Product.id == Wishlist.product_id)
        .where(Wishlist.user_id == user.id)
    )
    rows = (await db.execute(stmt)).all()
    return {"results": [
        {
            "id": w.id, "product_id": p.id, "title": p.title,
            "price": str(p.discount_price or p.price),
            "image_url": p.image_url, "added_at": w.added_at.isoformat(),
        }
        for w, p in rows
    ]}


@router.post("/wishlist/", status_code=status.HTTP_201_CREATED)
async def wishlist_add(payload: WishIn, user: CurrentUser, db: DB) -> dict:
    existing = await db.scalar(
        select(Wishlist).where(Wishlist.user_id == user.id, Wishlist.product_id == payload.product_id)
    )
    if existing:
        return {"ok": True, "already": True}
    db.add(Wishlist(user_id=user.id, product_id=payload.product_id))
    await db.commit()
    return {"ok": True}


@router.delete("/wishlist/{product_id}/")
async def wishlist_remove(product_id: int, user: CurrentUser, db: DB) -> dict:
    await db.execute(
        delete(Wishlist).where(Wishlist.user_id == user.id, Wishlist.product_id == product_id)
    )
    await db.commit()
    return {"ok": True}


# ----------------------------------------------------------------------
# Reviews
# ----------------------------------------------------------------------
class ReviewIn(BaseModel):
    product_id: int
    rating: int
    title: str = ""
    body: str = ""


@router.get("/reviews/")
async def list_reviews(db: DB, product_id: int = Query(...)) -> dict:
    rows = (await db.scalars(
        select(Review).where(Review.product_id == product_id).order_by(Review.created_at.desc())
    )).all()
    return {"results": [
        {
            "id": r.id, "user_id": r.user_id, "rating": r.rating,
            "title": r.title, "body": r.body, "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]}


@router.post("/reviews/", status_code=status.HTTP_201_CREATED)
async def review_create(payload: ReviewIn, user: CurrentUser, db: DB) -> dict:
    if not (1 <= payload.rating <= 5):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "rating 1-5 oralig'ida bo'lsin")
    rev = Review(
        product_id=payload.product_id, user_id=user.id,
        rating=payload.rating, title=payload.title, body=payload.body,
    )
    db.add(rev)
    await db.commit()
    await db.refresh(rev)
    return {"id": rev.id, "ok": True}


@router.post("/orders/checkout/", status_code=status.HTTP_201_CREATED)
async def checkout(payload: OrderIn, user: CurrentUser, db: DB) -> dict:
    """Order yaratish — /orders/ bilan teng (Flutter checkout endpoint)."""
    return await create_order(payload, user, db)


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
