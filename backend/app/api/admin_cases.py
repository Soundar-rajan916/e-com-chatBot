import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
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
    Refund,
)
from app.services.cases import (
    CaseRuleError,
    add_case_note,
    approve_refund,
    change_priority,
    get_full_case_response,
    reject_refund,
    release_case,
    reopen_case,
    reply_to_customer,
    resolve_case,
    take_case,
)

logger = logging.getLogger("app.api.admin_cases")
router = APIRouter(prefix="/admin/cases", tags=["admin-cases"])
public_router = APIRouter(prefix="/sessions", tags=["sessions"])


def standard_error(code: str, message: str, status_code: int = 400) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


# ============================================================================
# Schemas
# ============================================================================

class CustomerPreview(BaseModel):
    id: str
    name: str
    phone_masked: str


class RefundSummary(BaseModel):
    id: str
    amount: str
    status: str
    order_number: str | None = None


class CaseListItem(BaseModel):
    id: str
    session_id: str | None = None
    status: str
    priority: str
    reason_type: str
    overdue: bool
    age_seconds: int
    customer: CustomerPreview
    assigned_to: str | None = None
    assigned_agent_name: str | None = None
    preview: str
    refund: RefundSummary | None = None
    created_at: str
    updated_at: str
    version: int


class CasesListResponse(BaseModel):
    items: list[CaseListItem]
    total: int
    cursor: str | None = None


class CaseStatsResponse(BaseModel):
    open: int
    in_progress: int
    overdue: int
    unassigned: int
    mine_open: int


class AssignPayload(BaseModel):
    version: int
    agent_id: uuid.UUID | None = None
    force: bool = False


class VersionPayload(BaseModel):
    version: int


