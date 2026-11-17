"""WhatsApp Provider Protocol and Data Structures."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SendResult:
    success: bool
    openwa_message_id: str | None = None
    status: str = "sent"  # "sent" | "delivered" | "failed"
    error: str | None = None
    raw_response: dict[str, Any] | None = None


class WhatsAppProvider(Protocol):
    """Protocol for WhatsApp message delivery and session inspection."""

    async def send_text(
        self,
        chat_id: str,
        text: str,
        idempotency_key: str | None = None,
    ) -> SendResult:
        """Send a plain text message to a specific WhatsApp chat ID."""
        ...

    async def get_session_status(self) -> dict[str, Any]:
        """Fetch status of the WhatsApp session."""
        ...

    async def get_qr(self) -> dict[str, Any]:
        """Fetch base64 PNG QR code data for session pairing."""
        ...

    async def get_message_media(
        self,
        chat_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Fetch stored media for a message."""
        ...
