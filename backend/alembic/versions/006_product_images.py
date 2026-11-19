"""Phase 6 Name-Driven Product Image Pipeline: plans and verified images

Revision ID: 006_product_images
Revises: 005_whatsapp_openwa
Create Date: 2026-11-18 13:30:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "006_product_images"
down_revision: str | None = "005_whatsapp_openwa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. product_image_plans
    op.create_table(
        "product_image_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
            index=True,
        ),
        sa.Column("item", sa.String(255), nullable=True, index=True),
        sa.Column("queries", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("must_show", sa.Text(), nullable=True),
        sa.Column("must_not_show", sa.Text(), nullable=True),
        sa.Column("people_ok", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'planned'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 2. product_images
    op.create_table(
        "product_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
            index=True,
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_photo_id", sa.String(100), nullable=True),
        sa.Column("source_page_url", sa.Text(), nullable=True),
        sa.Column("photographer", sa.String(255), nullable=True),
        sa.Column("photographer_url", sa.Text(), nullable=True),
        sa.Column("licence", sa.Text(), nullable=True),
        sa.Column("credit_text", sa.Text(), nullable=True),
        sa.Column("image_url_large", sa.Text(), nullable=True),
        sa.Column("image_url_thumb", sa.Text(), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("phash", sa.String(64), nullable=True, index=True),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'missing'"),
            index=True,
        ),
        sa.Column("score", sa.Numeric(4, 3), nullable=True),
        sa.Column("verdict", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("product_images")
    op.drop_table("product_image_plans")
