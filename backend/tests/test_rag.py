import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, PolicyChunk, Product
from app.schemas import ChatResponse
from app.services.embeddings import FakeEmbedder
from app.services.llm import LLMResponse
from app.services.pipeline import handle_message
from app.services.rag import retrieve_policy_context, retrieve_product_context


@pytest.mark.asyncio
async def test_policy_retrieval_happy_path(db_session: AsyncSession):
    embedder = FakeEmbedder()
    chunk_emb = await embedder.embed_query("7-day return window cancellation refund")

    chunk = PolicyChunk(
        id=uuid.uuid4(),
        source_file="test_policy.md",
        section_title="Returns and refund window",
        language="en",
        chunk_index=0,
        content="## Returns and refund window\nWe offer a 7-day return window from the date of delivery.",
        content_hash="h1",
        embedding=chunk_emb,
    )
    db_session.add(chunk)
    await db_session.commit()

    with patch("app.services.rag.get_embedder", return_value=embedder):
        context, sources, trace = await retrieve_policy_context(
            session=db_session,
            query="return window cancellation",
            language="en",
            min_score=0.1,  # FakeEmbedder has lower raw dot products
        )

    assert context["status"] == "policy_found"
    assert len(sources) >= 1
    assert sources[0].type == "policy"
    assert sources[0].title == "Returns and refund window"
    assert trace["selected_count"] >= 1


@pytest.mark.asyncio
async def test_policy_retrieval_below_threshold(db_session: AsyncSession):
    embedder = FakeEmbedder()
    # High min_score threshold that won't be met
    with patch("app.services.rag.get_embedder", return_value=embedder):
        context, sources, trace = await retrieve_policy_context(
            session=db_session,
            query="completely unrelated query about astronomy stars galaxies",
            language="en",
            min_score=0.99,
        )

    assert context["status"] == "no_relevant_policy"
    assert len(sources) == 0
    assert trace["selected_count"] == 0


@pytest.mark.asyncio
async def test_product_search_filter_relaxation(db_session: AsyncSession):
    embedder = FakeEmbedder()
    emb = await embedder.embed_query("silk saree traditional clothing")

    p = Product(
        id=uuid.uuid4(),
        sku="TEST-SAREE-RELAX",
        name_en="Traditional Kanchipuram Silk Saree",
        name_ta="காஞ்சிபுரம் பட்டு",
        category="Traditional & Ethnic Wear",
        description_en="Pure silk saree for weddings",
        description_ta="பட்டு புடவை",
        price=Decimal("4500.00"),
        stock_qty=10,
        content_hash="h_relax",
        embedding=emb,
    )
    db_session.add(p)
    await db_session.commit()

    with patch("app.services.rag.get_embedder", return_value=embedder):
        # Strict search with impossible max_price (e.g. 1000)
        context, sources, trace = await retrieve_product_context(
            session=db_session,
            search_query="silk saree",
            category="Traditional & Ethnic Wear",
            max_price=Decimal("1000.00"),  # saree is 4500, so strict filter gives 0
            min_score=0.1,
        )

    # Should relax filter and find the saree
    assert trace["filters_relaxed"] is True
    assert context["status"] == "products_found"
    assert any(prod["sku"] == "TEST-SAREE-RELAX" for prod in context["products"])
    assert len(sources) >= 1
    assert sources[0].type == "product"


@pytest.mark.asyncio
async def test_pipeline_rag_and_sources_in_response(db_session: AsyncSession):
    # Customer
    customer = Customer(
        id=uuid.uuid4(),
        name="Test RAG Customer",
        phone="+919999988888",
        preferred_language="en",
    )
    db_session.add(customer)

    # Product
    embedder = FakeEmbedder()
    emb = await embedder.embed_query("cotton kurti ethnic wear")
    prod = Product(
        id=uuid.uuid4(),
        sku="TEST-PIPELINE-KURTI",
        name_en="Cotton Embroidered Kurti",
        name_ta="குர்தி",
        category="Traditional & Ethnic Wear",
        description_en="Beautiful cotton kurti",
        description_ta="குர்தி விவரம்",
        price=Decimal("1499.00"),
        stock_qty=5,
        content_hash="h_pipe",
        embedding=emb,
    )
    db_session.add(prod)
    await db_session.commit()

    mock_llm = AsyncMock()
    # 1. Router LLM response
    router_resp = LLMResponse(
        content='{"intent": "product_question", "language": "en", "search_query": "cotton kurti", "category": "Traditional & Ethnic Wear", "max_price_inr": null, "order_number": null, "refund_reason": null}',
        model="llama-3.1-8b-instant",
        prompt_tokens=100,
        completion_tokens=25,
        cost_inr=Decimal("0.005"),
        latency_ms=120,
    )
    # 2. Generator LLM response
    gen_resp = LLMResponse(
        content="We have the Cotton Embroidered Kurti available for ₹1,499 in stock.",
        model="llama-3.3-70b-versatile",
        prompt_tokens=250,
        completion_tokens=30,
        cost_inr=Decimal("0.025"),
        latency_ms=250,
    )
    mock_llm.chat_completion.side_effect = [router_resp, gen_resp]

    from app.config import get_settings

    test_settings = get_settings().model_copy(update={"RAG_MIN_SCORE": 0.1})

    with patch("app.services.rag.get_embedder", return_value=embedder):
        response: ChatResponse = await handle_message(
            session=db_session,
            customer_id=customer.id,
            session_id=None,
            text="Do you have any cotton kurti available?",
            llm_client=mock_llm,
            settings=test_settings,
        )

    assert response.intent == "product_question"
    assert len(response.sources) >= 1
    assert response.sources[0].type == "product"
    assert response.sources[0].title == "Cotton Embroidered Kurti"


@pytest.mark.asyncio
async def test_rag_fallback_on_embedder_failure(db_session: AsyncSession):
    with patch("app.services.rag.get_embedder", side_effect=RuntimeError("Embedding service offline")):
        context, sources, trace = await retrieve_policy_context(
            session=db_session,
            query="return policy",
            language="en",
        )

    assert context["status"] == "retrieval_error"
    assert len(sources) == 0
    assert "error" in trace
