"""WhatsApp Inbound & Outbound Background Workers with Advisory Locking and Pacing."""

import asyncio
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import (
    ChatMessage,
    ChatSession,
    Customer,
    PendingConfirmation,
    WhatsAppContact,
    WhatsAppGatewayState,
    WhatsAppInboundEvent,
    WhatsAppOutbound,
)
from app.services.pipeline import handle_message
from app.services.whatsapp.confirmations import (
    create_pending_confirmation,
    verify_and_execute_confirmation,
)
from app.services.whatsapp.formatter import chunk_whatsapp_message, format_for_whatsapp
from app.services.whatsapp.identity import (
    get_or_create_contact,
    parse_inbound_command,
    redeem_link_code,
    unlink_contact,
)
from app.services.whatsapp.provider import WhatsAppProvider
from app.services.whatsapp.stt import VoiceNoteError, transcribe_voice_note

logger = logging.getLogger(__name__)


async def queue_outbound_message(
    db: AsyncSession,
    contact_id: uuid.UUID,
    chat_id: str,
    text_content: str,
) -> list[WhatsAppOutbound]:
    """Queue one or more outbound WhatsApp messages with Markdown conversion and chunking."""
    formatted = format_for_whatsapp(text_content)
    chunks = chunk_whatsapp_message(formatted)
    outbound_items: list[WhatsAppOutbound] = []

    for chunk in chunks:
        idempotency_key = f"out_{uuid.uuid4().hex}"
        item = WhatsAppOutbound(
            contact_id=contact_id,
            chat_id=chat_id,
            body=chunk,
            idempotency_key=idempotency_key,
            status="pending",
        )
        db.add(item)
        outbound_items.append(item)

    await db.flush()
    return outbound_items


