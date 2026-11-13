import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product
from app.services.embeddings import FakeEmbedder
from app.services.vectorstore import NumpyStore


@pytest.mark.asyncio
async def test_numpystore_product_search_and_filters(db_session: AsyncSession):
    embedder = FakeEmbedder(dimension=384)
    store = NumpyStore()

    emb1 = await embedder.embed_query("cotton kurti ethnic wear dress")
    emb2 = await embedder.embed_query("wireless headphones noise cancelling audio")
    emb3 = await embedder.embed_query("cotton saree ethnic silk traditional")

    p1 = Product(
        id=uuid.uuid4(),
        sku="TEST-KURTI-01",
        name_en="Cotton Kurti Blue",
        name_ta="பருத்தி குர்தி",
        category="Traditional & Ethnic Wear",
        description_en="Pure cotton ethnic dress",
        description_ta="பருத்தி ஆடை",
        price=Decimal("1200.00"),
        stock_qty=10,
        content_hash="hash1",
        embedding=emb1,
    )
    p2 = Product(
        id=uuid.uuid4(),
        sku="TEST-HEADPHONES-01",
        name_en="Wireless ANC Headphones",
        name_ta="ஹெட்போன்",
        category="Electronics & Audio",
        description_en="High fidelity audio headphones",
        description_ta="ஹெட்போன் விவரம்",
        price=Decimal("3500.00"),
        stock_qty=0,  # out of stock
        content_hash="hash2",
        embedding=emb2,
    )
    p3 = Product(
        id=uuid.uuid4(),
        sku="TEST-SAREE-01",
        name_en="Silk Saree Red",
        name_ta="பட்டு புடவை",
        category="Traditional & Ethnic Wear",
        description_en="Traditional silk saree",
        description_ta="பாரம்பரிய பட்டு புடவை",
        price=Decimal("2500.00"),
        stock_qty=5,
        content_hash="hash3",
        embedding=emb3,
    )

    db_session.add_all([p1, p2, p3])
    await db_session.commit()

    # 1. Search for kurti
    q_emb = await embedder.embed_query("kurti")
    hits = await store.search(db_session, "products", q_emb, top_k=2)
    assert len(hits) >= 1
    assert hits[0].payload["sku"] == "TEST-KURTI-01"
    assert isinstance(hits[0].score, float)

    # 2. Filter by max_price (e.g. <= 1500)
    hits_price = await store.search(
        db_session, "products", q_emb, top_k=5, filters={"max_price": Decimal("1500.00")}
    )
    assert all(Decimal(h.payload["price"]) <= Decimal("1500.00") for h in hits_price)
    assert any(h.payload["sku"] == "TEST-KURTI-01" for h in hits_price)
    assert not any(h.payload["sku"] == "TEST-SAREE-01" for h in hits_price)

    # 3. Filter by in_stock_only
    q_audio = await embedder.embed_query("headphones audio")
    hits_stock = await store.search(db_session, "products", q_audio, top_k=5, filters={"in_stock_only": True})
    # The out of stock headphones should NOT be returned
    assert not any(h.payload["sku"] == "TEST-HEADPHONES-01" for h in hits_stock)
