"""WhatsApp Voice Note Audio Validation and STT Transcription."""

import base64
import io
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class VoiceNoteError(Exception):
    pass


async def transcribe_voice_note(
    media: dict[str, Any],
) -> dict[str, Any]:
    """Transcribe an in-memory base64 WhatsApp voice note or audio file.

    Enforces:
    - MIME type whitelist (audio/ogg, audio/mp4, audio/webm, etc.)
    - Max byte size limit (VOICE_MAX_BYTES)
    - In-memory processing only (never written to disk)

    Returns:
        dict: {"text": str, "language": str, "confidence": float}
    """
    settings = get_settings()
    mimetype = media.get("mimetype", "").split(";")[0].strip().lower()
    allowed_mimes = settings.voice_allowed_mime_list

    if mimetype not in allowed_mimes and not any(m in mimetype for m in ("ogg", "opus", "mp4", "mpeg", "webm", "wav")):
        raise VoiceNoteError(f"Unsupported audio MIME type: {mimetype}")

    data_b64 = media.get("data")
    if not data_b64:
        raise VoiceNoteError("Missing audio media data")

    try:
        audio_bytes = base64.b64decode(data_b64)
    except Exception as exc:
        raise VoiceNoteError(f"Failed to base64-decode audio media: {exc}") from exc

    if len(audio_bytes) > settings.VOICE_MAX_BYTES:
        raise VoiceNoteError(f"Audio exceeds size limit ({len(audio_bytes)} > {settings.VOICE_MAX_BYTES} bytes)")

    if len(audio_bytes) < 100:
        raise VoiceNoteError("Audio payload is empty or too short")

    # Transcribe via configured provider
    provider = settings.STT_PROVIDER.lower()

    if provider == "fake":
        return {
            "text": "Where is my order ORD-10001?",
            "language": "en",
            "confidence": 0.95,
        }

    if provider == "groq" and settings.GROQ_API_KEY and settings.GROQ_API_KEY != "gsk_placeholder":
        try:
            filename = "audio.ogg" if "ogg" in mimetype or "opus" in mimetype else "audio.mp4"
            files = {
                "file": (filename, io.BytesIO(audio_bytes), mimetype or "audio/ogg"),
            }
            data = {
                "model": settings.STT_MODEL,
                "prompt": settings.STT_PROMPT_HINT,
            }
            if settings.STT_LANGUAGE_HINT and settings.STT_LANGUAGE_HINT != "auto":
                data["language"] = settings.STT_LANGUAGE_HINT

            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            }
            url = f"{settings.GROQ_BASE_URL.rstrip('/')}/audio/transcriptions"

            async with httpx.AsyncClient(timeout=25.0) as client:
                res = await client.post(url, headers=headers, files=files, data=data)

            if res.status_code == 200:
                body = res.json()
                text = body.get("text", "").strip()
                return {
                    "text": text,
                    "language": body.get("language", "auto"),
                    "confidence": 0.92,
                }
            logger.warning("Groq STT returned status %d: %s", res.status_code, res.text)
        except Exception as exc:
            logger.error("Groq STT transcription error: %s", exc)

    # Fallback response if external provider not configured or failed
    logger.info("Using fallback mock transcription for voice note")
    return {
        "text": "Audio voice note received. Please type your message if you need immediate assistance.",
        "language": "en",
        "confidence": 0.70,
    }
