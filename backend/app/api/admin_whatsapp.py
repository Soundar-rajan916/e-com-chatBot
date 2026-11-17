"""Staff Console WhatsApp Connection Management & Risk Disclosures."""

import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_agent, verify_csrf
from app.config import get_settings
from app.db import get_session
from app.models import Agent, WhatsAppGatewayState
from app.services.whatsapp.openwa import OpenWaProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/whatsapp", tags=["admin-whatsapp"])

RISK_STATEMENT = (
    "open-wa is unofficial. WhatsApp may ban numbers that use unofficial clients, "
    "and WhatsApp Web changes can break the library without notice. Use a DEDICATED number "
    "that is not important to the owner, only REPLY to people who message first, never send "
    "bulk or unsolicited messages, and keep the official WhatsApp Business Cloud API as the "
    "documented production upgrade path."
)


@router.get("/status", status_code=status.HTTP_200_OK)
async def get_whatsapp_gateway_status(
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Retrieve WhatsApp connection status, dashboard info, and risk statement for staff console."""
    settings = get_settings()
    session_id = settings.OPENWA_SESSION_ID

    stmt = select(WhatsAppGatewayState).where(WhatsAppGatewayState.session_id == session_id)
    res = await session.execute(stmt)
    state = res.scalar_one_or_none()

    provider = OpenWaProvider()
    live_status = await provider.get_session_status()

    # If status requires pairing QR, fetch live QR code
    qr_code = None
    if live_status.get("status") in ("qr_ready", "initializing", "created"):
        qr_resp = await provider.get_qr()
        qr_code = qr_resp.get("qrCode")

    phone = live_status.get("phone") or (state.phone_number if state else None)
    push_name = live_status.get("pushName") or (state.push_name if state else None)
    status_str = live_status.get("status") or (state.status if state else "unknown")
    is_paused = state.is_paused if state else False

    return {
        "enabled": settings.WHATSAPP_ENABLED,
        "session_id": session_id,
        "status": status_str,
        "is_paused": is_paused,
        "phone": phone,
        "push_name": push_name,
        "qr_code": qr_code,
        "risk_statement": RISK_STATEMENT,
        "dashboard_url": "http://localhost:2785",
        "last_heartbeat": state.last_heartbeat_at.isoformat() if (state and state.last_heartbeat_at) else None,
    }


@router.post("/pause", status_code=status.HTTP_200_OK, dependencies=[Depends(verify_csrf)])
async def pause_whatsapp_gateway(
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Pause automated WhatsApp outbound replies."""
    settings = get_settings()
    session_id = settings.OPENWA_SESSION_ID

    stmt = select(WhatsAppGatewayState).where(WhatsAppGatewayState.session_id == session_id)
    res = await session.execute(stmt)
    state = res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not state:
        state = WhatsAppGatewayState(
            session_id=session_id,
            status="paused",
            is_paused=True,
            last_heartbeat_at=now,
        )
        session.add(state)
    else:
        state.is_paused = True
        state.updated_at = now

    await session.commit()
    return {"status": "paused", "is_paused": True}


@router.post("/resume", status_code=status.HTTP_200_OK, dependencies=[Depends(verify_csrf)])
async def resume_whatsapp_gateway(
    current_agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Resume automated WhatsApp outbound replies."""
    settings = get_settings()
    session_id = settings.OPENWA_SESSION_ID

    stmt = select(WhatsAppGatewayState).where(WhatsAppGatewayState.session_id == session_id)
    res = await session.execute(stmt)
    state = res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not state:
        state = WhatsAppGatewayState(
            session_id=session_id,
            status="ready",
            is_paused=False,
            last_heartbeat_at=now,
        )
        session.add(state)
    else:
        state.is_paused = False
        state.updated_at = now

    await session.commit()
    return {"status": "resumed", "is_paused": False}