async def process_single_inbound_event(
    db: AsyncSession,
    event: WhatsAppInboundEvent,
    provider: WhatsAppProvider,
) -> None:
    """Process a single WhatsApp inbound event under an advisory transaction lock."""
    payload = event.raw_payload or {}
    event_type = event.event_type

    if event_type == "session.status":
        status_val = payload.get("status") or (payload.get("data") or {}).get("status", "unknown")
        session_id = event.session_id
        stmt = select(WhatsAppGatewayState).where(WhatsAppGatewayState.session_id == session_id)
        res = await db.execute(stmt)
        state = res.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if not state:
            state = WhatsAppGatewayState(
                session_id=session_id,
                status=status_val,
                last_heartbeat_at=now,
            )
            db.add(state)
        else:
            state.status = status_val
            state.last_heartbeat_at = now
            state.updated_at = now
        event.status = "processed"
        event.processed_at = now
        await db.commit()
        return

    if event_type == "message.ack":
        data = payload.get("data") or payload
        openwa_msg_id = data.get("id") or data.get("messageId")
        new_status = data.get("status", "delivered")
        now = datetime.now(timezone.utc)
        if openwa_msg_id:
            stmt = select(WhatsAppOutbound).where(WhatsAppOutbound.openwa_message_id == openwa_msg_id)
            res = await db.execute(stmt)
            out_item = res.scalar_one_or_none()
            if out_item:
                out_item.status = new_status

        event.status = "processed"
        event.processed_at = now
        await db.commit()
        return

    if event_type != "message.received":
        logger.info("Ignoring unhandled event type: %s", event_type)
        event.status = "ignored"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # Process message.received
    msg_data = payload.get("data") or payload
    from_me = msg_data.get("fromMe", False)
    is_group = msg_data.get("isGroup", False)
    kind = msg_data.get("kind", "individual")

    # Filter out echoes and groups
    if from_me or is_group or kind in ("group", "broadcast", "channel", "status"):
        logger.info("Ignoring non-individual inbound message %s", msg_data.get("id"))
        event.status = "ignored"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    chat_id = msg_data.get("from") or msg_data.get("chatId")
    if not chat_id:
        event.status = "failed"
        event.error_message = "Missing chat ID in message.received"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # Take PostgreSQL advisory lock per chat_id to serialize messages from this contact
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:chat_id))"), {"chat_id": chat_id})

    # Fetch or create contact
    sender_phone = msg_data.get("senderPhone")
    contact = await get_or_create_contact(db, chat_id=chat_id, sender_phone=sender_phone)

    # Audio vs text extraction
    msg_type = msg_data.get("type", "text")
    input_mode = "text"
    inbound_text = msg_data.get("body", "").strip()
    openwa_inbound_id = msg_data.get("id")

    if msg_type in ("voice", "audio", "ptt"):
        input_mode = "voice"
        media = msg_data.get("media") or {}
        # If media data is missing from the webhook payload, attempt fallback fetch from OpenWA
        if not media.get("data") and openwa_inbound_id:
            try:
                fetched_media = await provider.get_message_media(chat_id, openwa_inbound_id)
                if fetched_media.get("data"):
                    media = fetched_media
            except Exception as f_err:
                logger.warning("Failed to fetch message media for %s: %s", openwa_inbound_id, f_err)

        try:
            transcription = await transcribe_voice_note(media)
            inbound_text = transcription.get("text", "")
        except VoiceNoteError as v_err:
            logger.warning("Voice note validation failed: %s", v_err)
            await queue_outbound_message(
                db,
                contact.id,
                chat_id,
                f"Sorry, we could not process your voice note: {v_err}. Please send a text message instead.",
            )
            event.status = "processed"
            event.processed_at = datetime.now(timezone.utc)
            await db.commit()
            return

    if not inbound_text:
        event.status = "ignored"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # Command parsing
    cmd, arg = parse_inbound_command(inbound_text)

    # 1. Opt-out (STOP)
    if cmd == "STOP":
        contact.opted_out = True
        contact.updated_at = datetime.now(timezone.utc)
        await queue_outbound_message(
            db,
            contact.id,
            chat_id,
            "You have unsubscribed from WhatsApp messages. We will no longer message you. Send START at any time to resume.",
        )
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # 2. Opt-in (START)
    if cmd == "START":
        contact.opted_out = False
        contact.updated_at = datetime.now(timezone.utc)
        await queue_outbound_message(
            db,
            contact.id,
            chat_id,
            "Welcome back! Your WhatsApp notifications and assistant support are now active. How can we help you today?",
        )
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # If contact is opted out and command is NOT START, do not process
    if contact.opted_out:
        logger.info("Ignoring message from opted out contact %s", contact.phone_number)
        event.status = "ignored"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # 3. Account Link (LINK <code>)
    if cmd == "LINK" and arg:
        success, reply_msg, _ = await redeem_link_code(db, contact, arg)
        await queue_outbound_message(db, contact.id, chat_id, reply_msg)
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # 4. Account Unlink (UNLINK)
    if cmd == "UNLINK":
        success, reply_msg = await unlink_contact(db, contact)
        await queue_outbound_message(db, contact.id, chat_id, reply_msg)
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # 5. Typed Confirmation (YES <code>)
    if cmd == "YES" and arg:
        success, reply_msg, _ = await verify_and_execute_confirmation(db, contact, arg)
        await queue_outbound_message(db, contact.id, chat_id, reply_msg)
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # 6. Cancellation (CANCEL)
    if cmd == "CANCEL":
        # Cancel any pending confirmations
        await db.execute(
            text(
                "UPDATE pending_confirmations SET status = 'cancelled' "
                "WHERE contact_id = :cid AND status = 'pending'"
            ),
            {"cid": contact.id},
        )
        await queue_outbound_message(db, contact.id, chat_id, "Cancelled any pending action.")
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # 7. Conversational Message -> Route to Chat Pipeline
    # Find active WhatsApp chat session for contact
    stmt = (
        select(ChatSession)
        .where(
            ChatSession.wa_contact_id == contact.id,
            ChatSession.channel == "whatsapp",
        )
        .order_by(ChatSession.created_at.desc())
    )
    res = await db.execute(stmt)
    chat_session = res.scalar_one_or_none()

    if not chat_session:
        chat_session = ChatSession(
            customer_id=contact.customer_id,
            wa_contact_id=contact.id,
            channel="whatsapp",
        )
        db.add(chat_session)
        await db.flush()
    else:
        # Keep customer_id updated in case contact was linked recently
        if chat_session.customer_id != contact.customer_id:
            chat_session.customer_id = contact.customer_id
            await db.flush()

    # Record incoming message in chat_messages
    openwa_inbound_id = msg_data.get("id")
    user_msg = ChatMessage(
        session_id=chat_session.id,
        role="user",
        content=inbound_text,
        input_mode=input_mode,
        channel="whatsapp",
        openwa_message_id=openwa_inbound_id,
    )
    db.add(user_msg)
    await db.flush()

    # Pre-check: If this is an unlinked user asking for account-locked actions (order status or refunds)
    # Give them an explicit account linking prompt with instructions
    clean_lower = inbound_text.lower()
    is_account_query = any(k in clean_lower for k in ("order", "refund", "return", "status", "track", "cancel"))
    if not contact.customer_id and is_account_query and not any(k in clean_lower for k in ("ord-", "order #")):
        prompt_text = (
            "To check order details, track shipments, or request refunds, please link your WhatsApp number to your store account.\n\n"
            "1. Visit our website and sign in to your account.\n"
            "2. Under *Account Settings*, click *Link WhatsApp* to generate a 6-digit code.\n"
            "3. Send the code here as: *LINK <code>*\n\n"
            "Or ask me any questions about our products, sizing, or store policies!"
        )
        await queue_outbound_message(db, contact.id, chat_id, prompt_text)
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # Check for High-Impact Refund Request that requires typed confirmation
    # If customer is linked, asks for refund, and provides an ORD-XXXXX number:
    # Instead of creating the refund automatically, create a pending confirmation!
    import re
    ord_match = re.search(r"\b(ORD-\d{4,8})\b", inbound_text, re.IGNORECASE)
    is_refund_intent = any(k in clean_lower for k in ("refund", "return", "money back"))

    if contact.customer_id and ord_match and is_refund_intent:
        order_num = ord_match.group(1).upper()
        # Create pending confirmation
        conf = await create_pending_confirmation(
            db=db,
            contact=contact,
            action_type="refund",
            payload={"order_number": order_num, "reason": inbound_text},
        )
        reply = (
            f"⚠️ *Refund Confirmation Required*\n\n"
            f"You requested a refund for Order *{order_num}*.\n\n"
            f"To authorize this refund, please reply:\n"
            f"*YES {conf.code}*\n\n"
            f"*(This code expires in 15 minutes. Reply CANCEL to abort.)*"
        )
        await queue_outbound_message(db, contact.id, chat_id, reply)
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # Execute full channel-agnostic chat pipeline
    pipeline_resp = await handle_message(
        session=db,
        customer_id=contact.customer_id,
        session_id=chat_session.id,
        text=inbound_text,
        channel="whatsapp",
        input_mode=input_mode,
    )

    # Queue outbound response (with audio confirmation header if received via voice note)
    outbound_text = pipeline_resp.reply
    if input_mode == "voice" and inbound_text:
        outbound_text = f"🎙️ _Heard: \"{inbound_text}\"_\n\n{outbound_text}"

    await queue_outbound_message(db, contact.id, chat_id, outbound_text)

    event.status = "processed"
    event.processed_at = datetime.now(timezone.utc)
    await db.commit()


