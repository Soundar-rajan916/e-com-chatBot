import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Agent,
    ChatMessage,
    ChatSession,
    Escalation,
    EscalationEvent,
    EscalationNote,
    Order,
    Refund,
    Trace,
    WhatsAppContact,
)
from app.services.payments import MockPaymentGateway, PaymentGatewayInterface

logger = logging.getLogger("app.services.cases")


class CaseRuleError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409, current_case: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.current_case = current_case


async def get_case_or_404(session: AsyncSession, case_id: uuid.UUID, for_update: bool = False) -> Escalation:
    stmt = (
        select(Escalation)
        .options(
            selectinload(Escalation.customer),
            selectinload(Escalation.assigned_agent),
            selectinload(Escalation.refund).selectinload(Refund.order),
            selectinload(Escalation.notes).selectinload(EscalationNote.agent),
            selectinload(Escalation.events),
        )
        .where(Escalation.id == case_id)
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    esc = result.scalar_one_or_none()
    if not esc:
        raise CaseRuleError("not_found", "Case not found", status_code=404)
    return esc


async def get_full_case_response(session: AsyncSession, case_id: uuid.UUID) -> dict[str, Any]:
    esc = await get_case_or_404(session, case_id, for_update=False)

    # Recent orders for customer (up to 5)
    orders_stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.customer_id == esc.customer_id)
        .order_by(desc(Order.placed_at))
        .limit(5)
    )
    orders_rows = (await session.execute(orders_stmt)).scalars().all()
    recent_orders = [
        {
            "id": str(o.id),
            "order_number": o.order_number,
            "status": o.status,
            "total_amount_inr": str(o.total_amount),
            "placed_at": o.placed_at.isoformat() if o.placed_at else None,
            "items": [
                {
                    "product_title": it.product_name,
                    "quantity": it.quantity,
                    "unit_price_inr": str(it.unit_price),
                }
                for it in (o.items or [])
            ],
        }
        for o in orders_rows
    ]

    # Messages
    msgs_stmt = (
        select(ChatMessage)
        .options(selectinload(ChatMessage.agent))
        .where(ChatMessage.session_id == esc.session_id)
        .order_by(ChatMessage.created_at)
    )
    msgs_rows = (await session.execute(msgs_stmt)).scalars().all()
    messages = [
        {
            "id": str(m.id),
            "session_id": str(m.session_id),
            "role": m.role,
            "content": m.content,
            "agent_id": str(m.agent_id) if m.agent_id else None,
            "agent_name": m.agent.name if m.agent else None,
            "input_mode": m.input_mode or "text",
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs_rows
    ]

    # Traces
    traces_stmt = (
        select(Trace)
        .where(Trace.session_id == esc.session_id)
        .order_by(Trace.created_at)
    )
    traces_rows = (await session.execute(traces_stmt)).scalars().all()
    traces = [
        {
            "id": str(t.id),
            "session_id": str(t.session_id),
            "intent": t.intent,
            "language": t.language,
            "router_raw": t.router_raw or {},
            "tool_calls": t.tool_calls or [],
            "final_answer": t.final_answer,
            "models": t.models or {},
            "prompt_tokens": t.prompt_tokens,
            "completion_tokens": t.completion_tokens,
            "cost_inr": str(t.cost_inr),
            "latency_ms": t.latency_ms,
            "error": t.error,
            "created_at": t.created_at.isoformat(),
        }
        for t in traces_rows
    ]

    # Notes
    notes = [
        {
            "id": str(n.id),
            "agent_id": str(n.agent_id),
            "agent_name": n.agent.name if n.agent else "Agent",
            "body": n.body,
            "created_at": n.created_at.isoformat(),
        }
        for n in (esc.notes or [])
    ]

    # Events
    agent_ids = {e.actor_id for e in (esc.events or []) if e.actor_type == "agent" and e.actor_id}
    agent_map = {}
    if agent_ids:
        agents = (await session.execute(select(Agent).where(Agent.id.in_(agent_ids)))).scalars().all()
        agent_map = {a.id: a.name for a in agents}

    events = [
        {
            "id": str(e.id),
            "actor_type": e.actor_type,
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "actor_name": agent_map.get(e.actor_id, "Agent") if e.actor_type == "agent" else "System",
            "action": e.action,
            "detail": e.detail or {},
            "created_at": e.created_at.isoformat(),
        }
        for e in (esc.events or [])
    ]

    # Linked order & refund
    order_info = None
    refund_info = None
    if esc.refund:
        refund_info = {
            "id": str(esc.refund.id),
            "order_id": str(esc.refund.order_id),
            "order_number": esc.refund.order.order_number if esc.refund.order else None,
            "amount": str(esc.refund.amount),
            "reason": esc.refund.reason,
            "status": esc.refund.status,
            "created_at": esc.refund.created_at.isoformat(),
        }
        if esc.refund.order:
            order_info = {
                "id": str(esc.refund.order.id),
                "order_number": esc.refund.order.order_number,
                "status": esc.refund.order.status,
                "total_amount_inr": str(esc.refund.order.total_amount),
                "placed_at": esc.refund.order.placed_at.isoformat() if esc.refund.order.placed_at else None,
                "items": [
                    {
                        "product_title": it.product_name,
                        "quantity": it.quantity,
                        "unit_price_inr": str(it.unit_price),
                    }
                    for it in (esc.refund.order.items or [])
                ],
            }

    phone_clean = esc.customer.phone.strip() if esc.customer else ""
    phone_masked = f"{phone_clean[:5]}*** **{phone_clean[-3:]}" if len(phone_clean) >= 10 else phone_clean

    case_summary = {
        "id": str(esc.id),
        "session_id": str(esc.session_id),
        "customer_id": str(esc.customer_id),
        "customer_name": esc.customer.name if esc.customer else "Unknown",
        "customer_phone_masked": phone_masked,
        "reason": esc.reason,
        "reason_type": esc.reason_type,
        "status": esc.status,
        "priority": esc.priority,
        "assigned_to": str(esc.assigned_to) if esc.assigned_to else None,
        "assigned_agent_name": esc.assigned_agent.name if esc.assigned_agent else None,
        "refund_id": str(esc.refund_id) if esc.refund_id else None,
        "order_number": esc.refund.order.order_number if (esc.refund and esc.refund.order) else None,
        "resolution_note": esc.resolution_note,
        "version": esc.version,
        "created_at": esc.created_at.isoformat(),
        "updated_at": esc.updated_at.isoformat() if esc.updated_at else esc.created_at.isoformat(),
        "first_response_at": esc.first_response_at.isoformat() if esc.first_response_at else None,
        "resolved_at": esc.resolved_at.isoformat() if esc.resolved_at else None,
    }

    res = {
        **case_summary,
        "escalation": case_summary,
        "case": case_summary,
        "customer": {
            "id": str(esc.customer.id),
            "name": esc.customer.name,
            "phone": esc.customer.phone,
            "preferred_language": esc.customer.preferred_language,
            "created_at": esc.customer.created_at.isoformat(),
        },
        "order": order_info,
        "recent_orders": recent_orders,
        "refund": refund_info,
        "linked_refund": refund_info,
        "messages": messages,
        "traces": traces,
        "notes": notes,
        "events": events,
    }
    return res


def verify_case_version(esc: Escalation, expected_version: int) -> None:
    if esc.version != expected_version:
        raise CaseRuleError(
            code="stale_version",
            message="This case was changed by someone else. Please reload.",
            status_code=409,
        )


async def take_case(
    session: AsyncSession,
    case_id: uuid.UUID,
    agent: Agent,
    version: int,
    force: bool = False,
) -> dict[str, Any]:
    """Agent takes an unassigned case or admin reassigns."""
    esc = await get_case_or_404(session, case_id, for_update=True)
    verify_case_version(esc, version)

    if esc.status == "resolved":
        raise CaseRuleError("invalid_state", "Cannot take a resolved case. Reopen it first.", status_code=409)

    # Agents may take unassigned cases or their own case; admins can take/reassign any
    if esc.assigned_to and esc.assigned_to != agent.id:
        if agent.role != "admin" and not force:
            raise CaseRuleError(
                code="already_assigned",
                message="Case is already assigned to another agent. Admin privilege required to reassign.",
                status_code=403,
            )

    old_assigned = esc.assigned_to
    esc.assigned_to = agent.id
    if esc.status == "open":
        esc.status = "in_progress"
    esc.version += 1

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=agent.id,
        action="assigned",
        detail={"previous_assignee": str(old_assigned) if old_assigned else None, "assigned_to": str(agent.id)},
    )
    session.add(event)
    await session.commit()
    return await get_full_case_response(session, case_id)


