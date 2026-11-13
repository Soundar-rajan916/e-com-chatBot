"""phase 2 rag and product models

Revision ID: 002_phase2
Revises: 001_initial
Create Date: 2026-11-12 14:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.config import get_settings

revision: str = "002_phase2"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    settings = get_settings()
    vector_backend = settings.VECTOR_BACKEND.lower()
    embedding_dim = settings.EMBEDDING_DIM

    conn = op.get_bind()

    if vector_backend == "pgvector":
        # Check if extension is available
        result = conn.execute(sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")).scalar()
        if not result:
            raise RuntimeError(
                "VECTOR_BACKEND is configured as 'pgvector', but the 'vector' PostgreSQL extension is not available "
                "in this database. Install pgvector or set VECTOR_BACKEND=numpy in your .env."
            )
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        embedding_type = sa.text(f"vector({embedding_dim})")
    else:
        embedding_type = postgresql.ARRAY(sa.DOUBLE_PRECISION())

    # 1. Products Table
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_ta", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("subcategory", sa.String(length=100), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=False),
        sa.Column("description_ta", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("stock_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating", sa.Numeric(precision=2, scale=1), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", embedding_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)
    op.create_index("ix_products_category", "products", ["category"])
    op.create_index("ix_products_price", "products", ["price"])

    # 2. Policy Chunks Table
    op.create_table(
        "policy_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("section_title", sa.String(length=255), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", embedding_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("source_file", "chunk_index", name="uq_policy_chunk_source_index"),
    )

    # If pgvector, create HNSW index for cosine similarity
    if vector_backend == "pgvector":
        op.execute(
            "CREATE INDEX ix_products_embedding_hnsw ON products USING hnsw (embedding vector_cosine_ops)"
        )
        op.execute(
            "CREATE INDEX ix_policy_chunks_embedding_hnsw ON policy_chunks USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    op.drop_table("policy_chunks")
    op.drop_table("products")
