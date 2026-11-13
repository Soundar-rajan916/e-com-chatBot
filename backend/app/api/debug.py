from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Trace
from app.schemas import TraceResponse

router = APIRouter()


@router.get("/traces/{session_id}", response_model=list[TraceResponse])
async def get_session_traces(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[TraceResponse]:
    """
    Read-only inspection of execution traces for a given chat session.
    """
    stmt = select(Trace).where(Trace.session_id == session_id).order_by(Trace.created_at.asc())
    result = await session.execute(stmt)
    traces = list(result.scalars().all())
    return [TraceResponse.model_validate(t) for t in traces]
