import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_optional_customer
from app.auth.security import generate_session_token, hash_session_token
from app.config import get_settings
from app.db import get_session
from app.models import ChatMessage, ChatSession, Customer
from app.schemas import ChatRequest, ChatResponse
from app.services.pipeline import handle_message

logger = logging.getLogger("app.api.chat")
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    req: Request,
    resp: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    customer: Annotated[Customer | None, Depends(get_optional_customer)],
) -> ChatResponse:
    """
    Primary chat endpoint. Thin adapter delegating to handle_message pipeline.
    Supports authenticated customers (via shop_session cookie) and anonymous visitors
    (via support_anon cookie), as well as legacy tests passing customer_id directly.
    """
    settings = get_settings()

    # Determine customer_id and anon_token
    customer_id: uuid.UUID | None = None
    if customer is not None:
        customer_id = customer.id
    elif settings.ALLOW_CLIENT_CUSTOMER_ID and request.customer_id is not None:
        customer_id = request.customer_id

    anon_token = req.cookies.get(settings.ANON_COOKIE_NAME)
    if customer_id is None and not anon_token:
        # Create a new anonymous visitor token
        anon_token = generate_session_token()
        is_secure = settings.APP_ENV != "dev"
        expires_at = datetime.now(UTC) + timedelta(days=30)
        resp.set_cookie(
            key=settings.ANON_COOKIE_NAME,
            value=anon_token,
            max_age=30 * 86400,
            expires=expires_at,
            path="/",
            httponly=True,
            secure=is_secure,
            samesite="lax",
        )

    context_dict = request.context.model_dump() if request.context else None

    return await handle_message(
        session=session,
        customer_id=customer_id,
        session_id=request.session_id,
        text=request.message,
        channel="web",
        input_mode=request.input_mode,
        anon_token=anon_token,
        context=context_dict,
    )


@router.get("/chat/current")
async def get_current_chat(
    req: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    customer: Annotated[Customer | None, Depends(get_optional_customer)],
) -> dict:
    """
    Retrieves the most recent active chat session and its messages for restoring widget state.
    """
    settings = get_settings()
    anon_token = req.cookies.get(settings.ANON_COOKIE_NAME)
    anon_token_hash = hash_session_token(anon_token) if anon_token else None

    stmt = select(ChatSession).options(selectinload(ChatSession.messages))

    if customer is not None:
        stmt = stmt.where(ChatSession.customer_id == customer.id)
    elif anon_token_hash:
        stmt = stmt.where(ChatSession.anon_token_hash == anon_token_hash)
    else:
        return {"session_id": None, "messages": [], "customer_id": None}

    stmt = stmt.order_by(ChatSession.created_at.desc()).limit(1)
    res = await session.execute(stmt)
    chat_session = res.scalar_one_or_none()

    if not chat_session:
        return {
            "session_id": None,
            "messages": [],
            "customer_id": str(customer.id) if customer else None,
        }

    return {
        "session_id": str(chat_session.id),
        "customer_id": str(chat_session.customer_id) if chat_session.customer_id else None,
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "input_mode": m.input_mode,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in chat_session.messages
        ],
    }
