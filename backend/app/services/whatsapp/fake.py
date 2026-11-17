"""In-memory Fake WhatsApp Provider for tests and development."""

import uuid
from typing import Any

from app.services.whatsapp.provider import SendResult, WhatsAppProvider


class FakeWhatsAppProvider(WhatsAppProvider):
    """In-memory fake provider recording messages and mocking responses."""

    def __init__(self, default_status: str = "ready") -> None:
        self.sent_messages: list[dict[str, Any]] = []
        self.session_status: str = default_status
        self.should_fail: bool = False
        self.fail_error: str = "Simulated WhatsApp error"
        self.mock_phone: str = "+919876543210"
        self.mock_push_name: str = "Store Support"

    async def send_text(
        self,
        chat_id: str,
        text: str,
        idempotency_key: str | None = None,
    ) -> SendResult:
        if self.should_fail:
            return SendResult(
                success=False,
                error=self.fail_error,
                status="failed",
            )

        msg_id = f"fake_msg_{uuid.uuid4().hex[:12]}"
        record = {
            "id": msg_id,
            "chatId": chat_id,
            "text": text,
            "idempotencyKey": idempotency_key,
            "status": "sent",
        }
        self.sent_messages.append(record)
        return SendResult(
            success=True,
            openwa_message_id=msg_id,
            status="sent",
            raw_response=record,
        )

    async def get_session_status(self) -> dict[str, Any]:
        return {
            "sessionId": "ecom-store",
            "status": self.session_status,
            "engine": "baileys",
            "phone": self.mock_phone,
            "pushName": self.mock_push_name,
            "active": self.session_status == "ready",
        }

    async def get_qr(self) -> dict[str, Any]:
        return {
            "sessionId": "ecom-store",
            "qrCode": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "expiresAt": "2026-11-17T12:00:00.000Z",
        }

    async def get_message_media(
        self,
        chat_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        return {
            "mimetype": "audio/ogg",
            "data": "T2dnUwACAAAAAAAAAABt",
        }

    def clear(self) -> None:
        self.sent_messages.clear()
