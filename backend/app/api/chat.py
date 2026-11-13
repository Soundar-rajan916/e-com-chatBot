from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas import ChatRequest, ChatResponse
from app.services.pipeline import handle_message

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    """
    Primary chat endpoint. Thin adapter delegating to handle_message pipeline.
    """
    return await handle_message(
        session=session,
        customer_id=request.customer_id,
        session_id=request.session_id,
        text=request.message,
        channel="web",
    )