async def release_case(
    session: AsyncSession,
    case_id: uuid.UUID,
    agent: Agent,
    version: int,
) -> dict[str, Any]:
    """Returns in_progress case to open and unassigned."""
    esc = await get_case_or_404(session, case_id, for_update=True)
    verify_case_version(esc, version)

    if esc.status != "in_progress":
        raise CaseRuleError("invalid_state", "Only in_progress cases can be released to open.", status_code=409)

    if esc.assigned_to != agent.id and agent.role != "admin":
        raise CaseRuleError("forbidden", "You can only release cases assigned to you.", status_code=403)

    esc.assigned_to = None
    esc.status = "open"
    esc.version += 1

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=agent.id,
        action="unassigned",
        detail={},
    )
    session.add(event)
    await session.commit()
    return await get_full_case_response(session, case_id)


async def reply_to_customer(
    session: AsyncSession,
    case_id: uuid.UUID,
    agent: Agent,
    message: str,
    version: int | None = None,
) -> dict[str, Any]:
    """Reply directly to the customer. Allowed only if assigned to caller or caller is admin."""
    esc = await get_case_or_404(session, case_id, for_update=True)
    if version is not None:
        verify_case_version(esc, version)

    if esc.status == "resolved":
        raise CaseRuleError("invalid_state", "Cannot reply to a resolved case. Reopen it first.", status_code=409)

    if esc.assigned_to != agent.id and agent.role != "admin":
        raise CaseRuleError("forbidden", "You must take this case before replying to the customer.", status_code=403)

    now = datetime.now(UTC)
    clean_msg = message.strip()
    if not clean_msg:
        raise CaseRuleError("invalid_input", "Reply message cannot be empty.", status_code=422)

    msg = ChatMessage(
        session_id=esc.session_id,
        role="agent",
        agent_id=agent.id,
        content=clean_msg,
        input_mode="text",
    )
    session.add(msg)

    # Queue to WhatsApp outbound if WhatsApp session
    try:
        chat_sess = await session.get(ChatSession, esc.session_id)
        if chat_sess:
            wa_contact = None
            if chat_sess.wa_contact_id:
                wa_contact = await session.get(WhatsAppContact, chat_sess.wa_contact_id)
            if not wa_contact and (chat_sess.channel == "whatsapp" or esc.customer_id):
                stmt = select(WhatsAppContact).where(WhatsAppContact.customer_id == esc.customer_id).limit(1)
                wa_contact = (await session.execute(stmt)).scalar_one_or_none()
            if wa_contact and not wa_contact.opted_out:
                from app.services.whatsapp.worker import queue_outbound_message
                await queue_outbound_message(session, wa_contact.id, wa_contact.chat_id, clean_msg)
    except Exception as exc:
        logger.warning("Failed queuing message to WhatsApp outbound in cases.py: %s", exc)

    if esc.first_response_at is None:
        esc.first_response_at = now

    esc.status = "in_progress"
    esc.version += 1

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=agent.id,
        action="replied",
        detail={"length": len(clean_msg), "message_id": str(msg.id)},
    )
    session.add(event)
    await session.commit()
    return await get_full_case_response(session, case_id)


