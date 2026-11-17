"""OpenWA Provider implementation communicating with upstream OpenWA REST API."""

import logging
from typing import Any

import httpx

from app.config import get_settings
from app.services.whatsapp.provider import SendResult, WhatsAppProvider

logger = logging.getLogger(__name__)


class OpenWaProvider(WhatsAppProvider):
    """Client for OpenWA upstream container gateway REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        session_id: str | None = None,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.OPENWA_BASE_URL).rstrip("/")
        self.session_id = session_id or settings.OPENWA_SESSION_ID
        self.api_key = api_key or settings.OPENWA_API_KEY
        self.timeout = timeout

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    async def send_text(
        self,
        chat_id: str,
        text: str,
        idempotency_key: str | None = None,
    ) -> SendResult:
        """Send a text message via OpenWA POST /api/sessions/:sessionId/messages/send-text."""
        url = f"{self.base_url}/api/sessions/{self.session_id}/messages/send-text"
        headers = self._headers(idempotency_key=idempotency_key)
        payload = {
            "chatId": chat_id,
            "text": text,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

            if response.status_code in (200, 201):
                data = response.json()
                msg_id = data.get("id") or data.get("messageId")
                logger.info("OpenWA message sent successfully to %s: %s", chat_id, msg_id)
                return SendResult(
                    success=True,
                    openwa_message_id=msg_id,
                    status=data.get("status", "sent"),
                    raw_response=data,
                )

            err_text = response.text
            logger.warning(
                "OpenWA send_text returned status %d for %s: %s",
                response.status_code,
                chat_id,
                err_text,
            )
            return SendResult(
                success=False,
                error=f"HTTP {response.status_code}: {err_text}",
            )

        except Exception as exc:
            logger.error("OpenWA send_text error for %s: %s", chat_id, str(exc))
            return SendResult(
                success=False,
                error=str(exc),
            )

    async def get_message_media(
        self,
        chat_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """Download a message's stored media via GET /api/sessions/:sessionId/messages/:chatId/:messageId/media.
        
        Returns a dict: {"mimetype": str, "data": str (base64)} or {"error": str}.
        """
        import base64
        url = f"{self.base_url}/api/sessions/{self.session_id}/messages/{chat_id}/{message_id}/media"
        headers = self._headers()

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 200:
                mimetype = response.headers.get("content-type", "audio/ogg").split(";")[0].strip()
                audio_b64 = base64.b64encode(response.content).decode("ascii")
                return {
                    "mimetype": mimetype,
                    "data": audio_b64,
                }

            logger.warning(
                "OpenWA get_message_media returned status %d for msg %s: %s",
                response.status_code,
                message_id,
                response.text,
            )
            return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as exc:
            logger.error("OpenWA get_message_media failed for msg %s: %s", message_id, str(exc))
            return {"error": str(exc)}

    async def get_session_status(self) -> dict[str, Any]:
        """Fetch session status via GET /api/sessions/:sessionId/status."""
        url = f"{self.base_url}/api/sessions/{self.session_id}/status"
        headers = self._headers()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()

            return {
                "status": "error",
                "error": f"HTTP {response.status_code}: {response.text}",
            }
        except Exception as exc:
            logger.error("OpenWA get_session_status failed: %s", str(exc))
            return {
                "status": "unreachable",
                "error": str(exc),
            }

    async def get_qr(self) -> dict[str, Any]:
        """Fetch pairing QR code via GET /api/sessions/:sessionId/qr."""
        url = f"{self.base_url}/api/sessions/{self.session_id}/qr"
        headers = self._headers()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()

            return {
                "status": "error",
                "error": f"HTTP {response.status_code}: {response.text}",
            }
        except Exception as exc:
            logger.error("OpenWA get_qr failed: %s", str(exc))
            return {
                "status": "unreachable",
                "error": str(exc),
            }
