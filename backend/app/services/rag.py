import logging
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.schemas import SourceItem
from app.services.embeddings import get_embedder
from app.services.vectorstore import Hit, get_vector_store

logger = logging.getLogger("app.services.rag")


async def retrieve_policy_context(
    session: AsyncSession,
    query: str,
    language: str,
    top_k: int | None = None,
    min_score: float | None = None,
) -> tuple[dict[str, Any], list[SourceItem], dict[str, Any]]:
    """
    Retrieves grounded policy chunks for a policy inquiry.
    Returns (llm_context, sources, trace_entry).
    """
    settings = get_settings()
    top_k = top_k or settings.RAG_TOP_K
    min_score = min_score if min_score is not None else settings.RAG_MIN_SCORE

    trace_entry: dict[str, Any] = {
        "tool": "policy_retrieval",
        "query": query,
        "language": language,
        "hits": [],
        "selected_count": 0,
    }

    try:
        embedder = get_embedder()
        query_embedding = await embedder.embed_query(query)
        store = get_vector_store()

        # Search policy chunks (cross-lingual embedding matches across en & ta)
        hits: list[Hit] = await store.search(
            session=session,
            table="policy_chunks",
            query_embedding=query_embedding,
            top_k=top_k * 2,  # fetch slight over-sample to filter
        )

        # Record all candidate hits in trace
        trace_entry["hits"] = [
            {"id": str(h.id), "title": h.payload.get("section_title"), "score": round(h.score, 4)}
            for h in hits
        ]

        # Filter by calibrated minimum similarity score
        valid_hits = [h for h in hits if h.score >= min_score][:top_k]
        trace_entry["selected_count"] = len(valid_hits)

        if not valid_hits:
            logger.info("Policy query '%s' had no chunks scoring >= %s", query, min_score)
            return (
                {"status": "no_relevant_policy", "query": query, "message": "No relevant policy found."},
                [],
                trace_entry,
            )

        sources = [
            SourceItem(
                type="policy",
                id=str(h.id),
                title=h.payload.get("section_title", "Policy Section"),
            )
            for h in valid_hits
        ]

        llm_context = {
            "status": "policy_found",
            "query": query,
            "policy_sections": [
                {
                    "title": h.payload.get("section_title"),
                    "content": h.payload.get("content"),
                    "language": h.payload.get("language"),
                    "score": round(h.score, 4),
                }
                for h in valid_hits
            ],
        }

        return llm_context, sources, trace_entry

    except Exception as e:
        logger.exception("Error during policy retrieval for query '%s': %s", query, e)
        trace_entry["error"] = str(e)
        return (
            {"status": "retrieval_error", "query": query, "error": str(e)},
            [],
            trace_entry,
        )


async def retrieve_product_context(
    session: AsyncSession,
    search_query: str,
    category: str | None = None,
    max_price: Decimal | None = None,
    in_stock_only: bool = False,
    top_k: int | None = None,
    min_score: float | None = None,
) -> tuple[dict[str, Any], list[SourceItem], dict[str, Any]]:
    """
    Retrieves grounded products matching semantic query, category, and price criteria.
    Supports filter relaxation if strict filters return zero matches.
    Returns (llm_context, sources, trace_entry).
    """
    settings = get_settings()
    top_k = top_k or settings.RAG_TOP_K
    min_score = min_score if min_score is not None else settings.RAG_MIN_SCORE
    candidates_count = settings.PRODUCT_SEARCH_CANDIDATES

    initial_filters: dict[str, Any] = {}
    if category:
        initial_filters["category"] = category
    if max_price is not None:
        initial_filters["max_price"] = max_price
    if in_stock_only:
        initial_filters["in_stock_only"] = True

    trace_entry: dict[str, Any] = {
        "tool": "product_search",
        "search_query": search_query,
        "filters": {k: str(v) for k, v in initial_filters.items()},
        "filters_relaxed": False,
        "hits": [],
        "selected_count": 0,
    }

    try:
        embedder = get_embedder()
        query_embedding = await embedder.embed_query(search_query)
        store = get_vector_store()

        hits: list[Hit] = await store.search(
            session=session,
            table="products",
            query_embedding=query_embedding,
            top_k=candidates_count,
            filters=initial_filters,
        )

        filters_relaxed = False
        # If strict filtering returned no results and filters were applied, relax filters
        if not hits and (category or max_price is not None):
            logger.info(
                "Product search '%s' yielded 0 hits with filters %s. Relaxing filters...",
                search_query,
                initial_filters,
            )
            filters_relaxed = True
            hits = await store.search(
                session=session,
                table="products",
                query_embedding=query_embedding,
                top_k=candidates_count,
                filters={"in_stock_only": in_stock_only} if in_stock_only else None,
            )

        trace_entry["filters_relaxed"] = filters_relaxed
        trace_entry["hits"] = [
            {
                "id": str(h.id),
                "sku": h.payload.get("sku"),
                "name": h.payload.get("name_en"),
                "score": round(h.score, 4),
            }
            for h in hits
        ]

        valid_hits = [h for h in hits if h.score >= min_score][:top_k]
        trace_entry["selected_count"] = len(valid_hits)

        if not valid_hits:
            logger.info("Product search '%s' had no items scoring >= %s", search_query, min_score)
            return (
                {"status": "no_matching_products", "query": search_query, "filters_relaxed": filters_relaxed},
                [],
                trace_entry,
            )

        sources = [
            SourceItem(
                type="product",
                id=str(h.id),
                title=h.payload.get("name_en", "Product"),
            )
            for h in valid_hits
        ]

        llm_context = {
            "status": "products_found",
            "search_query": search_query,
            "filters_relaxed": filters_relaxed,
            "products": [
                {
                    "sku": h.payload.get("sku"),
                    "name_en": h.payload.get("name_en"),
                    "name_ta": h.payload.get("name_ta"),
                    "category": h.payload.get("category"),
                    "price_inr": h.payload.get("price"),
                    "stock_qty": h.payload.get("stock_qty"),
                    "score": round(h.score, 4),
                }
                for h in valid_hits
            ],
        }

        return llm_context, sources, trace_entry

    except Exception as e:
        logger.exception("Error during product retrieval for query '%s': %s", search_query, e)
        trace_entry["error"] = str(e)
        return (
            {"status": "retrieval_error", "query": search_query, "error": str(e)},
            [],
            trace_entry,
        )
