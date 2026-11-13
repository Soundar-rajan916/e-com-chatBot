from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import PolicyChunk, Product


@dataclass
class Hit:
    id: UUID
    score: float
    payload: dict[str, Any]


class VectorStore(ABC):
    """Abstract VectorStore interface for semantic similarity search."""

    @abstractmethod
    async def search(
        self,
        session: AsyncSession,
        table: str,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[Hit]:
        """Search top_k nearest documents by cosine similarity."""
        raise NotImplementedError


class PgVectorStore(VectorStore):
    """pgvector implementation executing cosine distance queries via SQL."""

    async def search(
        self,
        session: AsyncSession,
        table: str,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[Hit]:
        filters = filters or {}

        if table == "products":
            # 1 - cosine_distance gives cosine similarity
            similarity_expr = (1 - Product.embedding.cosine_distance(query_embedding)).label("score")
            stmt = select(Product, similarity_expr)

            if filters.get("category"):
                stmt = stmt.where(Product.category.ilike(f"%{filters['category']}%"))
            if filters.get("max_price") is not None:
                max_price = Decimal(str(filters["max_price"]))
                stmt = stmt.where(Product.price <= max_price)
            if filters.get("in_stock_only"):
                stmt = stmt.where(Product.stock_qty > 0)

            stmt = stmt.order_by(similarity_expr.desc()).limit(top_k)
            result = await session.execute(stmt)
            rows = result.all()

            hits: list[Hit] = []
            for prod, score in rows:
                hits.append(
                    Hit(
                        id=prod.id,
                        score=float(score),
                        payload={
                            "sku": prod.sku,
                            "name_en": prod.name_en,
                            "name_ta": prod.name_ta,
                            "category": prod.category,
                            "subcategory": prod.subcategory,
                            "description_en": prod.description_en,
                            "description_ta": prod.description_ta,
                            "price": str(prod.price),
                            "stock_qty": prod.stock_qty,
                            "rating": str(prod.rating) if prod.rating is not None else None,
                        },
                    )
                )
            return hits

        elif table == "policy_chunks":
            similarity_expr = (1 - PolicyChunk.embedding.cosine_distance(query_embedding)).label("score")
            stmt = select(PolicyChunk, similarity_expr)

            if filters.get("language"):
                stmt = stmt.where(PolicyChunk.language == filters["language"])

            stmt = stmt.order_by(similarity_expr.desc()).limit(top_k)
            result = await session.execute(stmt)
            rows = result.all()

            hits = []
            for chunk, score in rows:
                hits.append(
                    Hit(
                        id=chunk.id,
                        score=float(score),
                        payload={
                            "source_file": chunk.source_file,
                            "section_title": chunk.section_title,
                            "language": chunk.language,
                            "chunk_index": chunk.chunk_index,
                            "content": chunk.content,
                        },
                    )
                )
            return hits

        else:
            raise ValueError(f"Unknown table for vector search: {table}")


class NumpyStore(VectorStore):
    """In-memory numpy implementation computing exact cosine similarity."""

    async def search(
        self,
        session: AsyncSession,
        table: str,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[Hit]:
        filters = filters or {}
        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            q_norm = 1.0

        if table == "products":
            stmt = select(Product)
            if filters.get("category"):
                stmt = stmt.where(Product.category.ilike(f"%{filters['category']}%"))
            if filters.get("max_price") is not None:
                max_price = Decimal(str(filters["max_price"]))
                stmt = stmt.where(Product.price <= max_price)
            if filters.get("in_stock_only"):
                stmt = stmt.where(Product.stock_qty > 0)

            result = await session.execute(stmt)
            products = list(result.scalars().all())
            if not products:
                return []

            embeddings = np.array([p.embedding for p in products], dtype=np.float32)
            dots = np.dot(embeddings, q_vec)
            norms = np.linalg.norm(embeddings, axis=1) * q_norm
            # Avoid division by zero
            norms[norms == 0] = 1e-9
            scores = dots / norms

            # Sort descending
            ranked_indices = np.argsort(-scores)[:top_k]

            hits: list[Hit] = []
            for idx in ranked_indices:
                prod = products[idx]
                hits.append(
                    Hit(
                        id=prod.id,
                        score=float(scores[idx]),
                        payload={
                            "sku": prod.sku,
                            "name_en": prod.name_en,
                            "name_ta": prod.name_ta,
                            "category": prod.category,
                            "subcategory": prod.subcategory,
                            "description_en": prod.description_en,
                            "description_ta": prod.description_ta,
                            "price": str(prod.price),
                            "stock_qty": prod.stock_qty,
                            "rating": str(prod.rating) if prod.rating is not None else None,
                        },
                    )
                )
            return hits

        elif table == "policy_chunks":
            stmt = select(PolicyChunk)
            if filters.get("language"):
                stmt = stmt.where(PolicyChunk.language == filters["language"])

            result = await session.execute(stmt)
            chunks = list(result.scalars().all())
            if not chunks:
                return []

            embeddings = np.array([c.embedding for c in chunks], dtype=np.float32)
            dots = np.dot(embeddings, q_vec)
            norms = np.linalg.norm(embeddings, axis=1) * q_norm
            norms[norms == 0] = 1e-9
            scores = dots / norms

            ranked_indices = np.argsort(-scores)[:top_k]

            hits = []
            for idx in ranked_indices:
                chunk = chunks[idx]
                hits.append(
                    Hit(
                        id=chunk.id,
                        score=float(scores[idx]),
                        payload={
                            "source_file": chunk.source_file,
                            "section_title": chunk.section_title,
                            "language": chunk.language,
                            "chunk_index": chunk.chunk_index,
                            "content": chunk.content,
                        },
                    )
                )
            return hits

        else:
            raise ValueError(f"Unknown table for vector search: {table}")


def get_vector_store(backend: str | None = None) -> VectorStore:
    """Factory to instantiate the appropriate vector store."""
    choice = (backend or get_settings().VECTOR_BACKEND).lower()
    if choice == "pgvector":
        return PgVectorStore()
    return NumpyStore()
