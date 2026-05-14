"""Shop router — /api/shop/* (webapp + Flutter contract).

Asosiy farqlar:
  - /shop/categories/ — to'g'ridan-to'g'ri ARRAY qaytaradi (Flutter shunday kutadi)
  - /shop/products/   — `q` va `search` ikkalasi ham qabul qilinadi
  - /shop/cart/update/ — POST (Flutter) va PATCH ham qo'llab quvvatlanadi
  - /shop/cart/update/ body: {item_id, quantity} (Flutter) yoki {product_id, quantity}
  - /shop/orders/checkout/ — cart'dan order yaratadi (items kerak emas)
  - /shop/wishlist/{wishlist_item_id}/ DELETE — wishlist.id ishlatadi (Flutter)
  - /shop/reviews/ — `product` va `product_id` ikkalasi qabul qilinadi
"""
from __future__ import annotations

import secrets as _s
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select

from app.api.deps import CurrentUser, DB
from app.models.shop import Cart, CartItem, Category, Order, OrderItem, Product, Review, Wishlist
from app.schemas.common import paginated

router = APIRouter(prefix="/shop", tags=["shop"])


# ============================================================================
# Schemas
# ============================================================================
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


# ============================================================================
# Categories
# ============================================================================
@router.get("/categories/")
async def list_categories(db: DB) -> list[dict]:
    """Flutter to'g'ridan-to'g'ri array kutadi (not {results})."""
    rows = (await db.scalars(
        select(Category).where(Category.is_active == True).order_by(Category.order, Category.name)  # noqa: E712
    )).all()
    return [CategoryOut.model_validate(r).model_dump() for r in rows]


