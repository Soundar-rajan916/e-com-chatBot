"""phase 3 admin console, governor events, and voice note models

Revision ID: 003_phase3
Revises: 002_phase2
Create Date: 2026-11-13 11:00:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "003_phase3"
down_revision: str | None = "002_phase2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create agents table
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="agent"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agents_email", "agents", ["email"], unique=True)

    # 2. Create agent_sessions table
    op.create_table(
        "agent_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )
    op.create_index("ix_agent_sessions_agent_id", "agent_sessions", ["agent_id"])
    op.create_index("ix_agent_sessions_token_hash", "agent_sessions", ["token_hash"], unique=True)

    # 3. Extend chat_messages table
    op.add_column(
        "chat_messages",
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "chat_messages",
        sa.Column("input_mode", sa.String(20), nullable=False, server_default="text"),
    )
    op.create_index("ix_chat_messages_session_created", "chat_messages", ["session_id", "created_at"])
    op.create_index("ix_chat_messages_agent_id", "chat_messages", ["agent_id"])

    # 4. Extend escalations table
    op.add_column(
        "escalations",
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column(
        "escalations",
        sa.Column("reason_type", sa.String(50), nullable=False, server_default="user_requested"),
    )
    op.add_column(
        "escalations",
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
    )
    op.add_column(
        "escalations",
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "escalations",
        sa.Column(
            "refund_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("refunds.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("escalations", sa.Column("resolution_note", sa.Text(), nullable=True))
    op.add_column("escalations", sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("escalations", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("escalations", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column(
        "escalations",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Backfill customer_id for existing escalations from chat_sessions
    op.execute(
        """
        UPDATE escalations e
        SET customer_id = cs.customer_id
        FROM chat_sessions cs
        WHERE e.session_id = cs.id AND e.customer_id IS NULL;
        """
    )

    # In case there are orphan escalations without session (fallback: set to any existing customer or delete)
    op.execute(
        """
        UPDATE escalations
        SET customer_id = (SELECT id FROM customers LIMIT 1)
        WHERE customer_id IS NULL;
        """
    )
    op.alter_column("escalations", "customer_id", nullable=False)

    # Map old 'closed' status to 'resolved'
    op.execute("UPDATE escalations SET status = 'resolved' WHERE status = 'closed';")

    op.create_index("ix_escalations_status", "escalations", ["status"])
    op.create_index("ix_escalations_created_at", "escalations", ["created_at"])
    op.create_index("ix_escalations_assigned_to", "escalations", ["assigned_to"])
    op.create_index("ix_escalations_refund_id", "escalations", ["refund_id"])
    op.create_index(
        "uq_active_session_escalation",
        "escalations",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('open', 'in_progress')"),
    )

    # 5. Create escalation_notes table
    op.create_table(
        "escalation_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "escalation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("escalations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_escalation_notes_escalation_id", "escalation_notes", ["escalation_id"])
    op.create_index("ix_escalation_notes_agent_id", "escalation_notes", ["agent_id"])

    # 6. Create escalation_events table (audit log)
    op.create_table(
        "escalation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "escalation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("escalations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("detail", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_escalation_events_escalation_id", "escalation_events", ["escalation_id"])
    op.create_index("ix_escalation_events_created_at", "escalation_events", ["created_at"])

    # 7. Create governor_events table
    op.create_table(
        "governor_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("from_mode", sa.String(20), nullable=False),
        sa.Column("to_mode", sa.String(20), nullable=False),
        sa.Column("month_spend_inr", sa.Numeric(12, 4), nullable=False),
        sa.Column("day_spend_inr", sa.Numeric(12, 4), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
    )
    op.create_index("ix_governor_events_at", "governor_events", ["at"])

    # 8. Backfill existing pending_approval refunds without an escalation
    op.execute(
        """
        DO $$
        DECLARE
            ref_rec RECORD;
            chosen_session_id UUID;
            new_esc_id UUID;
        BEGIN
            FOR ref_rec IN
                SELECT r.id AS refund_id, r.customer_id, r.amount, r.created_at
                FROM refunds r
                LEFT JOIN escalations e ON e.refund_id = r.id
                WHERE r.status = 'pending_approval' AND e.id IS NULL
            LOOP
                -- Find existing session for customer or create one
                SELECT id INTO chosen_session_id
                FROM chat_sessions
                WHERE customer_id = ref_rec.customer_id
                ORDER BY created_at DESC
                LIMIT 1;

                IF chosen_session_id IS NULL THEN
                    INSERT INTO chat_sessions (id, customer_id, channel, created_at)
                    VALUES (gen_random_uuid(), ref_rec.customer_id, 'web', ref_rec.created_at)
                    RETURNING id INTO chosen_session_id;
                END IF;

                new_esc_id := gen_random_uuid();

                -- Insert escalation with reason_type refund_pending_approval & priority high
                INSERT INTO escalations (
                    id, session_id, customer_id, reason, reason_type, status,
                    priority, refund_id, version, created_at, updated_at
                ) VALUES (
                    new_esc_id, chosen_session_id, ref_rec.customer_id,
                    'Refund approval pending for amount > limit',
                    'refund_pending_approval', 'open', 'high', ref_rec.refund_id,
                    1, ref_rec.created_at, ref_rec.created_at
                )
                ON CONFLICT (session_id) WHERE status IN ('open', 'in_progress')
                DO UPDATE SET refund_id = ref_rec.refund_id, priority = 'high';

                -- Insert created audit event
                INSERT INTO escalation_events (
                    id, escalation_id, actor_type, actor_id, action, detail, created_at
                ) VALUES (
                    gen_random_uuid(), new_esc_id, 'system', NULL, 'created',
                    jsonb_build_object('reason_type', 'refund_pending_approval', 'refund_id', ref_rec.refund_id::text),
                    ref_rec.created_at
                );
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    # 1. Drop governor_events
    op.drop_table("governor_events")

    # 2. Drop escalation_events
    op.drop_table("escalation_events")

    # 3. Drop escalation_notes
    op.drop_table("escalation_notes")

    # 4. Revert escalations
    op.drop_index("uq_active_session_escalation", table_name="escalations")
    op.drop_index("ix_escalations_refund_id", table_name="escalations")
    op.drop_index("ix_escalations_assigned_to", table_name="escalations")
    op.drop_index("ix_escalations_created_at", table_name="escalations")
    op.drop_index("ix_escalations_status", table_name="escalations")

    op.execute("UPDATE escalations SET status = 'closed' WHERE status = 'resolved';")

    op.drop_column("escalations", "updated_at")
    op.drop_column("escalations", "version")
    op.drop_column("escalations", "resolved_at")
    op.drop_column("escalations", "first_response_at")
    op.drop_column("escalations", "resolution_note")
    op.drop_column("escalations", "refund_id")
    op.drop_column("escalations", "assigned_to")
    op.drop_column("escalations", "priority")
    op.drop_column("escalations", "reason_type")
    op.drop_column("escalations", "customer_id")

    # 5. Revert chat_messages
    op.drop_index("ix_chat_messages_agent_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_session_created", table_name="chat_messages")
    op.drop_column("chat_messages", "input_mode")
    op.drop_column("chat_messages", "agent_id")

    # 6. Drop agent_sessions
    op.drop_table("agent_sessions")

    # 7. Drop agents
    op.drop_table("agents")