async def add_case_note(
    session: AsyncSession,
    case_id: uuid.UUID,
    agent: Agent,
    body: str,
) -> dict[str, Any]:
    """Add a private note to the case (1-2000 characters)."""
    esc = await get_case_or_404(session, case_id, for_update=True)
    clean_body = body.strip()
    if not clean_body or len(clean_body) > 2000:
        raise CaseRuleError("invalid_input", "Note body must be between 1 and 2000 characters.", status_code=422)

    note = EscalationNote(
        escalation_id=esc.id,
        agent_id=agent.id,
        body=clean_body,
    )
    session.add(note)

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=agent.id,
        action="note_added",
        detail={"length": len(clean_body)},
    )
    session.add(event)
    await session.commit()
    return await get_full_case_response(session, case_id)


async def change_priority(
    session: AsyncSession,
    case_id: uuid.UUID,
    agent: Agent,
    priority: Literal["low", "normal", "high"],
    version: int,
) -> dict[str, Any]:
    """Change case priority."""
    esc = await get_case_or_404(session, case_id, for_update=True)
    verify_case_version(esc, version)

    old_priority = esc.priority
    esc.priority = priority
    esc.version += 1

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=agent.id,
        action="priority_changed",
        detail={"old": old_priority, "new": priority},
    )
    session.add(event)
    await session.commit()
    return await get_full_case_response(session, case_id)


