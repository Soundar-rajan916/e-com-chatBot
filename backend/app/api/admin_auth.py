import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_agent, verify_csrf
from app.auth.security import (
    dummy_verify_password,
    generate_session_token,
    hash_session_token,
    verify_password,
)
from app.config import get_settings
from app.db import get_session
from app.models import Agent, AgentSession

logger = logging.getLogger("app.api.admin_auth")
router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class AgentResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str


@router.post("/login", response_model=AgentResponse, dependencies=[Depends(verify_csrf)])
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AgentResponse:
    """
    Authenticate agent with email and password using Argon2id.
    Implements lockout after 5 consecutive failures and constant-time dummy verification.
    Sets secure httpOnly admin_session cookie.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    clean_email = req.email.strip().lower()

    stmt = select(Agent).where(Agent.email == clean_email)
    result = await session.execute(stmt)
    agent = result.scalar_one_or_none()

    if agent is None:
        dummy_verify_password(req.password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Check for active lockout
    if agent.locked_until and agent.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not agent.is_active:
        dummy_verify_password(req.password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(req.password, agent.password_hash):
        agent.failed_attempts += 1
        if agent.failed_attempts >= 5:
            agent.locked_until = now + timedelta(minutes=15)
            logger.warning("Agent account locked due to 5 failed attempts: agent_id=%s", agent.id)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Success: reset failed attempts and lockout
    agent.failed_attempts = 0
    agent.locked_until = None

    token = generate_session_token()
    token_hash = hash_session_token(token)
    expires_at = now + timedelta(hours=settings.ADMIN_SESSION_HOURS)

    agent_session = AgentSession(
        agent_id=agent.id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(agent_session)
    await session.commit()

    is_secure = settings.APP_ENV != "dev"
    response.set_cookie(
        key=settings.ADMIN_COOKIE_NAME,
        value=token,
        max_age=settings.ADMIN_SESSION_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        path="/",
    )

    logger.info("Agent logged in successfully: agent_id=%s role=%s", agent.id, agent.role)

    return AgentResponse(
        id=str(agent.id),
        email=agent.email,
        name=agent.name,
        role=agent.role,
    )


@router.post("/logout", dependencies=[Depends(verify_csrf)])
async def logout(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Revokes the current agent session token and clears the cookie."""
    settings = get_settings()
    token = request.cookies.get(settings.ADMIN_COOKIE_NAME)

    if token:
        token_hash = hash_session_token(token)
        stmt = select(AgentSession).where(
            AgentSession.token_hash == token_hash,
            AgentSession.revoked_at.is_(None),
        )
        result = await session.execute(stmt)
        agent_session = result.scalar_one_or_none()
        if agent_session:
            agent_session.revoked_at = datetime.now(UTC)
            await session.commit()
            logger.info("Agent session revoked: agent_id=%s", agent_session.agent_id)

    response.delete_cookie(
        key=settings.ADMIN_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
    )
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=AgentResponse)
async def get_me(
    current_agent: Annotated[Agent, Depends(get_current_agent)],
) -> AgentResponse:
    """Returns the profile of the currently authenticated agent."""
    return AgentResponse(
        id=str(current_agent.id),
        email=current_agent.email,
        name=current_agent.name,
        role=current_agent.role,
    )
