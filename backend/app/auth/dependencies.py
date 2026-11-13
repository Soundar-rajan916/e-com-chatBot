from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.security import hash_session_token
from app.config import get_settings
from app.db import get_session
from app.models import Agent, AgentSession


async def verify_csrf(request: Request) -> None:
    """
    Enforce CSRF protection on state-changing requests.
    Requires header 'X-Requested-With: admin-console' for POST, PATCH, PUT, DELETE.
    """
    if request.method in ("POST", "PATCH", "PUT", "DELETE"):
        csrf_header = request.headers.get("X-Requested-With")
        if csrf_header != "admin-console":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing or invalid X-Requested-With header for admin request.",
            )


async def get_current_agent(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Agent:
    """
    Authenticate the agent via the secure httpOnly admin_session cookie.
    Validates token hash, expiry, and revocation in agent_sessions table.
    """
    settings = get_settings()
    token = request.cookies.get(settings.ADMIN_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    token_hash = hash_session_token(token)
    now = datetime.now(UTC)

    stmt = (
        select(AgentSession)
        .options(selectinload(AgentSession.agent))
        .where(
            AgentSession.token_hash == token_hash,
            AgentSession.revoked_at.is_(None),
            AgentSession.expires_at > now,
        )
    )
    result = await session.execute(stmt)
    agent_session = result.scalar_one_or_none()

    if agent_session is None or not agent_session.agent or not agent_session.agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked session.",
        )

    # Attach session to request state for convenient reference if needed
    request.state.agent_session = agent_session
    return agent_session.agent


async def require_admin(
    agent: Annotated[Agent, Depends(get_current_agent)],
) -> Agent:
    """Enforces that the authenticated agent has the 'admin' role."""
    if agent.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return agent
