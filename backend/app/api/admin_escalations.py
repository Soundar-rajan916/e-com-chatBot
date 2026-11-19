import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_agent, verify_csrf
from app.config import get_settings
from app.db import get_session
from app.models import (
    Agent,
    ChatMessage,
    ChatSession,
    Customer,
    Escalation,
    EscalationEvent,
    EscalationNote,
    Order,
    Refund,
    Trace,
    WhatsAppContact,
)
from app.services.payments import MockPaymentGateway

logger = logging.getLogger("app.api.admin_escalations")
router = APIRouter(prefix="/admin/escalations", tags=["admin-escalations"])
public_session_router = APIRouter(prefix="/sessions", tags=["sessions"])


# ============================================================================
# Helpers
# ============================================================================


def mask_phone(phone: str) -> str:
    cleaned = phone.strip()
    if len(cleaned) >= 10:
        # e.g. "+919876543210" -> "+91 98*** **210"
        return f"{cleaned[:5]}*** **{cleaned[-3:]}"
    return cleaned


def is_case_overdue(created_at: datetime, status: str, sla_minutes: int) -> bool:
    if status == "resolved":
        return False
    now = datetime.now(UTC)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return (now - created_at).total_seconds() > (sla_minutes * 60)


# ============================================================================
# Schemas
# ============================================================================


