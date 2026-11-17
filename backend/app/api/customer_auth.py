import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_customer, verify_customer_csrf
from app.auth.security import (
    dummy_verify_password,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.config import get_settings
from app.db import get_session
from app.models import ChatSession, Customer, CustomerSession
from app.schemas import (
    CustomerChangePasswordRequest,
    CustomerLoginRequest,
    CustomerRegisterRequest,
    CustomerResponse,
    CustomerUpdateRequest,
)

logger = logging.getLogger("app.api.customer_auth")
router = APIRouter(prefix="/auth", tags=["customer-auth"])


async def claim_anonymous_sessions(
    session: AsyncSession,
    anon_token: str | None,
    customer_id,
) -> None:
    """Links any anonymous chat session started by this browser to the authenticated customer."""
    if not anon_token:
        return
    token_hash = hash_session_token(anon_token)
    stmt = (
        update(ChatSession)
        .where(
            ChatSession.anon_token_hash == token_hash,
            ChatSession.customer_id.is_(None),
        )
        .values(customer_id=customer_id)
    )
    await session.execute(stmt)


@router.post(
    "/register",
    response_model=CustomerResponse,
    dependencies=[Depends(verify_customer_csrf)],
)
async def register(
    req: CustomerRegisterRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CustomerResponse:
    settings = get_settings()
    now = datetime.now(UTC)
    clean_email = req.email.strip().lower()
    clean_phone = req.phone.strip()

    # Check for existing email or phone
    stmt = select(Customer).where(
        (Customer.email == clean_email) | (Customer.phone == clean_phone)
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        if existing.email == clean_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this phone number already exists.",
        )

    # Create new customer
    pw_hash = hash_password(req.password)
    customer = Customer(
        email=clean_email,
        password_hash=pw_hash,
        name=req.name.strip(),
        phone=clean_phone,
        preferred_language=req.preferred_language or "en",
        is_active=True,
    )
    session.add(customer)
    await session.flush()

    # Create customer session
    token = generate_session_token()
    token_hash = hash_session_token(token)
    expires_at = now + timedelta(days=settings.SHOP_SESSION_MAX_AGE_DAYS)
    cust_session = CustomerSession(
        customer_id=customer.id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(cust_session)

    # Claim anonymous chat session if cookie exists
    anon_token = request.cookies.get(settings.ANON_COOKIE_NAME)
    await claim_anonymous_sessions(session, anon_token, customer.id)

    # Auto-link any existing WhatsApp contacts matching this phone number
    from app.models import WhatsAppContact
    from app.services.whatsapp.identity import normalize_phone_number, PHONE_DIGITS_RE
    norm_phone = normalize_phone_number(clean_phone)
    raw_digits = PHONE_DIGITS_RE.sub("", clean_phone)
    if raw_digits:
        last10 = raw_digits[-10:] if len(raw_digits) >= 10 else raw_digits
        stmt_wa = select(WhatsAppContact).where(
            (WhatsAppContact.phone_number == norm_phone)
            | (WhatsAppContact.phone_number == clean_phone)
            | (WhatsAppContact.phone_number.endswith(last10))
        )
        res_wa = await session.execute(stmt_wa)
        for wa_contact in res_wa.scalars():
            wa_contact.customer_id = customer.id

    await session.commit()
    await session.refresh(customer)

    # Set shop_session cookie
    is_secure = settings.APP_ENV != "dev"
    max_age = settings.SHOP_SESSION_MAX_AGE_DAYS * 86400
    response.set_cookie(
        key=settings.SHOP_COOKIE_NAME,
        value=token,
        max_age=max_age,
        expires=expires_at,
        path="/",
        httponly=True,
        secure=is_secure,
        samesite="lax",
    )

    logger.info("New customer registered: customer_id=%s", customer.id)
    return CustomerResponse.model_validate(customer)


@router.post(
    "/login",
    response_model=CustomerResponse,
    dependencies=[Depends(verify_customer_csrf)],
)
async def login(
    req: CustomerLoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CustomerResponse:
    settings = get_settings()
    now = datetime.now(UTC)
    clean_email = req.email.strip().lower()

    stmt = select(Customer).where(Customer.email == clean_email)
    result = await session.execute(stmt)
    customer = result.scalar_one_or_none()

    if customer is None:
        dummy_verify_password(req.password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Check for active lockout
    if customer.locked_until and customer.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account temporarily locked due to multiple failed login attempts. Please try again later.",
        )

    if not customer.is_active or not customer.password_hash:
        dummy_verify_password(req.password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(req.password, customer.password_hash):
        customer.failed_attempts += 1
        if customer.failed_attempts >= settings.CUSTOMER_LOCKOUT_ATTEMPTS:
            customer.locked_until = now + timedelta(minutes=settings.CUSTOMER_LOCKOUT_MINUTES)
            logger.warning(
                "Customer account locked due to consecutive failed attempts: customer_id=%s",
                customer.id,
            )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Success
    customer.failed_attempts = 0
    customer.locked_until = None
    customer.last_login_at = now

    token = generate_session_token()
    token_hash = hash_session_token(token)
    expires_at = now + timedelta(days=settings.SHOP_SESSION_MAX_AGE_DAYS)

    cust_session = CustomerSession(
        customer_id=customer.id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(cust_session)

    anon_token = request.cookies.get(settings.ANON_COOKIE_NAME)
    await claim_anonymous_sessions(session, anon_token, customer.id)
    await session.commit()

    is_secure = settings.APP_ENV != "dev"
    max_age = settings.SHOP_SESSION_MAX_AGE_DAYS * 86400
    response.set_cookie(
        key=settings.SHOP_COOKIE_NAME,
        value=token,
        max_age=max_age,
        expires=expires_at,
        path="/",
        httponly=True,
        secure=is_secure,
        samesite="lax",
    )

    logger.info("Customer logged in: customer_id=%s", customer.id)
    return CustomerResponse.model_validate(customer)


@router.post(
    "/logout",
    dependencies=[Depends(verify_customer_csrf)],
)
async def logout(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, bool]:
    settings = get_settings()
    token = request.cookies.get(settings.SHOP_COOKIE_NAME)
    if token:
        token_hash = hash_session_token(token)
        now = datetime.now(UTC)
        stmt = (
            update(CustomerSession)
            .where(CustomerSession.token_hash == token_hash)
            .values(revoked_at=now)
        )
        await session.execute(stmt)
        await session.commit()

    response.delete_cookie(settings.SHOP_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=CustomerResponse)
async def get_me(
    customer: Annotated[Customer, Depends(get_current_customer)],
) -> CustomerResponse:
    return CustomerResponse.model_validate(customer)


@router.patch(
    "/me",
    response_model=CustomerResponse,
    dependencies=[Depends(verify_customer_csrf)],
)
async def update_me(
    req: CustomerUpdateRequest,
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CustomerResponse:
    if req.name is not None and req.name.strip():
        customer.name = req.name.strip()
    if req.preferred_language is not None and req.preferred_language.strip():
        customer.preferred_language = req.preferred_language.strip()
    await session.commit()
    await session.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.post(
    "/change-password",
    dependencies=[Depends(verify_customer_csrf)],
)
async def change_password(
    req: CustomerChangePasswordRequest,
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, bool]:
    if not customer.password_hash or not verify_password(req.old_password, customer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    customer.password_hash = hash_password(req.new_password)
    await session.commit()
    logger.info("Password changed for customer_id=%s", customer.id)
    return {"ok": True}
