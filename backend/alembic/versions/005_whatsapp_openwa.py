"""Phase 5 WhatsApp Integration with OpenWA upstream gateway

Revision ID: 005_whatsapp_openwa
Revises: 004_ecommerce_store
Create Date: 2026-11-17 12:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "005_whatsapp_openwa"
down_revision: str | None = "004_ecommerce_store"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. whatsapp_contacts
    op.create_table(
        "whatsapp_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone_number", sa.String(32), nullable=False),
        sa.Column("chat_id", sa.String(128), nullable=False),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("opted_out", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_whatsapp_contacts_phone_number", "whatsapp_contacts", ["phone_number"], unique=True)
    op.create_index("ix_whatsapp_contacts_chat_id", "whatsapp_contacts", ["chat_id"], unique=True)
    op.create_index("ix_whatsapp_contacts_customer_id", "whatsapp_contacts", ["customer_id"])

    # 2. whatsapp_link_codes
    op.create_table(
        "whatsapp_link_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_whatsapp_link_codes_customer_id", "whatsapp_link_codes", ["customer_id"])
    op.create_index("ix_whatsapp_link_codes_code", "whatsapp_link_codes", ["code"])

    # 3. whatsapp_inbound_events
    op.create_table(
        "whatsapp_inbound_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("delivery_id", sa.String(128), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(128), nullable=False),
        sa.Column("sender_chat_id", sa.String(128), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_whatsapp_inbound_events_delivery_id", "whatsapp_inbound_events", ["delivery_id"], unique=True)
    op.create_index("ix_whatsapp_inbound_events_idempotency_key", "whatsapp_inbound_events", ["idempotency_key"], unique=True)
    op.create_index("ix_whatsapp_inbound_events_event_type", "whatsapp_inbound_events", ["event_type"])
    op.create_index("ix_whatsapp_inbound_events_status", "whatsapp_inbound_events", ["status"])
    op.create_index("ix_whatsapp_inbound_events_sender_chat_id", "whatsapp_inbound_events", ["sender_chat_id"])

    # 4. whatsapp_outbound
    op.create_table(
        "whatsapp_outbound",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("whatsapp_contacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chat_id", sa.String(128), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("openwa_message_id", sa.String(128), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_whatsapp_outbound_contact_id", "whatsapp_outbound", ["contact_id"])
    op.create_index("ix_whatsapp_outbound_chat_id", "whatsapp_outbound", ["chat_id"])
    op.create_index("ix_whatsapp_outbound_idempotency_key", "whatsapp_outbound", ["idempotency_key"], unique=True)
    op.create_index("ix_whatsapp_outbound_status", "whatsapp_outbound", ["status"])
    op.create_index("ix_whatsapp_outbound_openwa_message_id", "whatsapp_outbound", ["openwa_message_id"])

    # 5. pending_confirmations
    op.create_table(
        "pending_confirmations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("whatsapp_contacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_pending_confirmations_contact_id", "pending_confirmations", ["contact_id"])
    op.create_index("ix_pending_confirmations_code", "pending_confirmations", ["code"])
    op.create_index("ix_pending_confirmations_status", "pending_confirmations", ["status"])

    # 6. whatsapp_gateway_state
    op.create_table(
        "whatsapp_gateway_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="unknown"),
        sa.Column("is_paused", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("phone_number", sa.String(32), nullable=True),
        sa.Column("push_name", sa.String(128), nullable=True),
        sa.Column("qr_data", sa.Text(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_whatsapp_gateway_state_session_id", "whatsapp_gateway_state", ["session_id"], unique=True)

    # 7. Extend chat_sessions
    op.add_column(
        "chat_sessions",
        sa.Column(
            "wa_contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("whatsapp_contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_chat_sessions_wa_contact_id", "chat_sessions", ["wa_contact_id"])

    # 8. Extend chat_messages
    op.add_column(
        "chat_messages",
        sa.Column("channel", sa.String(32), nullable=False, server_default="web"),
    )
    op.add_column(
        "chat_messages",
        sa.Column("openwa_message_id", sa.String(128), nullable=True),
    )
    op.create_index("ix_chat_messages_openwa_message_id", "chat_messages", ["openwa_message_id"])


def downgrade() -> None:
    # 8. chat_messages
    op.drop_index("ix_chat_messages_openwa_message_id", table_name="chat_messages")
    op.drop_column("chat_messages", "openwa_message_id")
    op.drop_column("chat_messages", "channel")

    # 7. chat_sessions
    op.drop_index("ix_chat_sessions_wa_contact_id", table_name="chat_sessions")
    op.drop_column("chat_sessions", "wa_contact_id")

    # 6. whatsapp_gateway_state
    op.drop_table("whatsapp_gateway_state")

    # 5. pending_confirmations
    op.drop_table("pending_confirmations")

    # 4. whatsapp_outbound
    op.drop_table("whatsapp_outbound")

    # 3. whatsapp_inbound_events
    op.drop_table("whatsapp_inbound_events")

    # 2. whatsapp_link_codes
    op.drop_table("whatsapp_link_codes")

    # 1. whatsapp_contacts
    op.drop_table("whatsapp_contacts")
