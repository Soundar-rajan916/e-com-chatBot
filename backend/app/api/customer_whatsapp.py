"""Customer Account WhatsApp Linking Endpoints."""

import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_customer, verify_customer_csrf
from app.config import get_settings
from app.db import get_session
from app.models import Customer, WhatsAppContact, WhatsAppLinkCode
from app.services.whatsapp.identity import (
    create_link_code,
    mask_phone_number,
    unlink_contact,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me/whatsapp", tags=["customer-whatsapp"])


@router.get("", status_code=status.HTTP_200_OK)
async def get_my_whatsapp_status(
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Retrieve WhatsApp connection status for current authenticated customer."""
    stmt = (
        select(WhatsAppContact)
        .where(WhatsAppContact.customer_id == customer.id)
        .order_by(WhatsAppContact.updated_at.desc())
    )
    res = await session.execute(stmt)
    contact = res.scalar_one_or_none()

    if not contact:
        return {
            "is_linked": False,
            "phone_masked": None,
            "opted_out": False,
            "linked_at": None,
        }

    return {
        "is_linked": True,
        "phone_masked": mask_phone_number(contact.phone_number),
        "opted_out": contact.opted_out,
        "linked_at": contact.created_at.isoformat(),
    }


@router.post(
    "/link-code",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_customer_csrf)],
)
async def generate_whatsapp_link_code(
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Generate a 6-digit one-time code to link WhatsApp account."""
    settings = get_settings()
    link_code = await create_link_code(session, customer.id)
    await session.commit()

    now = datetime.now(timezone.utc)
    seconds_left = max(0, int((link_code.expires_at - now).total_seconds()))

    store_phone = settings.WHATSAPP_PHONE_NUMBER or ""
    clean_store_phone = store_phone.replace("+", "").strip()
    wa_link = f"https://wa.me/{clean_store_phone}?text=LINK%20{link_code.code}" if clean_store_phone else None

    return {
        "code": link_code.code,
        "expires_at": link_code.expires_at.isoformat(),
        "expires_in_seconds": seconds_left,
        "wa_link": wa_link,
        "instructions": f"Send 'LINK {link_code.code}' to our WhatsApp support number to complete linking.",
    }


@router.delete(
    "",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_customer_csrf)],
)
async def unlink_my_whatsapp(
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Unlink WhatsApp from current customer account."""
    stmt = select(WhatsAppContact).where(WhatsAppContact.customer_id == customer.id)
    res = await session.execute(stmt)
    contacts = list(res.scalars().all())

    if not contacts:
        return {"status": "not_linked", "message": "No WhatsApp account was linked."}

    for contact in contacts:
        contact.customer_id = None
        contact.updated_at = datetime.now(timezone.utc)

    await session.commit()
    return {"status": "unlinked", "message": "WhatsApp unlinked successfully."}