async def process_pending_inbound_events(
    db: AsyncSession,
    provider: WhatsAppProvider,
    batch_size: int = 5,
) -> int:
    """Fetch and process pending inbound events using SELECT ... FOR UPDATE SKIP LOCKED."""
    stmt = (
        select(WhatsAppInboundEvent)
        .where(WhatsAppInboundEvent.status == "pending")
        .order_by(WhatsAppInboundEvent.created_at.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    res = await db.execute(stmt)
    events = list(res.scalars().all())

    count = 0
    for event in events:
        try:
            await process_single_inbound_event(db, event, provider)
            count += 1
        except Exception as exc:
            logger.error("Failed processing inbound event %s: %s", event.id, exc, exc_info=True)
            event.status = "failed"
            event.error_message = str(exc)
            event.processed_at = datetime.now(timezone.utc)
            await db.commit()

    return count


async def process_pending_outbound_messages(
    db: AsyncSession,
    provider: WhatsAppProvider,
    batch_size: int = 5,
) -> int:
    """Fetch and send pending outbound messages adhering to pacing delays and reply-only guard."""
    settings = get_settings()

    stmt = (
        select(WhatsAppOutbound)
        .where(WhatsAppOutbound.status == "pending")
        .order_by(WhatsAppOutbound.created_at.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    res = await db.execute(stmt)
    items = list(res.scalars().all())

    sent_count = 0
    now = datetime.now(timezone.utc)
    reply_window = timedelta(hours=settings.WHATSAPP_REPLY_ONLY_HOURS)

    for item in items:
        # Check contact 72-hour reply-only guard
        stmt_c = select(WhatsAppContact).where(WhatsAppContact.id == item.contact_id)
        res_c = await db.execute(stmt_c)
        contact = res_c.scalar_one_or_none()

        if contact and contact.last_seen_at:
            if now - contact.last_seen_at > reply_window:
                logger.warning(
                    "72h reply window expired for contact %s (last seen %s). Skipping outbound send.",
                    contact.phone_number,
                    contact.last_seen_at,
                )
                item.status = "failed"
                item.error_message = "72h reply window expired; customer must message first."
                await db.commit()
                continue

        # Rate pacing: minimum delay with 50% random jitter
        base_delay_sec = settings.WHATSAPP_OUTBOUND_MIN_DELAY_MS / 1000.0
        jittered_delay = base_delay_sec * (1.0 + random.uniform(0.0, 0.5))
        await asyncio.sleep(jittered_delay)

        # Dispatch via WhatsApp provider
        item.status = "sending"
        item.attempts += 1
        item.last_attempt_at = datetime.now(timezone.utc)
        await db.flush()

        send_res = await provider.send_text(
            chat_id=item.chat_id,
            text=item.body,
            idempotency_key=item.idempotency_key,
        )

        if send_res.success:
            item.status = send_res.status or "sent"
            item.openwa_message_id = send_res.openwa_message_id
            item.sent_at = datetime.now(timezone.utc)
            item.error_message = None
            sent_count += 1
        else:
            item.status = "failed"
            item.error_message = send_res.error

        await db.commit()

    return sent_count


async def run_whatsapp_worker_loop(
    session_factory: Any,
    provider: WhatsAppProvider,
    stop_event: asyncio.Event,
) -> None:
    """Continuous background loop processing inbound webhooks and outbound rate-paced messages."""
    settings = get_settings()
    poll_sec = max(0.1, settings.WHATSAPP_POLL_INTERVAL_MS / 1000.0)

    logger.info("WhatsApp background worker loop started (polling every %.2fs)", poll_sec)

    while not stop_event.is_set():
        try:
            async with session_factory() as session:
                # 1. Process inbound events
                await process_pending_inbound_events(session, provider, batch_size=5)

                # 2. Check if outbound is paused
                session_id = settings.OPENWA_SESSION_ID
                stmt = select(WhatsAppGatewayState).where(WhatsAppGatewayState.session_id == session_id)
                res = await session.execute(stmt)
                state = res.scalar_one_or_none()

                if not state or not state.is_paused:
                    # 3. Process outbound messages with pacing
                    await process_pending_outbound_messages(session, provider, batch_size=5)

        except asyncio.CancelledError:
            logger.info("WhatsApp worker loop cancelled.")
            break
        except Exception as exc:
            logger.error("Error in WhatsApp worker loop iteration: %s", exc, exc_info=True)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_sec)
        except asyncio.TimeoutError:
            pass

    logger.info("WhatsApp background worker loop stopped.")
