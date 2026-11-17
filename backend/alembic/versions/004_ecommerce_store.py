"""Phase 4 E-Commerce Storefront: customer auth, carts, orders enhancement, and idempotency

Revision ID: 004_ecommerce_store
Revises: 003_phase3
Create Date: 2026-11-13 14:00:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004_ecommerce_store"
down_revision: str | None = "003_phase3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update customers table
    op.add_column("customers", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("customers", sa.Column("password_hash", sa.Text(), nullable=True))
    op.add_column(
        "customers",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "customers",
        sa.Column("failed_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column("customers", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("customers", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_customers_email", "customers", ["email"], unique=True)

    # 2. Customer sessions table
    op.create_table(
        "customer_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )
    op.create_index("ix_customer_sessions_customer_id", "customer_sessions", ["customer_id"])
    op.create_index("ix_customer_sessions_token_hash", "customer_sessions", ["token_hash"], unique=True)

    # 3. Product is_active flag
    op.add_column(
        "products",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )

    # 4. Carts table
    op.create_table(
        "carts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_carts_customer_id", "carts", ["customer_id"], unique=True)

    # 5. Cart items table
    op.create_table(
        "cart_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "cart_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("carts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), server_default=sa.text("1"), nullable=False),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("cart_id", "product_id", name="uq_cart_item_cart_product"),
    )
    op.create_index("ix_cart_items_cart_id", "cart_items", ["cart_id"])
    op.create_index("ix_cart_items_product_id", "cart_items", ["product_id"])

    # 6. Orders enhancements
    op.add_column("orders", sa.Column("shipping_name", sa.String(255), nullable=True))
    op.add_column("orders", sa.Column("shipping_phone", sa.String(50), nullable=True))
    op.add_column("orders", sa.Column("shipping_line1", sa.String(255), nullable=True))
    op.add_column("orders", sa.Column("shipping_line2", sa.String(255), nullable=True))
    op.add_column("orders", sa.Column("shipping_city", sa.String(100), nullable=True))
    op.add_column("orders", sa.Column("shipping_state", sa.String(100), nullable=True))
    op.add_column("orders", sa.Column("shipping_pincode", sa.String(20), nullable=True))
    op.add_column(
        "orders",
        sa.Column("payment_method", sa.String(50), server_default=sa.text("'cod'"), nullable=False),
    )
    op.add_column(
        "orders",
        sa.Column("payment_status", sa.String(50), server_default=sa.text("'pending'"), nullable=False),
    )
    op.add_column("orders", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("cancel_reason", sa.Text(), nullable=True))

    # 7. Order status history table
    op.create_table(
        "order_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_order_status_history_order_id", "order_status_history", ["order_id"])

    # Backfill order_status_history for existing orders
    op.execute(
        """
        INSERT INTO order_status_history (id, order_id, status, at, note)
        SELECT gen_random_uuid(), id, status, placed_at, 'Initial order status'
        FROM orders
        """
    )

    # 8. Idempotency keys table
    op.create_table(
        "idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("customer_id", "key", name="uq_idempotency_customer_key"),
    )
    op.create_index("ix_idempotency_customer_key", "idempotency_keys", ["customer_id", "key"])

    # 9. ChatSession adjustments for anonymous users
    op.alter_column("chat_sessions", "customer_id", nullable=True)
    op.add_column("chat_sessions", sa.Column("anon_token_hash", sa.String(64), nullable=True))
    op.create_index("ix_chat_sessions_anon_token_hash", "chat_sessions", ["anon_token_hash"])


def downgrade() -> None:
    # 9. Revert chat_sessions adjustments
    op.drop_index("ix_chat_sessions_anon_token_hash", table_name="chat_sessions")
    op.drop_column("chat_sessions", "anon_token_hash")
    # Note: customer_id may have nulls if anonymous sessions were created, so delete or backfill if needed
    op.execute("DELETE FROM chat_sessions WHERE customer_id IS NULL")
    op.alter_column("chat_sessions", "customer_id", nullable=False)

    # 8. Drop idempotency keys table
    op.drop_index("ix_idempotency_customer_key", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")

    # 7. Drop order status history table
    op.drop_index("ix_order_status_history_order_id", table_name="order_status_history")
    op.drop_table("order_status_history")

    # 6. Revert orders columns
    op.drop_column("orders", "cancel_reason")
    op.drop_column("orders", "cancelled_at")
    op.drop_column("orders", "payment_status")
    op.drop_column("orders", "payment_method")
    op.drop_column("orders", "shipping_pincode")
    op.drop_column("orders", "shipping_state")
    op.drop_column("orders", "shipping_city")
    op.drop_column("orders", "shipping_line2")
    op.drop_column("orders", "shipping_line1")
    op.drop_column("orders", "shipping_phone")
    op.drop_column("orders", "shipping_name")

    # 5. Drop cart items table
    op.drop_index("ix_cart_items_product_id", table_name="cart_items")
    op.drop_index("ix_cart_items_cart_id", table_name="cart_items")
    op.drop_table("cart_items")

    # 4. Drop carts table
    op.drop_index("ix_carts_customer_id", table_name="carts")
    op.drop_table("carts")

    # 3. Drop products is_active column
    op.drop_column("products", "is_active")

    # 2. Drop customer sessions table
    op.drop_index("ix_customer_sessions_token_hash", table_name="customer_sessions")
    op.drop_index("ix_customer_sessions_customer_id", table_name="customer_sessions")
    op.drop_table("customer_sessions")

    # 1. Revert customers columns
    op.drop_index("ix_customers_email", table_name="customers")
    op.drop_column("customers", "last_login_at")
    op.drop_column("customers", "locked_until")
    op.drop_column("customers", "failed_attempts")
    op.drop_column("customers", "is_active")
    op.drop_column("customers", "password_hash")
    op.drop_column("customers", "email")
