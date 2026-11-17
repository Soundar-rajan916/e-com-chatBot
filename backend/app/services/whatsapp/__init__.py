"""WhatsApp Service Module integrating OpenWA Upstream Gateway."""

from app.services.whatsapp.confirmations import (
    create_pending_confirmation,
    verify_and_execute_confirmation,
)
from app.services.whatsapp.fake import FakeWhatsAppProvider
from app.services.whatsapp.formatter import chunk_whatsapp_message, format_for_whatsapp
from app.services.whatsapp.identity import (
    chat_id_to_phone,
    create_link_code,
    get_or_create_contact,
    mask_phone_number,
    normalize_phone_number,
    parse_inbound_command,
    phone_to_chat_id,
    redeem_link_code,
    unlink_contact,
)
from app.services.whatsapp.openwa import OpenWaProvider
from app.services.whatsapp.provider import SendResult, WhatsAppProvider
from app.services.whatsapp.worker import (
    process_pending_inbound_events,
    process_pending_outbound_messages,
    queue_outbound_message,
    run_whatsapp_worker_loop,
)

__all__ = [
    "WhatsAppProvider",
    "OpenWaProvider",
    "FakeWhatsAppProvider",
    "SendResult",
    "format_for_whatsapp",
    "chunk_whatsapp_message",
    "normalize_phone_number",
    "chat_id_to_phone",
    "phone_to_chat_id",
    "mask_phone_number",
    "parse_inbound_command",
    "get_or_create_contact",
    "create_link_code",
    "redeem_link_code",
    "unlink_contact",
    "create_pending_confirmation",
    "verify_and_execute_confirmation",
    "queue_outbound_message",
    "process_pending_inbound_events",
    "process_pending_outbound_messages",
    "run_whatsapp_worker_loop",
]
