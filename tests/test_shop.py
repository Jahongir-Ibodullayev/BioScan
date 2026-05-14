"""Shop tests."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.shop import Category, Product
from app.models.user import User
from app.core.security import hash_password
from tests.conftest import _TestSession


async def _seed():
    async with _TestSession() as db:
        seller = User(
            phone="+998900000000",
            password=hash_password("pass"),
            account_type="seller",
            is_active=True,
        )
        db.add(seller)
        await db.flush()
        cat = Category(name="Asal", slug="asal", is_active=True)
        db.add(cat)
        await db.flush()
        p = Product(
            seller_id=seller.id, category_id=cat.id,
            title="Tog' asal", slug="tog-asal",
            price=Decimal("150000"), status="active", stock_quantity=10,
        )
        db.add(p)
        await db.commit()
        return p.id


@pytest.mark.asyncio
async def test_categories_list(client):
    await _seed()
    r = await client.get("/api/shop/categories/")
    assert r.status_code == 200
    assert any(c["slug"] == "asal" for c in r.json()["results"])


@pytest.mark.asyncio
async def test_products_list(client):
    await _seed()
    r = await client.get("/api/shop/products/")
    assert r.status_code == 200
    assert r.json()["count"] == 1


@pytest.mark.asyncio
async def test_product_detail(client):
    pid = await _seed()
    r = await client.get(f"/api/shop/products/{pid}/")
    assert r.status_code == 200
    assert r.json()["title"] == "Tog' asal"