class EscalationSummary(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str
    customer_phone_masked: str
    reason: str
    reason_type: str
    status: str
    priority: str
    assigned_to: uuid.UUID | None = None
    assigned_agent_name: str | None = None
    refund_id: uuid.UUID | None = None
    order_number: str | None = None
    resolution_note: str | None = None
    is_overdue: bool
    version: int
    created_at: datetime
    updated_at: datetime
    first_response_at: datetime | None = None
    resolved_at: datetime | None = None


class EscalationsListResponse(BaseModel):
    items: list[EscalationSummary]
    total: int


class EscalationStatsResponse(BaseModel):
    open_count: int
    in_progress_count: int
    resolved_count: int
    overdue_count: int
    unassigned_count: int
    my_open_count: int
    by_reason_type: dict[str, int]
    avg_response_time_seconds: float | None = None
    avg_resolution_time_seconds: float | None = None


class CustomerDetail(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    preferred_language: str
    created_at: datetime


class CustomerOrderItemDetail(BaseModel):
    product_title: str
    quantity: int
    unit_price_inr: Decimal


class CustomerOrderDetail(BaseModel):
    id: uuid.UUID
    order_number: str
    status: str
    total_amount_inr: Decimal
    created_at: datetime
    items: list[CustomerOrderItemDetail] = Field(default_factory=list)


class LinkedRefundDetail(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    order_number: str | None = None
    amount: Decimal
    reason: str
    status: str
    created_at: datetime


class ChatMessageItem(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    agent_id: uuid.UUID | None = None
    agent_name: str | None = None
    input_mode: str
    created_at: datetime


class TraceDetail(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    intent: str
    language: str
    router_raw: dict[str, Any]
    tool_calls: list[dict[str, Any]]
    final_answer: str
    models: dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    cost_inr: Decimal
    latency_ms: int
    error: str | None = None
    created_at: datetime


class EscalationNoteItem(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str
    body: str
    created_at: datetime


class EscalationEventItem(BaseModel):
    id: uuid.UUID
    actor_type: str
    actor_id: uuid.UUID | None = None
    actor_name: str | None = None
    action: str
    detail: dict[str, Any]
    created_at: datetime


class EscalationFullDetailResponse(BaseModel):
    escalation: EscalationSummary
    customer: CustomerDetail
    recent_orders: list[CustomerOrderDetail]
    refund: LinkedRefundDetail | None = None
    messages: list[ChatMessageItem]
    traces: list[TraceDetail]
    notes: list[EscalationNoteItem]
    events: list[EscalationEventItem]


# Action Request Models
class AssignRequest(BaseModel):
    agent_id: uuid.UUID | None = None
    version: int
    force: bool = False


class UnassignRequest(BaseModel):
    version: int


class AddNoteRequest(BaseModel):
    body: str = Field(..., min_length=1)


class ReplyRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ActionWithVersionRequest(BaseModel):
    version: int


class RejectRefundRequest(BaseModel):
    reason: str = Field(..., min_length=1)
    version: int


class ResolveRequest(BaseModel):
    resolution_note: str = Field(..., min_length=1)
    version: int


class UpdatePriorityRequest(BaseModel):
    priority: Literal["low", "normal", "high"]
    version: int


# ============================================================================
# Admin Endpoints
# ============================================================================


@router.get("", response_model=EscalationsListResponse)
async def list_escalations(
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    reason_type: str | None = Query(None),
    assigned: str | None = Query(None),
    q: str | None = Query(None),
    overdue_only: bool = Query(False, alias="overdue"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> EscalationsListResponse:
    """List and filter escalations with masked customer phone numbers."""
    settings = get_settings()
    now = datetime.now(UTC)
    sla_cutoff = now - timedelta(minutes=settings.ESCALATION_SLA_MINUTES)

    stmt = select(Escalation).options(
        selectinload(Escalation.customer),
        selectinload(Escalation.assigned_agent),
        selectinload(Escalation.refund).selectinload(Refund.order),
    )

    if status_filter:
        stmt = stmt.where(Escalation.status == status_filter)
    if priority:
        stmt = stmt.where(Escalation.priority == priority)
    if reason_type:
        stmt = stmt.where(Escalation.reason_type == reason_type)

    if assigned:
        if assigned.lower() == "me":
            stmt = stmt.where(Escalation.assigned_to == current_agent.id)
        elif assigned.lower() == "unassigned":
            stmt = stmt.where(Escalation.assigned_to.is_(None))
        else:
            try:
                assigned_uuid = uuid.UUID(assigned)
                stmt = stmt.where(Escalation.assigned_to == assigned_uuid)
            except ValueError:
                pass

    if overdue_only:
        stmt = stmt.where(
            Escalation.status != "resolved",
            Escalation.created_at < sla_cutoff,
        )

    if q and q.strip():
        search = f"%{q.strip()}%"
        stmt = stmt.join(Escalation.customer).where(
            or_(
                Customer.name.ilike(search),
                Customer.phone.ilike(search),
                Escalation.reason.ilike(search),
            )
        )

    # Count query
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count = (await session.execute(count_stmt)).scalar() or 0

    # Sort & Paginate
    stmt = stmt.order_by(desc(Escalation.created_at)).offset(offset).limit(limit)
    result = await session.execute(stmt)
    escalations = result.scalars().all()

    items: list[EscalationSummary] = []
    for esc in escalations:
        order_num = esc.refund.order.order_number if (esc.refund and esc.refund.order) else None
        items.append(
            EscalationSummary(
                id=esc.id,
                session_id=esc.session_id,
                customer_id=esc.customer_id,
                customer_name=esc.customer.name if esc.customer else "Unknown",
                customer_phone_masked=mask_phone(esc.customer.phone) if esc.customer else "",
                reason=esc.reason,
                reason_type=esc.reason_type,
                status=esc.status,
                priority=esc.priority,
                assigned_to=esc.assigned_to,
                assigned_agent_name=esc.assigned_agent.name if esc.assigned_agent else None,
                refund_id=esc.refund_id,
                order_number=order_num,
                resolution_note=esc.resolution_note,
                is_overdue=is_case_overdue(esc.created_at, esc.status, settings.ESCALATION_SLA_MINUTES),
                version=esc.version,
                created_at=esc.created_at,
                updated_at=esc.updated_at,
                first_response_at=esc.first_response_at,
                resolved_at=esc.resolved_at,
            )
        )

    return EscalationsListResponse(items=items, total=total_count)


@router.get("/stats", response_model=EscalationStatsResponse)
async def get_escalation_stats(
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EscalationStatsResponse:
    """Retrieve operational queue stats and 7-day SLAs."""
    settings = get_settings()
    now = datetime.now(UTC)
    seven_days_ago = now - timedelta(days=7)
    sla_cutoff = now - timedelta(minutes=settings.ESCALATION_SLA_MINUTES)

    # 1. Counts by status
    status_counts_stmt = select(Escalation.status, func.count(Escalation.id)).group_by(Escalation.status)
    status_res = (await session.execute(status_counts_stmt)).all()
    status_map = {st: cnt for st, cnt in status_res}

    # 2. Counts by reason_type
    reason_counts_stmt = select(Escalation.reason_type, func.count(Escalation.id)).group_by(
        Escalation.reason_type
    )
    reason_res = (await session.execute(reason_counts_stmt)).all()
    reason_map = {rt: cnt for rt, cnt in reason_res}

    # 3. Overdue count
    overdue_stmt = select(func.count(Escalation.id)).where(
        Escalation.status != "resolved",
        Escalation.created_at < sla_cutoff,
    )
    overdue_count = (await session.execute(overdue_stmt)).scalar() or 0

    # 4. Unassigned count
    unassigned_stmt = select(func.count(Escalation.id)).where(
        Escalation.status != "resolved",
        Escalation.assigned_to.is_(None),
    )
    unassigned_count = (await session.execute(unassigned_stmt)).scalar() or 0

    # 5. My open count
    my_open_stmt = select(func.count(Escalation.id)).where(
        Escalation.status.in_(["open", "in_progress"]),
        Escalation.assigned_to == current_agent.id,
    )
    my_open_count = (await session.execute(my_open_stmt)).scalar() or 0

    # 6. 7-day average response time (seconds)
    resp_stmt = select(
        func.avg(
            func.extract("epoch", Escalation.first_response_at) - func.extract("epoch", Escalation.created_at)
        )
    ).where(
        Escalation.first_response_at.is_not(None),
        Escalation.created_at >= seven_days_ago,
    )
    avg_resp = (await session.execute(resp_stmt)).scalar()

    # 7. 7-day average resolution time (seconds)
    resol_stmt = select(
        func.avg(func.extract("epoch", Escalation.resolved_at) - func.extract("epoch", Escalation.created_at))
    ).where(
        Escalation.resolved_at.is_not(None),
        Escalation.created_at >= seven_days_ago,
    )
    avg_resol = (await session.execute(resol_stmt)).scalar()

    return EscalationStatsResponse(
        open_count=status_map.get("open", 0),
        in_progress_count=status_map.get("in_progress", 0),
        resolved_count=status_map.get("resolved", 0),
        overdue_count=overdue_count,
        unassigned_count=unassigned_count,
        my_open_count=my_open_count,
        by_reason_type=reason_map,
        avg_response_time_seconds=float(avg_resp) if avg_resp is not None else None,
        avg_resolution_time_seconds=float(avg_resol) if avg_resol is not None else None,
    )


class ConversationListItem(BaseModel):
    session_id: uuid.UUID
    channel: str
    customer_name: str
    customer_phone: str
    message_count: int
    last_message: str
    created_at: datetime
    escalation_id: uuid.UUID | None = None
    has_traces: bool = False


@router.get("/conversations/all", response_model=list[ConversationListItem])
async def list_recent_conversations(
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(50, ge=1, le=100),
) -> list[ConversationListItem]:
    """Retrieve recent chat sessions (Web & WhatsApp) so support can inspect bot traces."""
    stmt = (
        select(ChatSession)
        .options(
            selectinload(ChatSession.customer),
            selectinload(ChatSession.wa_contact),
            selectinload(ChatSession.messages),
            selectinload(ChatSession.escalations),
        )
        .order_by(desc(ChatSession.created_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    chat_sessions = result.scalars().all()

    items: list[ConversationListItem] = []
    for cs in chat_sessions:
        cust_name = "Guest Visitor"
        cust_phone = "—"
        if cs.customer:
            cust_name = cs.customer.name
            cust_phone = mask_phone(cs.customer.phone)
        elif cs.wa_contact:
            cust_name = f"WhatsApp User ({cs.wa_contact.phone_number[-4:] if cs.wa_contact.phone_number else 'User'})"
            cust_phone = mask_phone(cs.wa_contact.phone_number or "")

        msgs = list(cs.messages or [])
        msg_count = len(msgs)
        last_msg = msgs[-1].content if msgs else "(No messages)"
        if len(last_msg) > 90:
            last_msg = last_msg[:87] + "..."

        esc_id = cs.escalations[0].id if cs.escalations else None

        trace_stmt = select(func.count(Trace.id)).where(Trace.session_id == cs.id)
        trace_cnt = (await session.execute(trace_stmt)).scalar() or 0

        items.append(
            ConversationListItem(
                session_id=cs.id,
                channel=cs.channel or "web",
                customer_name=cust_name,
                customer_phone=cust_phone,
                message_count=msg_count,
                last_message=last_msg,
                created_at=cs.created_at,
                escalation_id=esc_id,
                has_traces=trace_cnt > 0,
            )
        )
    return items


@router.get("/{id}", response_model=EscalationFullDetailResponse)
async def get_escalation_detail(
    id: uuid.UUID,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EscalationFullDetailResponse:
    """Retrieve full detail for a case: customer, orders, refund, transcript, traces, notes, and audit timeline."""
    settings = get_settings()

    stmt = (
        select(Escalation)
        .options(
            selectinload(Escalation.customer),
            selectinload(Escalation.assigned_agent),
            selectinload(Escalation.refund).selectinload(Refund.order),
            selectinload(Escalation.notes).selectinload(EscalationNote.agent),
            selectinload(Escalation.events),
        )
        .where(Escalation.id == id)
    )
    result = await session.execute(stmt)
    esc = result.scalar_one_or_none()
    if not esc:
        # Check if id is a ChatSession id
        sess_stmt = (
            select(ChatSession)
            .options(selectinload(ChatSession.customer), selectinload(ChatSession.escalations))
            .where(ChatSession.id == id)
        )
        chat_sess = (await session.execute(sess_stmt)).scalar_one_or_none()
        if chat_sess:
            if chat_sess.escalations:
                esc = chat_sess.escalations[0]
            else:
                esc = Escalation(
                    session_id=chat_sess.id,
                    customer_id=chat_sess.customer_id,
                    reason=f"Customer chat inspection ({chat_sess.channel or 'web'})",
                    reason_type="user_requested",
                    status="open",
                    priority="normal",
                )
                session.add(esc)
                await session.flush()
            stmt = (
                select(Escalation)
                .options(
                    selectinload(Escalation.customer),
                    selectinload(Escalation.assigned_agent),
                    selectinload(Escalation.refund).selectinload(Refund.order),
                    selectinload(Escalation.notes).selectinload(EscalationNote.agent),
                    selectinload(Escalation.events),
                )
                .where(Escalation.id == esc.id)
            )
            esc = (await session.execute(stmt)).scalar_one()
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation or session not found.")

    # Fetch recent orders for customer (last 5)
    order_items_list: list[CustomerOrderDetail] = []
    if esc.customer_id:
        orders_stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.customer_id == esc.customer_id)
            .order_by(desc(Order.placed_at))
            .limit(5)
        )
        orders_res = (await session.execute(orders_stmt)).scalars().unique().all()
        for ord_obj in orders_res:
            items = [
                CustomerOrderItemDetail(
                    product_title=it.product_name,
                    quantity=it.quantity,
                    unit_price_inr=it.unit_price,
                )
                for it in (ord_obj.items or [])
            ]
            order_items_list.append(
                CustomerOrderDetail(
                    id=ord_obj.id,
                    order_number=ord_obj.order_number,
                    status=ord_obj.status,
                    total_amount_inr=ord_obj.total_amount,
                    created_at=ord_obj.placed_at,
                    items=items,
                )
            )

    # Fetch transcript messages for session
    msg_stmt = (
        select(ChatMessage)
        .options(selectinload(ChatMessage.agent))
        .where(ChatMessage.session_id == esc.session_id)
        .order_by(ChatMessage.created_at)
    )
    msgs = (await session.execute(msg_stmt)).scalars().all()
    message_items = [
        ChatMessageItem(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            agent_id=m.agent_id,
            agent_name=m.agent.name if m.agent else None,
            input_mode=m.input_mode or "text",
            created_at=m.created_at,
        )
        for m in msgs
    ]

    # Fetch traces for session
    traces_stmt = select(Trace).where(Trace.session_id == esc.session_id).order_by(Trace.created_at)
    traces_rows = (await session.execute(traces_stmt)).scalars().all()
    trace_details = [
        TraceDetail(
            id=t.id,
            session_id=t.session_id,
            intent=t.intent,
            language=t.language,
            router_raw=t.router_raw or {},
            tool_calls=t.tool_calls or [],
            final_answer=t.final_answer,
            models=t.models or {},
            prompt_tokens=t.prompt_tokens,
            completion_tokens=t.completion_tokens,
            cost_inr=t.cost_inr,
            latency_ms=t.latency_ms,
            error=t.error,
            created_at=t.created_at,
        )
        for t in traces_rows
    ]

    # Notes
    note_items = [
        EscalationNoteItem(
            id=n.id,
            agent_id=n.agent_id,
            agent_name=n.agent.name if n.agent else "Agent",
            body=n.body,
            created_at=n.created_at,
        )
        for n in (esc.notes or [])
    ]

    # Resolve agent names for audit events
    agent_ids = {e.actor_id for e in (esc.events or []) if e.actor_type == "agent" and e.actor_id}
    agent_names_map = {}
    if agent_ids:
        agents_res = (await session.execute(select(Agent).where(Agent.id.in_(agent_ids)))).scalars().all()
        agent_names_map = {a.id: a.name for a in agents_res}

    event_items = [
        EscalationEventItem(
            id=e.id,
            actor_type=e.actor_type,
            actor_id=e.actor_id,
            actor_name=agent_names_map.get(e.actor_id, "Agent") if e.actor_type == "agent" else "System",
            action=e.action,
            detail=e.detail or {},
            created_at=e.created_at,
        )
        for e in (esc.events or [])
    ]

    # Linked refund
    linked_refund: LinkedRefundDetail | None = None
    if esc.refund:
        linked_refund = LinkedRefundDetail(
            id=esc.refund.id,
            order_id=esc.refund.order_id,
            order_number=esc.refund.order.order_number if esc.refund.order else None,
            amount=esc.refund.amount,
            reason=esc.refund.reason,
            status=esc.refund.status,
            created_at=esc.refund.created_at,
        )

    order_num = esc.refund.order.order_number if (esc.refund and esc.refund.order) else None

    return EscalationFullDetailResponse(
        escalation=EscalationSummary(
            id=esc.id,
            session_id=esc.session_id,
            customer_id=esc.customer_id,
            customer_name=esc.customer.name if esc.customer else "Unknown",
            customer_phone_masked=mask_phone(esc.customer.phone) if esc.customer else "",
            reason=esc.reason,
            reason_type=esc.reason_type,
            status=esc.status,
            priority=esc.priority,
            assigned_to=esc.assigned_to,
            assigned_agent_name=esc.assigned_agent.name if esc.assigned_agent else None,
            refund_id=esc.refund_id,
            order_number=order_num,
            resolution_note=esc.resolution_note,
            is_overdue=is_case_overdue(esc.created_at, esc.status, settings.ESCALATION_SLA_MINUTES),
            version=esc.version,
            created_at=esc.created_at,
            updated_at=esc.updated_at,
            first_response_at=esc.first_response_at,
            resolved_at=esc.resolved_at,
        ),
        customer=CustomerDetail(
            id=esc.customer.id,
            name=esc.customer.name,
            phone=esc.customer.phone,
            preferred_language=esc.customer.preferred_language,
            created_at=esc.customer.created_at,
        ),
        recent_orders=order_items_list,
        refund=linked_refund,
        messages=message_items,
        traces=trace_details,
        notes=note_items,
        events=event_items,
    )


# ============================================================================
# Escalation Actions
# ============================================================================


@router.post("/{id}/assign", dependencies=[Depends(verify_csrf)])
async def assign_escalation(
    id: uuid.UUID,
    body: AssignRequest,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Assign case to an agent with optimistic concurrency control."""
    esc = await session.get(Escalation, id)
    if not esc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found.")

    if esc.version != body.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: Case was updated by another user. Please refresh.",
        )

    target_agent_id = body.agent_id or current_agent.id

    # If already assigned to someone else and not current agent, prevent reassignment unless admin with force=True
    if esc.assigned_to and esc.assigned_to != current_agent.id and esc.assigned_to != target_agent_id:
        if current_agent.role != "admin" or not body.force:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Case is assigned to another agent. Admin force reassignment required.",
            )

    esc.assigned_to = target_agent_id
    if esc.status == "open":
        esc.status = "in_progress"
    esc.version += 1

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=current_agent.id,
        action="assigned",
        detail={"assigned_to": str(target_agent_id)},
    )
    session.add(event)
    await session.commit()

    return {"message": "Assigned successfully.", "version": esc.version, "status": esc.status}


@router.post("/{id}/unassign", dependencies=[Depends(verify_csrf)])
async def unassign_escalation(
    id: uuid.UUID,
    body: UnassignRequest,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Unassign case and return status to open."""
    esc = await session.get(Escalation, id)
    if not esc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found.")

    if esc.version != body.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: Case was updated by another user. Please refresh.",
        )

    esc.assigned_to = None
    esc.status = "open"
    esc.version += 1

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=current_agent.id,
        action="unassigned",
        detail={},
    )
    session.add(event)
    await session.commit()

    return {"message": "Unassigned successfully.", "version": esc.version, "status": esc.status}


@router.post("/{id}/notes", dependencies=[Depends(verify_csrf)])
async def add_escalation_note(
    id: uuid.UUID,
    body: AddNoteRequest,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Add an internal note to the case."""
    esc = await session.get(Escalation, id)
    if not esc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found.")

    note = EscalationNote(
        escalation_id=esc.id,
        agent_id=current_agent.id,
        body=body.body.strip(),
    )
    session.add(note)

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=current_agent.id,
        action="note_added",
        detail={"length": len(body.body.strip())},
    )
    session.add(event)
    await session.commit()

    return {"message": "Note added successfully.", "note_id": str(note.id)}


async def _maybe_queue_whatsapp_outbound(
    session: AsyncSession,
    session_id: uuid.UUID,
    customer_id: uuid.UUID | None,
    text_content: str,
) -> None:
    """If the session or customer is linked to WhatsApp, queue outbound message so customer receives it on their phone."""
    try:
        chat_sess = await session.get(ChatSession, session_id)
        if not chat_sess:
            return
        wa_contact = None
        if chat_sess.wa_contact_id:
            wa_contact = await session.get(WhatsAppContact, chat_sess.wa_contact_id)
        if not wa_contact and (chat_sess.channel == "whatsapp" or customer_id):
            stmt = select(WhatsAppContact).where(WhatsAppContact.customer_id == customer_id).limit(1)
            wa_contact = (await session.execute(stmt)).scalar_one_or_none()

        if wa_contact and not wa_contact.opted_out:
            from app.services.whatsapp.worker import queue_outbound_message
            await queue_outbound_message(session, wa_contact.id, wa_contact.chat_id, text_content)
            logger.info("Queued agent message to WhatsApp outbound for %s (%s)", wa_contact.phone_number, wa_contact.chat_id)
    except Exception as exc:
        logger.warning("Failed queuing message to WhatsApp outbound: %s", exc)


@router.post("/{id}/reply", dependencies=[Depends(verify_csrf)])
async def reply_to_customer(
    id: uuid.UUID,
    body: ReplyRequest,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Send an agent reply message into the customer chat session."""
    esc = await session.get(Escalation, id)
    if not esc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found.")

    now = datetime.now(UTC)

    # Insert message into chat_messages
    msg = ChatMessage(
        session_id=esc.session_id,
        role="agent",
        agent_id=current_agent.id,
        content=body.message.strip(),
        input_mode="text",
    )
    session.add(msg)

    # If WhatsApp session, queue to WhatsApp outbound as well
    await _maybe_queue_whatsapp_outbound(session, esc.session_id, esc.customer_id, body.message.strip())

    # Track SLA first response timestamp
    if esc.first_response_at is None:
        esc.first_response_at = now

    esc.status = "in_progress"

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=current_agent.id,
        action="replied",
        detail={"message_id": str(msg.id), "length": len(body.message.strip())},
    )
    session.add(event)
    await session.commit()

    logger.info("Agent replied to customer: escalation_id=%s agent_id=%s", esc.id, current_agent.id)
    return {"message": "Reply sent successfully.", "message_id": str(msg.id)}


@router.post("/{id}/refund/approve", dependencies=[Depends(verify_csrf)])
async def approve_refund(
    id: uuid.UUID,
    body: ActionWithVersionRequest,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Approve a pending refund with FOR UPDATE lock, execute payout, and notify chat."""
    esc = await session.get(Escalation, id)
    if not esc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found.")

    if esc.version != body.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: Case was updated by another user. Please refresh.",
        )

    if not esc.refund_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This escalation has no linked refund.",
        )

    # Lock refund row
    refund_stmt = select(Refund).where(Refund.id == esc.refund_id).with_for_update()
    refund = (await session.execute(refund_stmt)).scalar_one_or_none()
    if not refund:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked refund not found.")

    if refund.status != "pending_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund is already '{refund.status}'. Only pending_approval refunds can be approved.",
        )

    # Call MockPaymentGateway
    gateway = MockPaymentGateway()
    payout_res = await gateway.payout(esc.customer_id, refund.order_id, refund.amount)
    if payout_res.get("status") != "success":
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment gateway payout failed. Transaction rolled back.",
        )

    refund.status = "completed"
    esc.version += 1

    # Post automated agent message to chat
    notif_msg = ChatMessage(
        session_id=esc.session_id,
        role="agent",
        agent_id=current_agent.id,
        content=f"Your refund request for ₹{refund.amount:,.2f} has been approved and processed successfully.",
        input_mode="text",
    )
    session.add(notif_msg)

    # If WhatsApp session, queue to WhatsApp outbound as well
    await _maybe_queue_whatsapp_outbound(session, esc.session_id, esc.customer_id, notif_msg.content)

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=current_agent.id,
        action="refund_approved",
        detail={
            "refund_id": str(refund.id),
            "amount": str(refund.amount),
            "txn": payout_res.get("transaction_id"),
        },
    )
    session.add(event)
    await session.commit()

    return {"message": "Refund approved and paid out.", "version": esc.version}


@router.post("/{id}/refund/reject", dependencies=[Depends(verify_csrf)])
async def reject_refund(
    id: uuid.UUID,
    body: RejectRefundRequest,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Reject a pending refund with FOR UPDATE lock and notify chat."""
    esc = await session.get(Escalation, id)
    if not esc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found.")

    if esc.version != body.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: Case was updated by another user. Please refresh.",
        )

    if not esc.refund_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This escalation has no linked refund.",
        )

    refund_stmt = select(Refund).where(Refund.id == esc.refund_id).with_for_update()
    refund = (await session.execute(refund_stmt)).scalar_one_or_none()
    if not refund:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked refund not found.")

    if refund.status != "pending_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund is already '{refund.status}'.",
        )

    refund.status = "rejected"
    esc.version += 1

    # Post message to chat
    notif_msg = ChatMessage(
        session_id=esc.session_id,
        role="agent",
        agent_id=current_agent.id,
        content=f"Your refund request for ₹{refund.amount:,.2f} could not be approved. Reason: {body.reason.strip()}",
        input_mode="text",
    )
    session.add(notif_msg)

    # If WhatsApp session, queue to WhatsApp outbound as well
    await _maybe_queue_whatsapp_outbound(session, esc.session_id, esc.customer_id, notif_msg.content)

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=current_agent.id,
        action="refund_rejected",
        detail={
            "refund_id": str(refund.id),
            "amount": str(refund.amount),
            "reason": body.reason.strip(),
        },
    )
    session.add(event)
    await session.commit()

    return {"message": "Refund rejected.", "version": esc.version}


@router.post("/{id}/resolve", dependencies=[Depends(verify_csrf)])
async def resolve_escalation(
    id: uuid.UUID,
    body: ResolveRequest,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Resolve case with mandatory resolution note and validation that linked refund is completed/rejected."""
    esc = await session.get(Escalation, id)
    if not esc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found.")

    if esc.version != body.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: Case was updated by another user. Please refresh.",
        )

    # Validate linked refund status
    if esc.refund_id:
        refund = await session.get(Refund, esc.refund_id)
        if refund and refund.status == "pending_approval":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot resolve case while linked refund is pending approval. Approve or reject it first.",
            )

    now = datetime.now(UTC)
    esc.status = "resolved"
    esc.resolved_at = now
    esc.resolution_note = body.resolution_note.strip()
    esc.version += 1

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=current_agent.id,
        action="resolved",
        detail={"resolution_note": esc.resolution_note},
    )
    session.add(event)
    await session.commit()

    return {"message": "Escalation resolved successfully.", "version": esc.version}


@router.post("/{id}/reopen", dependencies=[Depends(verify_csrf)])
async def reopen_escalation(
    id: uuid.UUID,
    body: ActionWithVersionRequest,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Reopen a resolved escalation."""
    esc = await session.get(Escalation, id)
    if not esc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found.")

    if esc.version != body.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: Case was updated by another user. Please refresh.",
        )

    esc.status = "in_progress" if esc.assigned_to else "open"
    esc.resolved_at = None
    esc.version += 1

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=current_agent.id,
        action="reopened",
        detail={},
    )
    session.add(event)
    await session.commit()

    return {"message": "Escalation reopened.", "version": esc.version, "status": esc.status}


@router.patch("/{id}/priority", dependencies=[Depends(verify_csrf)])
async def update_escalation_priority(
    id: uuid.UUID,
    body: UpdatePriorityRequest,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Change priority of case with optimistic concurrency control."""
    esc = await session.get(Escalation, id)
    if not esc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found.")

    if esc.version != body.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: Case was updated by another user. Please refresh.",
        )

    old_priority = esc.priority
    esc.priority = body.priority
    esc.version += 1

    event = EscalationEvent(
        escalation_id=esc.id,
        actor_type="agent",
        actor_id=current_agent.id,
        action="priority_changed",
        detail={"old": old_priority, "new": body.priority},
    )
    session.add(event)
    await session.commit()

    return {"message": "Priority updated.", "version": esc.version, "priority": esc.priority}


# ============================================================================
# Public Polling for Customer Chat
# ============================================================================


@public_session_router.get("/{session_id}/messages")
async def poll_session_messages(
    session_id: uuid.UUID,
    customer_id: uuid.UUID = Query(...),
    after: datetime | None = Query(None),
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> list[ChatMessageItem]:
    """Public customer endpoint to poll latest messages (agent replies) for an active session."""
    from app.models import ChatSession

    # Verify session ownership
    chat_sess = await session.get(ChatSession, session_id)
    if not chat_sess or chat_sess.customer_id != customer_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    stmt = (
        select(ChatMessage)
        .options(selectinload(ChatMessage.agent))
        .where(ChatMessage.session_id == session_id)
    )
    if after:
        stmt = stmt.where(ChatMessage.created_at > after)

    stmt = stmt.order_by(ChatMessage.created_at).limit(50)
    result = await session.execute(stmt)
    messages = result.scalars().all()

    return [
        ChatMessageItem(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            agent_id=m.agent_id,
            agent_name=m.agent.name if m.agent else None,
            input_mode=m.input_mode or "text",
            created_at=m.created_at,
        )
        for m in messages
    ]