async def approve_refund(
    session: AsyncSession,
    case_id: uuid.UUID,
    agent: Agent,
    version: int,
    payment_gateway: PaymentGatewayInterface | None = None,
) -> dict[str, Any]:
    """
    Approve refund in ONE transaction with SELECT ... FOR UPDATE.
    Calls MockPaymentGateway.payout(). Payout failure rolls back with 502.
    Deciding already decided refund returns 409.
    Posts bilingual agent message to customer.
    Does not auto-resolve the case.
    """
    esc = await get_case_or_404(session, case_id, for_update=True)
    verify_case_version(esc, version)

    if not esc.refund_id:
        raise CaseRuleError("no_refund", "This case has no linked refund to approve.", status_code=400)

    # Lock refund row
    refund_stmt = select(Refund).where(Refund.id == esc.refund_id).with_for_update()
    refund = (await session.execute(refund_stmt)).scalar_one_or_none()
    if not refund:
        raise CaseRuleError("not_found", "Linked refund not found.", status_code=404)

    if refund.status != "pending_approval":
        raise CaseRuleError(
            code="already_decided",
            message=f"Refund is already '{refund.status}'. It cannot be approved again.",
            status_code=409,
        )

    # Call gateway payout
    gateway = payment_gateway or MockPaymentGateway()
    try:
        payout_res = await gateway.payout(esc.customer_id, refund.order_id, refund.amount)
        if not payout_res or payout_res.get("status") != "success":
            await session.rollback()
            raise CaseRuleError(
                code="payout_failed",
                message="Payment gateway payout failed. Refund remains pending approval.",
                status_code=502,
            )
    except Exception as exc:
        await session.rollback()
        logger.error("Payout exception: %s", exc)
        raise CaseRuleError(
            code="payout_failed",
            message="Payment gateway payout failed. Refund remains pending approval.",
            status_code=502,
        )

    refund.status = "processed"
    refund.decided_by = f"agent:{agent.email}"
    esc.version += 1

    order_num = refund.order.order_number if refund.order else "your order"

    # Post bilingual agent message
    bilingual_msg = (
        f"Your refund of ₹{refund.amount:,.2f} for order {order_num} has been approved and processed. / "
        f"உங்கள் ஆர்டர் {order_num}-க்கான ₹{refund.amount:,.2f} ரீஃபண்ட் அங்கீகரிக்கப்பட்டு செயலாக்கப்பட்டது."
    )
    chat_msg = ChatMessage(
        session_id=esc.session_id,
        role="agent",
        agent_id=agent.id,
        content=bilingual_msg,
        input_mode="text",
    )
    session.add(chat_msg)

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=agent.id,
        action="refund_approved",
        detail={
            "refund_id": str(refund.id),
            "amount": str(refund.amount),
            "txn": payout_res.get("transaction_id") if isinstance(payout_res, dict) else None,
        },
    )
    session.add(event)
    await session.commit()
    return await get_full_case_response(session, case_id)