class NotePayload(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class ReplyPayload(BaseModel):
    message: str = Field(..., min_length=1)
    version: int | None = None


class RejectPayload(BaseModel):
    reason: str = Field(..., min_length=1)
    version: int


class ResolvePayload(BaseModel):
    resolution_note: str | None = None
    note: str | None = None
    version: int

    @property
    def clean_note(self) -> str:
        val = self.resolution_note or self.note
        return val.strip() if val else ""


class PriorityPayload(BaseModel):
    priority: Literal["low", "normal", "high"]
    version: int


class CustomerVisibleMessage(BaseModel):
    id: str
    role: str
    sender_label: str
    content: str
    created_at: str
    input_mode: str = "text"


# ============================================================================
# Admin Case Endpoints
# ============================================================================

@router.get("", response_model=CasesListResponse)
async def list_cases(
    response: Response,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    reason_type: str | None = Query(None),
    assigned: str | None = Query("any"),
    overdue: bool = Query(False),
    q: str | None = Query(None),
    sort: str = Query("newest"),
    limit: int = Query(25, ge=1, le=100),
    cursor: int = Query(0, ge=0),
) -> CasesListResponse:
    """Retrieve cases queue with filters, preview, customer details and masked phone."""
    response.headers["Cache-Control"] = "no-store"
    settings = get_settings()
    now = datetime.now(UTC)
    sla_cutoff = now - timedelta(minutes=settings.ESCALATION_SLA_MINUTES)

    stmt = (
        select(Escalation)
        .options(
            selectinload(Escalation.customer),
            selectinload(Escalation.assigned_agent),
            selectinload(Escalation.refund).selectinload(Refund.order),
        )
    )

    if status_filter and status_filter.lower() != "all":
        stmt = stmt.where(Escalation.status == status_filter)

    if priority and priority.lower() != "all":
        stmt = stmt.where(Escalation.priority == priority)

    if reason_type and reason_type.lower() != "all":
        stmt = stmt.where(Escalation.reason_type == reason_type)

    if assigned:
        if assigned.lower() == "me":
            stmt = stmt.where(Escalation.assigned_to == current_agent.id)
        elif assigned.lower() == "unassigned":
            stmt = stmt.where(Escalation.assigned_to.is_(None))

    if overdue:
        stmt = stmt.where(
            Escalation.status != "resolved",
            Escalation.created_at < sla_cutoff,
        )

    if q and q.strip():
        search_term = f"%{q.strip()}%"
        stmt = stmt.join(Escalation.customer).where(
            or_(
                Customer.name.ilike(search_term),
                Customer.phone.ilike(search_term),
                Escalation.reason.ilike(search_term),
            )
        )

    # Count total matching query
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0

    # Sort & Paginate
    if sort == "oldest":
        stmt = stmt.order_by(Escalation.created_at.asc())
    else:
        stmt = stmt.order_by(Escalation.created_at.desc())

    stmt = stmt.offset(cursor).limit(limit)
    escalations = (await session.execute(stmt)).scalars().all()

    # Pre-fetch last customer message previews for the cases
    session_ids = [e.session_id for e in escalations]
    previews_map = {}
    if session_ids:
        # Fetch customer messages for these sessions
        msgs_stmt = (
            select(ChatMessage.session_id, ChatMessage.content)
            .where(ChatMessage.session_id.in_(session_ids), ChatMessage.role == "user")
            .order_by(ChatMessage.created_at.desc())
        )
        msgs_rows = (await session.execute(msgs_stmt)).all()
        for s_id, content in msgs_rows:
            if s_id not in previews_map:
                previews_map[s_id] = content[:120]

    items: list[CaseListItem] = []
    for esc in escalations:
        created_utc = esc.created_at.replace(tzinfo=UTC) if esc.created_at.tzinfo is None else esc.created_at
        age_seconds = int((now - created_utc).total_seconds())
        is_overdue = esc.status != "resolved" and age_seconds > (settings.ESCALATION_SLA_MINUTES * 60)

        phone_clean = esc.customer.phone.strip() if esc.customer else ""
        phone_masked = f"{phone_clean[:5]}*** **{phone_clean[-3:]}" if len(phone_clean) >= 10 else phone_clean

        refund_summary = None
        if esc.refund:
            order_num = esc.refund.order.order_number if esc.refund.order else None
            refund_summary = RefundSummary(
                id=str(esc.refund.id),
                amount=str(esc.refund.amount),
                status=esc.refund.status,
                order_number=order_num,
            )

        items.append(
            CaseListItem(
                id=str(esc.id),
                session_id=str(esc.session_id),
                status=esc.status,
                priority=esc.priority,
                reason_type=esc.reason_type,
                overdue=is_overdue,
                age_seconds=max(0, age_seconds),
                customer=CustomerPreview(
                    id=str(esc.customer.id) if esc.customer else "",
                    name=esc.customer.name if esc.customer else "Unknown",
                    phone_masked=phone_masked,
                ),
                assigned_to=str(esc.assigned_to) if esc.assigned_to else None,
                assigned_agent_name=esc.assigned_agent.name if esc.assigned_agent else None,
                preview=previews_map.get(esc.session_id, esc.reason[:120]),
                refund=refund_summary,
                created_at=esc.created_at.isoformat(),
                updated_at=esc.updated_at.isoformat() if esc.updated_at else esc.created_at.isoformat(),
                version=esc.version,
            )
        )

    next_cursor = str(cursor + limit) if (cursor + limit) < total else None
    return CasesListResponse(items=items, total=total, cursor=next_cursor)


@router.get("/stats", response_model=CaseStatsResponse)
async def get_case_stats(
    response: Response,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CaseStatsResponse:
    """Retrieve counts for open, in_progress, overdue, unassigned, and mine_open."""
    response.headers["Cache-Control"] = "no-store"
    settings = get_settings()
    now = datetime.now(UTC)
    sla_cutoff = now - timedelta(minutes=settings.ESCALATION_SLA_MINUTES)

    open_count = (await session.execute(select(func.count(Escalation.id)).where(Escalation.status == "open"))).scalar() or 0
    in_progress_count = (await session.execute(select(func.count(Escalation.id)).where(Escalation.status == "in_progress"))).scalar() or 0
    overdue_count = (await session.execute(select(func.count(Escalation.id)).where(Escalation.status != "resolved", Escalation.created_at < sla_cutoff))).scalar() or 0
    unassigned_count = (await session.execute(select(func.count(Escalation.id)).where(Escalation.status != "resolved", Escalation.assigned_to.is_(None)))).scalar() or 0
    mine_open_count = (await session.execute(select(func.count(Escalation.id)).where(Escalation.status.in_(["open", "in_progress"]), Escalation.assigned_to == current_agent.id))).scalar() or 0

    return CaseStatsResponse(
        open=open_count,
        in_progress=in_progress_count,
        overdue=overdue_count,
        unassigned=unassigned_count,
        mine_open=mine_open_count,
    )


@router.get("/{id}")
async def get_case(
    id: uuid.UUID,
    response: Response,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Retrieve full case detail."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return await get_full_case_response(session, id)
    except CaseRuleError as e:
        raise standard_error(e.code, e.message, e.status_code)


@router.post("/{id}/assign", dependencies=[Depends(verify_csrf)])
@router.post("/{id}/take", dependencies=[Depends(verify_csrf)])
async def assign_case_endpoint(
    id: uuid.UUID,
    body: AssignPayload,
    response: Response,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Take case or assign to an agent."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return await take_case(session, id, current_agent, body.version, force=body.force)
    except CaseRuleError as e:
        raise standard_error(e.code, e.message, e.status_code)


@router.post("/{id}/unassign", dependencies=[Depends(verify_csrf)])
@router.post("/{id}/release", dependencies=[Depends(verify_csrf)])
async def unassign_case_endpoint(
    id: uuid.UUID,
    body: VersionPayload,
    response: Response,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Release case back to open."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return await release_case(session, id, current_agent, body.version)
    except CaseRuleError as e:
        raise standard_error(e.code, e.message, e.status_code)


@router.post("/{id}/notes", dependencies=[Depends(verify_csrf)])
async def add_note_endpoint(
    id: uuid.UUID,
    body: NotePayload,
    response: Response,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Add a private team note."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return await add_case_note(session, id, current_agent, body.body)
    except CaseRuleError as e:
        raise standard_error(e.code, e.message, e.status_code)


@router.post("/{id}/reply", dependencies=[Depends(verify_csrf)])
async def reply_endpoint(
    id: uuid.UUID,
    body: ReplyPayload,
    response: Response,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Send an agent reply to the customer."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return await reply_to_customer(session, id, current_agent, body.message, body.version)
    except CaseRuleError as e:
        raise standard_error(e.code, e.message, e.status_code)


@router.post("/{id}/refund/approve", dependencies=[Depends(verify_csrf)])
@router.post("/{id}/approve-refund", dependencies=[Depends(verify_csrf)])
async def approve_refund_endpoint(
    id: uuid.UUID,
    body: VersionPayload,
    response: Response,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Approve refund with payout and post bilingual message."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return await approve_refund(session, id, current_agent, body.version)
    except CaseRuleError as e:
        raise standard_error(e.code, e.message, e.status_code)


@router.post("/{id}/refund/reject", dependencies=[Depends(verify_csrf)])
@router.post("/{id}/reject-refund", dependencies=[Depends(verify_csrf)])
async def reject_refund_endpoint(
    id: uuid.UUID,
    body: RejectPayload,
    response: Response,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Reject refund with reason and post bilingual message."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return await reject_refund(session, id, current_agent, body.reason, body.version)
    except CaseRuleError as e:
        raise standard_error(e.code, e.message, e.status_code)


@router.post("/{id}/resolve", dependencies=[Depends(verify_csrf)])
async def resolve_case_endpoint(
    id: uuid.UUID,
    body: ResolvePayload,
    response: Response,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Resolve case with resolution note."""
    response.headers["Cache-Control"] = "no-store"
    note = body.clean_note
    if not note:
        raise standard_error("invalid_input", "Resolution note is required.", 422)
    try:
        return await resolve_case(session, id, current_agent, note, body.version)
    except CaseRuleError as e:
        raise standard_error(e.code, e.message, e.status_code)


@router.post("/{id}/reopen", dependencies=[Depends(verify_csrf)])
async def reopen_case_endpoint(
    id: uuid.UUID,
    body: VersionPayload,
    response: Response,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Reopen resolved case."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return await reopen_case(session, id, current_agent, body.version)
    except CaseRuleError as e:
        raise standard_error(e.code, e.message, e.status_code)


@router.patch("/{id}/priority", dependencies=[Depends(verify_csrf)])
async def priority_endpoint(
    id: uuid.UUID,
    body: PriorityPayload,
    response: Response,
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Change priority."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return await change_priority(session, id, current_agent, body.priority, body.version)
    except CaseRuleError as e:
        raise standard_error(e.code, e.message, e.status_code)


# ============================================================================
# Public Customer Polling
# ============================================================================

@public_router.get("/{session_id}/messages", response_model=list[CustomerVisibleMessage])
async def get_customer_session_messages(
    session_id: uuid.UUID,
    customer_id: uuid.UUID = Query(...),
    after: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=50),
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> list[CustomerVisibleMessage]:
    """
    Public customer endpoint returning assistant and agent messages.
    Agent messages are labelled 'Support executive' with no agent identity.
    403 for wrong customer. Never leaks notes, traces or events.
    """
    chat_sess = await session.get(ChatSession, session_id)
    if not chat_sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    if chat_sess.customer_id != customer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for customer.")

    stmt = select(ChatMessage).where(
        ChatMessage.session_id == session_id,
        ChatMessage.role.in_(["user", "assistant", "agent"]),
    )
    if after:
        stmt = stmt.where(ChatMessage.created_at > after)

    stmt = stmt.order_by(ChatMessage.created_at.asc()).limit(limit)
    messages = (await session.execute(stmt)).scalars().all()

    def get_sender_label(role: str) -> str:
        if role == "agent":
            return "Support executive"
        elif role == "user":
            return "Customer"
        return "AI Assistant"

    return [
        CustomerVisibleMessage(
            id=str(m.id),
            role=m.role,
            sender_label=get_sender_label(m.role),
            content=m.content,
            created_at=m.created_at.isoformat(),
            input_mode=m.input_mode or "text",
        )
        for m in messages
    ]
