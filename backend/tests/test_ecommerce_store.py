import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.models import Customer, Product


@pytest.mark.asyncio
async def test_store_config_and_policy(client: AsyncClient, db_session: AsyncSession):
    # GET /config
    resp = await client.get("/config")
    assert resp.status_code == 200
    cfg = resp.json()
    assert "store_name" in cfg
    assert cfg["return_window_days"] == 7
    assert Decimal(str(cfg["refund_auto_approve_limit_inr"])) == Decimal("2000.00")

    # GET /policy/en
    resp_en = await client.get("/policy/en")
    assert resp_en.status_code == 200
    assert "Return" in resp_en.text or "Policy" in resp_en.text or len(resp_en.text) > 0

    # GET /policy/ta
    resp_ta = await client.get("/policy/ta")
    assert resp_ta.status_code == 200


@pytest.mark.asyncio
async def test_customer_auth_lifecycle(client: AsyncClient, db_session: AsyncSession):
    csrf_headers = {"X-Requested-With": "shop-web"}

    # 1. Register
    reg_payload = {
        "email": "testbuyer@example.com",
        "password": "Password123!",
        "name": "Test Buyer",
        "phone": "+919888877777",
        "preferred_language": "en",
    }
    reg_res = await client.post("/auth/register", json=reg_payload, headers=csrf_headers)
    assert reg_res.status_code == 200
    data = reg_res.json()
    assert data["email"] == "testbuyer@example.com"
    assert "shop_session" in client.cookies

    # 2. Duplicate registration conflict
    dup_res = await client.post("/auth/register", json=reg_payload, headers=csrf_headers)
    assert dup_res.status_code == 409

    # 3. GET /auth/me
    me_res = await client.get("/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Test Buyer"

    # 4. PATCH /auth/me
    patch_res = await client.patch(
        "/auth/me",
        json={"name": "Buyer Updated", "preferred_language": "ta"},
        headers=csrf_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Buyer Updated"
    assert patch_res.json()["preferred_language"] == "ta"

    # 5. Change Password
    cp_res = await client.post(
        "/auth/change-password",
        json={"old_password": "Password123!", "new_password": "NewSecretPassword1!"},
        headers=csrf_headers,
    )
    assert cp_res.status_code == 200
    assert cp_res.json()["ok"] is True

    # 6. Logout
    logout_res = await client.post("/auth/logout", headers=csrf_headers)
    assert logout_res.status_code == 200

    # After logout, /auth/me fails with 401
    me_unauth = await client.get("/auth/me")
    assert me_unauth.status_code == 401

    # 7. Login with old password fails
    bad_login = await client.post(
        "/auth/login",
        json={"email": "testbuyer@example.com", "password": "Password123!"},
        headers=csrf_headers,
    )
    assert bad_login.status_code == 401

    # 8. Login with new password succeeds
    good_login = await client.post(
        "/auth/login",
        json={"email": "testbuyer@example.com", "password": "NewSecretPassword1!"},
        headers=csrf_headers,
    )
    assert good_login.status_code == 200
    assert good_login.json()["email"] == "testbuyer@example.com"


@pytest.mark.asyncio
async def test_product_catalog_and_svg_images(client: AsyncClient, db_session: AsyncSession):
    # Seed 2 test products
    p1 = Product(
        sku="TEST-SKU-001",
        name_en="Kanchipuram Silk Saree",
        name_ta="காஞ்சிபுரம் பட்டுப் புடவை",
        category="Traditional & Ethnic Wear",
        description_en="Pure handloom silk saree with zari border",
        description_ta="கைத்தறி பட்டு புடவை",
        price=Decimal("4999.00"),
        stock_qty=15,
        rating=Decimal("4.8"),
        is_active=True,
        content_hash="hash_p1",
        embedding=[0.01] * 384,
    )
    p2 = Product(
        sku="TEST-SKU-002",
        name_en="Bluetooth Wireless Earbuds",
        name_ta="ப்ளூடூத் வயர்லெஸ் இயர்பட்ஸ்",
        category="Electronics",
        description_en="Compact wireless earbuds with deep bass",
        description_ta="வயர்லெஸ் இயர்பட்ஸ்",
        price=Decimal("1299.00"),
        stock_qty=20,
        rating=Decimal("4.5"),
        is_active=True,
        content_hash="hash_p2",
        embedding=[0.02] * 384,
    )
    db_session.add_all([p1, p2])
    await db_session.commit()

    # GET /products
    res = await client.get("/products")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2
    assert "categories" in data

    # Search query
    search_res = await client.get("/products", params={"q": "Saree"})
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert any(item["sku"] == "TEST-SKU-001" for item in search_data["items"])

    # Category filter
    cat_res = await client.get("/products", params={"category": "Electronics"})
    assert cat_res.status_code == 200
    assert all(item["category"] == "Electronics" for item in cat_res.json()["items"])

    # Detail by SKU
    det_res = await client.get("/products/TEST-SKU-001")
    assert det_res.status_code == 200
    assert det_res.json()["name_en"] == "Kanchipuram Silk Saree"
    assert Decimal(str(det_res.json()["price"])) == Decimal("4999.00")

    # SVG Image endpoint
    svg_res = await client.get(f"/products/{p1.id}/image.svg")
    assert svg_res.status_code == 200
    assert "image/svg+xml" in svg_res.headers.get("content-type", "")
    assert "<svg" in svg_res.text

    # Related products
    rel_res = await client.get(f"/products/{p1.id}/related")
    assert rel_res.status_code == 200


@pytest.mark.asyncio
async def test_cart_and_checkout_e2e(client: AsyncClient, db_session: AsyncSession):
    # Create customer & product
    customer = Customer(
        email="shopper@example.com",
        password_hash=hash_password("ShopperPass123!"),
        name="Happy Shopper",
        phone="+919876543299",
        preferred_language="en",
        is_active=True,
    )
    product = Product(
        sku="TEST-BUY-01",
        name_en="Handcrafted Terracotta Pot",
        name_ta="மண்பானை",
        category="Home & Living",
        description_en="Eco-friendly clay pot",
        description_ta="மண்பானை விவரம்",
        price=Decimal("450.00"),
        stock_qty=5,
        rating=Decimal("4.6"),
        is_active=True,
        content_hash="hash_pot",
        embedding=[0.05] * 384,
    )
    db_session.add_all([customer, product])
    await db_session.commit()

    csrf_headers = {"X-Requested-With": "shop-web"}

    # Login
    login_res = await client.post(
        "/auth/login",
        json={"email": "shopper@example.com", "password": "ShopperPass123!"},
        headers=csrf_headers,
    )
    assert login_res.status_code == 200

    # GET empty cart
    cart_empty = await client.get("/cart")
    assert cart_empty.status_code == 200
    assert cart_empty.json()["total_items"] == 0

    # Add 2 items to cart
    add_res = await client.post(
        "/cart/items",
        json={"product_id": str(product.id), "quantity": 2},
        headers=csrf_headers,
    )
    assert add_res.status_code == 200
    cart_data = add_res.json()
    assert cart_data["total_items"] == 2
    assert Decimal(str(cart_data["total"])) == Decimal("900.00")

    # Checkout
    checkout_payload = {
        "shipping_address": {
            "name": "Happy Shopper",
            "phone": "+919876543299",
            "line1": "123 Anna Salai",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "pincode": "600002",
        },
        "payment_method": "demo_card",
        "demo_payment_result": "success",
    }
    order_res = await client.post(
        "/checkout",
        json=checkout_payload,
        headers={**csrf_headers, "Idempotency-Key": "test-key-1001"},
    )
    assert order_res.status_code == 200
    order_data = order_res.json()
    order_number = order_data["order_number"]
    assert order_data["status"] == "placed"
    assert Decimal(str(order_data["total_amount"])) == Decimal("900.00")
    assert order_data["payment_status"] == "paid"

    # Verify stock decremented: 5 - 2 = 3
    check_p1 = await client.get(f"/products/{product.id}")
    assert check_p1.status_code == 200
    assert check_p1.json()["stock_qty"] == 3

    # Cart should now be empty
    cart_after = await client.get("/cart")
    assert cart_after.status_code == 200
    assert cart_after.json()["total_items"] == 0

    # Test Idempotency: replaying same checkout with same Idempotency-Key returns existing order
    idem_res = await client.post(
        "/checkout",
        json=checkout_payload,
        headers={**csrf_headers, "Idempotency-Key": "test-key-1001"},
    )
    assert idem_res.status_code == 200
    assert idem_res.json()["order_number"] == order_number

    # GET /me/orders
    orders_list = await client.get("/me/orders")
    assert orders_list.status_code == 200
    assert any(o["order_number"] == order_number for o in orders_list.json())

    # GET /me/orders/{order_number}
    detail_res = await client.get(f"/me/orders/{order_number}")
    assert detail_res.status_code == 200
    assert detail_res.json()["order_number"] == order_number

    # Cancel order
    cancel_res = await client.post(
        f"/me/orders/{order_number}/cancel",
        json={"reason": "Found alternative"},
        headers=csrf_headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Verify stock restored: 3 + 2 = 5
    check_p2 = await client.get(f"/products/{product.id}")
    assert check_p2.status_code == 200
    assert check_p2.json()["stock_qty"] == 5


@pytest.mark.asyncio
async def test_anonymous_chat_and_login_action(client: AsyncClient, db_session: AsyncSession, fake_groq):
    # Enqueue router to classify as order_status
    fake_groq.enqueue_router(
        '{"intent": "order_status", "language": "en", "order_number": null, "refund_reason": null}'
    )

    # Anonymous visitor asks for order status
    chat_res = await client.post(
        "/chat",
        json={"message": "Where is my order?"},
        headers={"X-Requested-With": "support-widget"},
    )
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert "support_anon" in client.cookies
    # Should return login prompt and action
    assert any(act.get("type") == "open_login" for act in data.get("actions", []))
    assert "sign in" in data["reply"].lower() or "உள்நுழையவும்" in data["reply"]