async def reject_refund(
    session: AsyncSession,
    case_id: uuid.UUID,
    agent: Agent,
    reason: str,
    version: int,
) -> dict[str, Any]:
    """
    Reject refund in ONE transaction with SELECT ... FOR UPDATE.
    Requires reason. Deciding already decided refund returns 409.
    Posts bilingual agent message to customer.
    Does not auto-resolve the case.
    """
    clean_reason = reason.strip()
    if not clean_reason:
        raise CaseRuleError("invalid_input", "Rejection reason is required.", status_code=422)

    esc = await get_case_or_404(session, case_id, for_update=True)
    verify_case_version(esc, version)

    if not esc.refund_id:
        raise CaseRuleError("no_refund", "This case has no linked refund to reject.", status_code=400)

    refund_stmt = select(Refund).where(Refund.id == esc.refund_id).with_for_update()
    refund = (await session.execute(refund_stmt)).scalar_one_or_none()
    if not refund:
        raise CaseRuleError("not_found", "Linked refund not found.", status_code=404)

    if refund.status != "pending_approval":
        raise CaseRuleError(
            code="already_decided",
            message=f"Refund is already '{refund.status}'. It cannot be rejected again.",
            status_code=409,
        )

    refund.status = "rejected"
    refund.decided_by = f"agent:{agent.email}"
    esc.version += 1

    order_num = refund.order.order_number if refund.order else "your order"

    bilingual_msg = (
        f"Your refund request for order {order_num} has been rejected. Reason: {clean_reason} / "
        f"உங்கள் ஆர்டர் {order_num}-க்கான ரீஃபண்ட் கோரிக்கை நிராகரிக்கப்பட்டது. காரணம்: {clean_reason}"
    )
    chat_msg = ChatMessage(
        session_id=esc.session_id,
        role="agent",
        agent_id=agent.id,
        content=bilingual_msg,
        input_mode="text",
    )
    session.add(chat_msg)

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=agent.id,
        action="refund_rejected",
        detail={"refund_id": str(refund.id), "reason": clean_reason},
    )
    session.add(event)
    await session.commit()
    return await get_full_case_response(session, case_id)


async def resolve_case(
    session: AsyncSession,
    case_id: uuid.UUID,
    agent: Agent,
    resolution_note: str,
    version: int,
) -> dict[str, Any]:
    """Resolve case with mandatory note. Blocked if refund is pending."""
    clean_note = resolution_note.strip()
    if not clean_note:
        raise CaseRuleError("invalid_input", "Resolution note is required to resolve case.", status_code=422)

    esc = await get_case_or_404(session, case_id, for_update=True)
    verify_case_version(esc, version)

    if esc.status == "resolved":
        raise CaseRuleError("invalid_state", "Case is already resolved.", status_code=409)

    # Check if linked refund is still pending
    if esc.refund_id:
        refund = await session.get(Refund, esc.refund_id)
        if refund and refund.status == "pending_approval":
            raise CaseRuleError(
                code="refund_pending",
                message="Cannot resolve case while refund is pending approval. Approve or reject it first.",
                status_code=409,
            )

    now = datetime.now(UTC)
    esc.status = "resolved"
    esc.resolved_at = now
    esc.resolution_note = clean_note
    esc.version += 1

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=agent.id,
        action="resolved",
        detail={"resolution_note": clean_note},
    )
    session.add(event)
    await session.commit()
    return await get_full_case_response(session, case_id)


async def reopen_case(
    session: AsyncSession,
    case_id: uuid.UUID,
    agent: Agent,
    version: int,
) -> dict[str, Any]:
    """Reopen a resolved case."""
    esc = await get_case_or_404(session, case_id, for_update=True)
    verify_case_version(esc, version)

    if esc.status != "resolved":
        raise CaseRuleError("invalid_state", "Only resolved cases can be reopened.", status_code=409)

    # Reopen returns resolved -> in_progress (if it had an assignee) else open
    esc.status = "in_progress" if esc.assigned_to else "open"
    esc.resolved_at = None
    esc.version += 1

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=agent.id,
        action="reopened",
        detail={},
    )
    session.add(event)
    await session.commit()
    return await get_full_case_response(session, case_id)
