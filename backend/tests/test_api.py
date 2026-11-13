import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db import get_session
from app.main import create_app
from app.models import ChatSession, Customer


@pytest.mark.asyncio
async def test_api_message_validation_errors(client: AsyncClient, db_session: AsyncSession):
    customer = Customer(name="API User", phone="+919999999021", preferred_language="en")
    db_session.add(customer)
    await db_session.commit()

    # 1. Empty message -> 422
    resp_empty = await client.post("/chat", json={"customer_id": str(customer.id), "message": ""})
    assert resp_empty.status_code == 422

    # 2. Whitespace-only message -> 422
    resp_ws = await client.post("/chat", json={"customer_id": str(customer.id), "message": "   "})
    assert resp_ws.status_code == 422

    # 3. Too long message (> 1000 chars) -> 422
    long_msg = "A" * 1001
    resp_long = await client.post("/chat", json={"customer_id": str(customer.id), "message": long_msg})
    assert resp_long.status_code == 422


@pytest.mark.asyncio
async def test_api_wrong_customer_session_returns_403(client: AsyncClient, db_session: AsyncSession):
    c1 = Customer(name="Customer 1", phone="+919999999022", preferred_language="en")
    c2 = Customer(name="Customer 2", phone="+919999999023", preferred_language="en")
    db_session.add_all([c1, c2])
    await db_session.flush()

    session_c1 = ChatSession(customer_id=c1.id, channel="web")
    db_session.add(session_c1)
    await db_session.commit()

    # Customer 2 attempts to send message in Customer 1's session
    resp = await client.post(
        "/chat",
        json={
            "customer_id": str(c2.id),
            "session_id": str(session_c1.id),
            "message": "Hello from impostor",
        },
    )
    assert resp.status_code == 403
    assert "Session does not belong to this customer" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_api_unknown_customer_returns_404(client: AsyncClient):
    random_id = str(uuid.uuid4())
    resp = await client.post(
        "/chat",
        json={"customer_id": random_id, "message": "Hello?"},
    )
    assert resp.status_code == 404
    assert "Customer not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_customers_demo_registered_only_in_dev(test_engine, db_session: AsyncSession, monkeypatch):
    customer = Customer(name="Demo Cust", phone="+919999999024", preferred_language="en")
    db_session.add(customer)
    await db_session.commit()

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_session():
        async with session_factory() as session:
            yield session

    # 1. When APP_ENV=dev
    monkeypatch.setenv("APP_ENV", "dev")
    get_settings.cache_clear()
    dev_app = create_app()
    dev_app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=dev_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as dev_client:
        resp = await dev_client.get("/customers/demo")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["name"] == "Demo Cust"

    # 2. When APP_ENV=prod -> Route must not exist (404)
    monkeypatch.setenv("APP_ENV", "prod")
    get_settings.cache_clear()
    prod_app = create_app()
    prod_app.dependency_overrides[get_session] = override_get_session
    transport_prod = ASGITransport(app=prod_app)
    async with AsyncClient(transport=transport_prod, base_url="http://testserver") as prod_client:
        resp_prod = await prod_client.get("/customers/demo")
        assert resp_prod.status_code == 404

    # Restore settings cache
    monkeypatch.setenv("APP_ENV", "dev")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient):
    # Allowed origin: http://localhost:5173
    resp_allowed = await client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp_allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"

    # Disallowed origin
    resp_disallowed = await client.options(
        "/health",
        headers={
            "Origin": "http://evil-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp_disallowed.headers.get("access-control-allow-origin") != "http://evil-site.com"


@pytest.mark.asyncio
async def test_health_check_reports_status(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "db": "connected"}