# ============================================================================
# Products
# ============================================================================
@router.get("/products/")
async def list_products(
    db: DB,
    category: str | None = None,
    # Webapp `search`, Flutter `q` — ikkalasini ham qabul qilamiz
    search: str | None = None,
    q: str | None = None,
    featured: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    query = search or q
    stmt = select(Product).where(Product.status == "active")
    if category:
        cat = await db.scalar(select(Category).where(Category.slug == category))
        if cat:
            stmt = stmt.where(Product.category_id == cat.id)
    if query:
        like = f"%{query}%"
        stmt = stmt.where(Product.title.ilike(like))
    if featured is not None:
        stmt = stmt.where(Product.is_featured == featured)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = (
        stmt.order_by(Product.is_featured.desc(), Product.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    rows = (await db.scalars(stmt)).all()
    items = [ProductOut.model_validate(r).model_dump(mode="json") for r in rows]
    return paginated(items, total=total, page=page, page_size=page_size)


@router.get("/products/{pk}/")
async def product_detail(pk: int, db: DB) -> dict:
    p = await db.scalar(select(Product).where(Product.id == pk))
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahsulot topilmadi")
    p.views_count += 1
    await db.commit()
    return ProductOut.model_validate(p).model_dump(mode="json")


# ============================================================================
# Cart
# ============================================================================
async def _get_or_create_cart(user_id: int, db) -> Cart:
    cart = await db.scalar(select(Cart).where(Cart.user_id == user_id))
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
    return cart


class CartAddIn(BaseModel):
    product_id: int
    quantity: int = 1


class CartUpdateIn(BaseModel):
    # Flutter: item_id (CartItem.id), Webapp: product_id
    item_id: int | None = None
    product_id: int | None = None
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
    return {"items": items, "total": str(total), "count": len(items), "cart_id": cart.id}


@router.post("/cart/add/", status_code=status.HTTP_201_CREATED)
async def cart_add(payload: CartAddIn, user: CurrentUser, db: DB) -> dict:
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


async def _cart_update_impl(payload: CartUpdateIn, user, db) -> dict:
    cart = await _get_or_create_cart(user.id, db)
    if payload.item_id:
        item = await db.scalar(
            select(CartItem).where(CartItem.id == payload.item_id, CartItem.cart_id == cart.id)
        )
    elif payload.product_id:
        item = await db.scalar(
            select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == payload.product_id)
        )
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "item_id yoki product_id majburiy")
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Savatda yo'q")
    if payload.quantity <= 0:
        await db.delete(item)
    else:
        item.quantity = payload.quantity
    await db.commit()
    return {"ok": True}


@router.post("/cart/update/")
async def cart_update_post(payload: CartUpdateIn, user: CurrentUser, db: DB) -> dict:
    """Flutter POST. PATCH alias quyida."""
    return await _cart_update_impl(payload, user, db)


@router.patch("/cart/update/")
async def cart_update_patch(payload: CartUpdateIn, user: CurrentUser, db: DB) -> dict:
    return await _cart_update_impl(payload, user, db)


@router.post("/cart/clear/")
async def cart_clear(user: CurrentUser, db: DB) -> dict:
    cart = await _get_or_create_cart(user.id, db)
    await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
    await db.commit()
    return {"ok": True}


# ============================================================================
# Wishlist
# ============================================================================
class WishIn(BaseModel):
    product_id: int


@router.get("/wishlist/")
async def list_wishlist(
    user: CurrentUser, db: DB,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
) -> dict:
    base = select(Wishlist).where(Wishlist.user_id == user.id)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = (
        select(Wishlist, Product)
        .join(Product, Product.id == Wishlist.product_id)
        .where(Wishlist.user_id == user.id)
        .order_by(Wishlist.added_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    rows = (await db.execute(stmt)).all()
    items = [
        {
            "id": w.id, "product_id": p.id, "title": p.title,
            "price": str(p.discount_price or p.price),
            "image_url": p.image_url, "added_at": w.added_at.isoformat(),
        }
        for w, p in rows
    ]
    return paginated(items, total=total, page=page, page_size=page_size)


@router.post("/wishlist/", status_code=status.HTTP_201_CREATED)
async def wishlist_add(payload: WishIn, user: CurrentUser, db: DB) -> dict:
    existing = await db.scalar(
        select(Wishlist).where(Wishlist.user_id == user.id, Wishlist.product_id == payload.product_id)
    )
    if existing:
        return {"ok": True, "already": True, "id": existing.id}
    item = Wishlist(user_id=user.id, product_id=payload.product_id)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"ok": True, "id": item.id}


@router.delete("/wishlist/{wishlist_id}/")
async def wishlist_remove(wishlist_id: int, user: CurrentUser, db: DB) -> dict:
    """Flutter wishlist.id yuboradi."""
    item = await db.scalar(
        select(Wishlist).where(Wishlist.id == wishlist_id, Wishlist.user_id == user.id)
    )
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Wishlist'da yo'q")
    await db.delete(item)
    await db.commit()
    return {"ok": True}


# ============================================================================
# Reviews
# ============================================================================
class ReviewIn(BaseModel):
    # Webapp `product_id`, Flutter `product` — ikkalasi ham qabul qilinadi
    product: int | None = None
    product_id: int | None = None
    rating: int
    # Webapp `title+body`, Flutter `comment` — moslashuvchan
    title: str = ""
    body: str = ""
    comment: str | None = None


@router.get("/reviews/")
async def list_reviews(
    db: DB,
    product: int | None = None,
    product_id: int | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
) -> dict:
    pid = product or product_id
    base = select(Review)
    if pid is not None:
        base = base.where(Review.product_id == pid)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = base.order_by(Review.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.scalars(stmt)).all()
    items = [
        {
            "id": r.id, "user_id": r.user_id, "rating": r.rating,
            "title": r.title, "body": r.body, "comment": r.body,
            "product_id": r.product_id,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
    return paginated(items, total=total, page=page, page_size=page_size)


@router.post("/reviews/", status_code=status.HTTP_201_CREATED)
async def review_create(payload: ReviewIn, user: CurrentUser, db: DB) -> dict:
    pid = payload.product_id or payload.product
    if pid is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "product_id majburiy")
    if not (1 <= payload.rating <= 5):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "rating 1-5 oralig'ida bo'lsin")
    rev = Review(
        product_id=pid, user_id=user.id, rating=payload.rating,
        title=payload.title or "",
        body=payload.body or payload.comment or "",
    )
    db.add(rev)
    await db.commit()
    await db.refresh(rev)
    return {"id": rev.id, "ok": True}


# ============================================================================
# Orders + Checkout
# ============================================================================
class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = 1


class OrderIn(BaseModel):
    items: list[OrderItemIn] = []  # ixtiyoriy — cart'dan ham olinadi
    shipping_full_name: str = ""
    shipping_phone: str = ""
    shipping_address: str = ""
    shipping_city: str = ""
    shipping_notes: str = ""
    payment_method: str = "cash"
    shipping_cost: Decimal = Decimal("0")


def _gen_order_number(user_id: int) -> str:
    return f"BS-{_s.randbelow(900000) + 100000}-{user_id}"


async def _create_order_impl(payload: OrderIn, user, db, use_cart: bool = False) -> dict:
    # Items'larni belgilash
    items = list(payload.items)
    if use_cart and not items:
        # Cart'dan olish
        cart = await _get_or_create_cart(user.id, db)
        cart_items = (await db.scalars(select(CartItem).where(CartItem.cart_id == cart.id))).all()
        items = [OrderItemIn(product_id=ci.product_id, quantity=ci.quantity) for ci in cart_items]

    if not items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "items yoki cart bo'sh")

    order = Order(
        customer_id=user.id,
        order_number=_gen_order_number(user.id),
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
    await db.flush()

    subtotal = Decimal("0")
    for it in items:
        prod = await db.scalar(select(Product).where(Product.id == it.product_id))
        if not prod:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Mahsulot {it.product_id} yo'q")
        price = prod.discount_price or prod.price
        db.add(OrderItem(
            order_id=order.id, product_id=prod.id,
            title_snapshot=prod.title, price_snapshot=price, quantity=it.quantity,
        ))
        subtotal += price * it.quantity

    order.subtotal = subtotal
    order.total_amount = subtotal + payload.shipping_cost
    await db.commit()
    await db.refresh(order)

    # Cart'ni tozalash (checkout uchun)
    if use_cart:
        cart = await _get_or_create_cart(user.id, db)
        await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        await db.commit()

    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "payment_status": order.payment_status,
        "subtotal": str(order.subtotal),
        "shipping_cost": str(order.shipping_cost),
        "total_amount": str(order.total_amount),
        "created_at": order.created_at.isoformat(),
    }


@router.post("/orders/", status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderIn, user: CurrentUser, db: DB) -> dict:
    return await _create_order_impl(payload, user, db, use_cart=False)


@router.post("/orders/checkout/", status_code=status.HTTP_201_CREATED)
async def checkout(payload: OrderIn, user: CurrentUser, db: DB) -> dict:
    """Flutter: cart bilan checkout — items berilmasa, cart'dan oladi."""
    return await _create_order_impl(payload, user, db, use_cart=True)


@router.get("/orders/")
async def my_orders(
    user: CurrentUser, db: DB,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
) -> dict:
    base = select(Order).where(Order.customer_id == user.id)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = base.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.scalars(stmt)).all()
    items = [
        {
            "id": o.id, "order_number": o.order_number, "status": o.status,
            "payment_status": o.payment_status,
            "subtotal": str(o.subtotal), "shipping_cost": str(o.shipping_cost),
            "total_amount": str(o.total_amount),
            "shipping_full_name": o.shipping_full_name,
            "shipping_phone": o.shipping_phone,
            "shipping_address": o.shipping_address,
            "created_at": o.created_at.isoformat(),
        }
        for o in rows
    ]
    return paginated(items, total=total, page=page, page_size=page_size)


@router.get("/orders/{order_id}/")
async def order_detail(order_id: int, user: CurrentUser, db: DB) -> dict:
    o = await db.scalar(
        select(Order).where(Order.id == order_id, Order.customer_id == user.id)
    )
    if not o:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Buyurtma topilmadi")
    items = (await db.scalars(select(OrderItem).where(OrderItem.order_id == o.id))).all()
    return {
        "id": o.id, "order_number": o.order_number, "status": o.status,
        "payment_status": o.payment_status, "payment_method": o.payment_method,
        "subtotal": str(o.subtotal), "shipping_cost": str(o.shipping_cost),
        "total_amount": str(o.total_amount),
        "shipping_full_name": o.shipping_full_name,
        "shipping_phone": o.shipping_phone,
        "shipping_address": o.shipping_address,
        "shipping_city": o.shipping_city,
        "shipping_notes": o.shipping_notes,
        "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
        "created_at": o.created_at.isoformat(),
        "items": [
            {
                "id": it.id, "product_id": it.product_id,
                "title": it.title_snapshot, "price": str(it.price_snapshot),
                "quantity": it.quantity,
            }
            for it in items
        ],
    }
