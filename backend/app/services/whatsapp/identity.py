"""WhatsApp Identity, Phone normalization, Link Codes, and Inbound Commands."""

import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Customer, WhatsAppContact, WhatsAppLinkCode

PHONE_DIGITS_RE = re.compile(r"\D")


def normalize_phone_number(raw: str) -> str:
    """Normalize phone number to E.164 string format (+919876543210)."""
    if not raw:
        return ""
    digits = PHONE_DIGITS_RE.sub("", raw)
    if not digits:
        return ""
    return f"+{digits}"


def chat_id_to_phone(chat_id: str) -> str:
    """Derive E.164 phone number from OpenWA chat ID (e.g. 919876543210@c.us)."""
    raw_user = chat_id.split("@")[0]
    return normalize_phone_number(raw_user)


def phone_to_chat_id(phone: str) -> str:
    """Convert E.164 phone number to OpenWA chat ID (e.g. +919876543210 -> 919876543210@c.us)."""
    digits = PHONE_DIGITS_RE.sub("", phone)
    return f"{digits}@c.us"


def mask_phone_number(phone: str) -> str:
    """Mask phone number keeping only country code prefix and last 3 digits."""
    if len(phone) <= 6:
        return "***"
    prefix = phone[:3]
    suffix = phone[-3:]
    return f"{prefix}***{suffix}"


def parse_inbound_command(text: str) -> tuple[str, str | None]:
    """Parse special control commands from incoming text.

    Returns:
        (command_type, argument)
        command_type: "STOP" | "START" | "LINK" | "UNLINK" | "YES" | "CANCEL" | "MESSAGE"
    """
    clean = text.strip()
    upper = clean.upper()

    if upper in ("STOP", "STOPALL", "UNSUBSCRIBE", "CANCEL"):
        return ("STOP", None)
    if upper in ("START", "UNSTOP", "RESUME", "OPTIN"):
        return ("START", None)
    if upper == "UNLINK":
        return ("UNLINK", None)

    # LINK <code> or CONNECT <code>
    link_match = re.match(r"^(?:LINK|CONNECT)\s+([A-Z0-9]{4,8})$", upper)
    if link_match:
        return ("LINK", link_match.group(1))

    # YES <code> or CONFIRM <code>
    yes_match = re.match(r"^(?:YES|CONFIRM)\s+([A-Z0-9]{4,8})$", upper)
    if yes_match:
        return ("YES", yes_match.group(1))

    return ("MESSAGE", clean)


async def find_customer_by_phone(db: AsyncSession, raw_phone: str) -> Customer | None:
    """Find Customer account by phone number with flexible formatting (E.164, raw, or last 10 digits)."""
    if not raw_phone:
        return None
    normalized = normalize_phone_number(raw_phone)
    digits = PHONE_DIGITS_RE.sub("", raw_phone)
    if not digits:
        return None

    # 1. Exact match against normalized E.164 or raw string
    stmt = select(Customer).where(
        (Customer.phone == normalized) | (Customer.phone == raw_phone)
    )
    res = await db.execute(stmt)
    cust = res.scalars().first()
    if cust:
        return cust

    # 2. Match by last 10 digits (standard mobile number length)
    if len(digits) >= 10:
        last10 = digits[-10:]
        stmt = select(Customer).where(Customer.phone.endswith(last10))
        res = await db.execute(stmt)
        return res.scalars().first()

    return None


async def get_or_create_contact(
    db: AsyncSession,
    chat_id: str,
    sender_phone: str | None = None,
) -> WhatsAppContact:
    """Fetch existing contact by chat_id or create a new one."""
    stmt = select(WhatsAppContact).where(WhatsAppContact.chat_id == chat_id)
    res = await db.execute(stmt)
    contact = res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    phone = normalize_phone_number(sender_phone) if sender_phone else chat_id_to_phone(chat_id)

    if contact:
        contact.last_seen_at = now
        # If contact was previously unlinked, check if a registered Customer account now matches
        if not contact.customer_id and (contact.phone_number or phone):
            cust = await find_customer_by_phone(db, contact.phone_number or phone)
            if cust:
                contact.customer_id = cust.id
        await db.flush()
        return contact

    # Try finding by phone_number to handle @lid / @c.us resolution
    if phone:
        stmt = select(WhatsAppContact).where(WhatsAppContact.phone_number == phone)
        res = await db.execute(stmt)
        contact = res.scalar_one_or_none()
        if contact:
            contact.chat_id = chat_id
            contact.last_seen_at = now
            if not contact.customer_id:
                cust = await find_customer_by_phone(db, phone)
                if cust:
                    contact.customer_id = cust.id
            await db.flush()
            return contact

    # Create new contact and auto-link to matching Customer if registered
    matched_cust = await find_customer_by_phone(db, phone) if phone else None
    contact = WhatsAppContact(
        phone_number=phone,
        chat_id=chat_id,
        customer_id=matched_cust.id if matched_cust else None,
        opted_out=False,
        last_seen_at=now,
    )
    db.add(contact)
    await db.flush()
    return contact


async def create_link_code(db: AsyncSession, customer_id: Any) -> WhatsAppLinkCode:
    """Generate a 6-digit one-time code to link a WhatsApp number to a Customer account."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.WHATSAPP_LINK_CODE_EXPIRE_MINUTES)

    # Invalidate previous unused codes for this customer
    await db.execute(
        update(WhatsAppLinkCode)
        .where(
            WhatsAppLinkCode.customer_id == customer_id,
            WhatsAppLinkCode.used_at.is_(None),
        )
        .values(used_at=now)
    )

    code = "".join(secrets.choice("0123456789") for _ in range(6))
    link_code = WhatsAppLinkCode(
        customer_id=customer_id,
        code=code,
        expires_at=expires_at,
    )
    db.add(link_code)
    await db.flush()
    return link_code


async def redeem_link_code(
    db: AsyncSession,
    contact: WhatsAppContact,
    code: str,
) -> tuple[bool, str, Customer | None]:
    """Redeem a link code from a WhatsApp contact."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(WhatsAppLinkCode)
        .where(
            WhatsAppLinkCode.code == code.strip(),
            WhatsAppLinkCode.used_at.is_(None),
            WhatsAppLinkCode.expires_at > now,
        )
        .order_by(WhatsAppLinkCode.created_at.desc())
    )
    res = await db.execute(stmt)
    link_code = res.scalar_one_or_none()

    if not link_code:
        return (False, "Invalid or expired link code. Please generate a new code in your account settings.", None)

    # Fetch customer
    cust_res = await db.execute(select(Customer).where(Customer.id == link_code.customer_id))
    customer = cust_res.scalar_one_or_none()
    if not customer:
        return (False, "Customer account not found.", None)

    # Mark code used and link contact
    link_code.used_at = now
    contact.customer_id = customer.id
    contact.updated_at = now
    await db.flush()

    return (
        True,
        f"Success! Your WhatsApp is now linked to your {customer.name} account. You can check your order status, manage refunds, and get support here.",
        customer,
    )


async def unlink_contact(db: AsyncSession, contact: WhatsAppContact) -> tuple[bool, str]:
    """Unlink WhatsApp contact from customer account."""
    if not contact.customer_id:
        return (False, "Your WhatsApp is not linked to any account.")

    contact.customer_id = None
    contact.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return (True, "Your WhatsApp account has been unlinked successfully.")
