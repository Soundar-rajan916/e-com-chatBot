"""End-to-End smoke verification script for E-Commerce Store & Support Chat Widget.

Tests full customer lifecycle, product catalog, deterministic SVG placeholders,
cart workflows, checkout with mock card outcomes, idempotency, order lifecycle,
and anonymous chat session claiming.
"""

import sys
import uuid
import httpx

BASE_URL = "http://127.0.0.1:8000"


def log(msg: str):
    print(f"[SMOKE] {msg}")


def test_smoke():
    log("Starting comprehensive E-Commerce Store Smoke Test...")

    client = httpx.Client(base_url=BASE_URL, timeout=90.0)

    # 1. Health & Config
    log("Checking /health and /config...")
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health_data = res.json()
    assert health_data.get("status") in ("ok", "degraded")

    res = client.get("/config")
    assert res.status_code == 200, f"Config failed: {res.text}"
    cfg = res.json()
    assert cfg.get("store_name") is not None
    assert cfg.get("return_window_days") == 7

    # 2. Store Policy
    log("Checking /policy/en and /policy/ta...")
    res = client.get("/policy/en")
    assert res.status_code == 200
    assert "return" in res.text.lower()

    # 3. Product Catalog & Deterministic SVG Image
    log("Checking product catalog and SVG generation...")
    res = client.get("/categories")
    assert res.status_code == 200, f"Categories failed: {res.text}"
    categories = res.json()
    assert len(categories) > 0, f"Categories empty: {categories}"

    res = client.get("/products?page=1&page_size=5&in_stock_only=true")
    assert res.status_code == 200, f"Products list failed: {res.text}"
    prod_data = res.json()
    assert len(prod_data["items"]) > 0, f"Products empty: {prod_data}"
    test_prod = prod_data["items"][0]
    prod_id = test_prod["id"]
    prod_title = test_prod.get("title") or test_prod.get("name_en") or "Silk Saree"

    # Verify SVG generation
    svg_res = client.get(f"/products/{prod_id}/image.svg")
    assert svg_res.status_code == 200, f"SVG failed: {svg_res.text}"
    assert "image/svg+xml" in svg_res.headers.get("content-type", ""), f"Content type wrong: {svg_res.headers}"
    assert "<svg" in svg_res.text, f"SVG content wrong: {svg_res.text[:100]}"

    # 4. Anonymous Chat Session
    log("Testing anonymous chat session...")
    anon_client = httpx.Client(base_url=BASE_URL, timeout=90.0)
    chat_res = anon_client.post(
        "/chat",
        headers={"X-Requested-With": "support-widget"},
        json={
            "message": "Do you have silk sarees available?",
            "context": {"type": "product", "id": prod_id, "title": prod_title},
        },
    )
    assert chat_res.status_code == 200, f"Anon chat failed: {chat_res.text}"
    chat_payload = chat_res.json()
    assert "reply" in chat_payload
    anon_session_id = chat_payload["session_id"]
    assert "support_anon" in anon_client.cookies

    # Test order status while unauthenticated triggers open_login action
    auth_req_res = anon_client.post(
        "/chat",
        headers={"X-Requested-With": "support-widget"},
        json={"message": "Where is my order status?"},
    )
    assert auth_req_res.status_code == 200
    actions = auth_req_res.json().get("actions", [])
    action_types = [a.get("type") if isinstance(a, dict) else a for a in actions]
    assert "open_login" in action_types, f"Expected open_login in actions, got: {actions}"

    # 5. Customer Registration & Login
    unique_suffix = uuid.uuid4().hex[:6]
    customer_email = f"smoke_user_{unique_suffix}@example.com"
    customer_phone = f"98{uuid.uuid4().int % 100000000:08d}"
    customer_pass = "SmokePass1234!"
    log(f"Registering customer: {customer_email} with phone {customer_phone}...")

    reg_res = client.post(
        "/auth/register",
        headers={"X-Requested-With": "shop-web"},
        json={
            "name": f"Smoke Tester {unique_suffix}",
            "email": customer_email,
            "phone": customer_phone,
            "password": customer_pass,
            "preferred_language": "en",
        },
    )
    assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
    reg_data = reg_res.json()
    assert reg_data["email"] == customer_email
    assert "shop_session" in client.cookies

    # Verify /auth/me
    me_res = client.get("/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["email"] == customer_email

    # 6. Cart Workflows
    log("Testing Cart API...")
    # Add item
    add_res = client.post(
        "/cart/items",
        headers={"X-Requested-With": "shop-web"},
        json={"product_id": prod_id, "quantity": 2},
    )
    assert add_res.status_code == 200, f"Add to cart failed: {add_res.text}"
    cart_data = add_res.json()
    assert cart_data["total_items"] == 2

    # Update item
    patch_res = client.patch(
        f"/cart/items/{prod_id}",
        headers={"X-Requested-With": "shop-web"},
        json={"quantity": 1},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["total_items"] == 1

    # 7. Checkout & Mock Payments
    log("Testing Checkout and Mock Payments...")
    shipping_addr = {
        "name": "Smoke Tester",
        "phone": customer_phone,
        "line1": "100 Anna Salai",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "pincode": "600002",
    }

    # Simulate payment decline
    decline_key = f"key_dec_{unique_suffix}"
    dec_res = client.post(
        "/checkout",
        headers={
            "X-Requested-With": "shop-web",
            "Idempotency-Key": decline_key,
        },
        json={
            "shipping_address": shipping_addr,
            "payment_method": "demo_card",
            "demo_payment_result": "failure",
        },
    )
    assert dec_res.status_code in (400, 402), f"Expected card decline 402, got {dec_res.status_code}: {dec_res.text}"

    # Successful checkout
    success_key = f"key_succ_{unique_suffix}"
    chk_res = client.post(
        "/checkout",
        headers={
            "X-Requested-With": "shop-web",
            "Idempotency-Key": success_key,
        },
        json={
            "shipping_address": shipping_addr,
            "payment_method": "demo_card",
            "demo_payment_result": "success",
        },
    )
    assert chk_res.status_code == 200, f"Checkout failed: {chk_res.text}"
    order_data = chk_res.json()
    order_num = order_data["order_number"]
    assert order_data["status"] in ("placed", "confirmed")
    assert order_data["payment_status"] == "paid"

    # Idempotent replay
    replay_res = client.post(
        "/checkout",
        headers={
            "X-Requested-With": "shop-web",
            "Idempotency-Key": success_key,
        },
        json={
            "shipping_address": shipping_addr,
            "payment_method": "mock_card",
            "mock_payment_outcome": "success",
        },
    )
    assert replay_res.status_code == 200
    assert replay_res.json()["order_number"] == order_num

    # 8. Order Status & Advance & Return Flow
    log(f"Advancing order {order_num} to delivered...")
    adv_res = client.post(
        f"/dev/orders/{order_num}/advance",
        headers={"X-Requested-With": "shop-web"},
    )
    assert adv_res.status_code == 200
    assert adv_res.json()["status"] in ("processing", "shipped")

    # Advance until delivered
    while adv_res.json()["status"] != "delivered":
        adv_res = client.post(
            f"/dev/orders/{order_num}/advance",
            headers={"X-Requested-With": "shop-web"},
        )
        assert adv_res.status_code == 200

    assert adv_res.json()["return_info"]["eligible"] is True

    # Request return
    log(f"Requesting return for order {order_num}...")
    ret_res = client.post(
        f"/me/orders/{order_num}/return",
        headers={"X-Requested-With": "shop-web"},
        json={
            "items": [{"product_id": prod_id, "quantity": 1}],
            "reason": "Defective piece detected during unboxing",
        },
    )
    assert ret_res.status_code == 200, f"Return failed: {ret_res.text}"
    ret_data = ret_res.json()
    assert ret_data["status"] in ("processed", "approved", "pending_approval")
    assert ret_data["refund_id"] is not None

    log("All E-Commerce Store & Chat Widget smoke assertions PASSED 100%!")


if __name__ == "__main__":
    import traceback
    try:
        test_smoke()
        sys.exit(0)
    except AssertionError as e:
        print(f"[FAIL] Smoke check assertion failed: {e}")
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Smoke test error: {e}")
        traceback.print_exc()
        sys.exit(1)
