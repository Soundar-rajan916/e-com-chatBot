"""Lightweight OpenWA Gateway Simulator for Development and Automated Tests."""

import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fake_openwa")

app = FastAPI(title="Fake OpenWA Gateway Simulator", version="0.27.0")

# In-memory simulator datastores
sessions: dict[str, dict[str, Any]] = {
    "ecom-store": {
        "sessionId": "ecom-store",
        "engine": "baileys",
        "status": "ready",
        "phone": "919876543210",
        "pushName": "Store Support",
        "active": True,
    }
}
webhooks: dict[str, list[dict[str, Any]]] = {}
sent_messages: list[dict[str, Any]] = []
api_keys: dict[str, dict[str, Any]] = {
    "wa_live_fake_operator_key": {
        "key": "wa_live_fake_operator_key",
        "name": "ecom-backend-operator",
        "role": 2,
        "allowedSessions": ["ecom-store"],
    }
}


class CreateSessionRequest(BaseModel):
    sessionId: str
    engine: str = "baileys"
    config: dict[str, Any] = Field(default_factory=dict)


class SendTextRequest(BaseModel):
    chatId: str
    text: str


class CreateWebhookRequest(BaseModel):
    url: str
    events: list[str] = Field(default_factory=lambda: ["message.received", "message.ack", "session.status"])
    secret: str | None = None


class CreateApiKeyRequest(BaseModel):
    name: str
    role: int = 2
    allowedSessions: list[str] = Field(default_factory=list)


# =========================================================================
# OpenWA Emulated REST Routes
# =========================================================================


@app.get("/api/sessions")
async def list_sessions():
    return list(sessions.values())


@app.post("/api/sessions", status_code=201)
async def create_session(req: CreateSessionRequest):
    if req.sessionId in sessions:
        raise HTTPException(status_code=409, detail="Session already exists")
    sess = {
        "sessionId": req.sessionId,
        "engine": req.engine,
        "status": "created",
        "phone": None,
        "pushName": None,
        "active": False,
    }
    sessions[req.sessionId] = sess
    return sess


@app.post("/api/sessions/{session_id}/start")
async def start_session(session_id: str):
    sess = sessions.get(session_id)
    if not sess:
        sess = {
            "sessionId": session_id,
            "engine": "baileys",
            "status": "ready",
            "phone": "919876543210",
            "pushName": "Store Support",
            "active": True,
        }
        sessions[session_id] = sess
    else:
        sess["status"] = "ready"
        sess["active"] = True
        sess["phone"] = sess.get("phone") or "919876543210"
        sess["pushName"] = sess.get("pushName") or "Store Support"
    return sess


@app.get("/api/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    sess = sessions.get(session_id)
    if not sess:
        return {"sessionId": session_id, "status": "disconnected", "active": False}
    return sess


@app.get("/api/sessions/{session_id}/qr")
async def get_session_qr(session_id: str):
    return {
        "sessionId": session_id,
        "qrCode": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "expiresAt": "2026-11-17T12:00:00.000Z",
    }


@app.post("/api/sessions/{session_id}/messages/send-text", status_code=201)
async def send_text_message(
    session_id: str,
    req: SendTextRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    msg_id = f"openwa_msg_{uuid.uuid4().hex[:12]}"
    record = {
        "id": msg_id,
        "sessionId": session_id,
        "chatId": req.chatId,
        "text": req.text,
        "idempotencyKey": idempotency_key,
        "status": "sent",
        "timestamp": int(time.time()),
    }
    sent_messages.append(record)
    logger.info("FakeOpenWA sent text to %s: %s (msgId=%s)", req.chatId, req.text[:40], msg_id)
    return record


@app.post("/api/sessions/{session_id}/webhooks", status_code=201)
async def register_webhook(session_id: str, req: CreateWebhookRequest):
    wh_list = webhooks.setdefault(session_id, [])
    wh = {
        "id": f"wh_{uuid.uuid4().hex[:8]}",
        "sessionId": session_id,
        "url": req.url,
        "events": req.events,
        "secret": req.secret,
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    wh_list.append(wh)
    logger.info("Registered webhook for %s: %s", session_id, req.url)
    return wh


@app.post("/api/auth/api-keys", status_code=201)
async def create_api_key(req: CreateApiKeyRequest):
    key_val = f"wa_live_{uuid.uuid4().hex}"
    key_obj = {
        "key": key_val,
        "name": req.name,
        "role": req.role,
        "allowedSessions": req.allowedSessions,
    }
    api_keys[key_val] = key_obj
    return key_obj


# =========================================================================
# Simulator Trigger Routes
# =========================================================================


class FireMessageRequest(BaseModel):
    sessionId: str = "ecom-store"
    chatId: str = "919876543210@c.us"
    body: str
    senderPhone: str | None = "919876543210"
    type: str = "text"
    media: dict[str, Any] | None = None


@app.post("/simulator/fire-message")
async def simulator_fire_message(req: FireMessageRequest):
    """Fire a simulated message.received webhook delivery with HMAC signature."""
    wh_list = webhooks.get(req.sessionId, [])
    if not wh_list:
        # Default fallback webhook
        wh_list = [{"url": "http://ecom_backend:8000/whatsapp/openwa/webhook", "secret": "openwa_dev_secure_webhook_secret_key_16chars"}]

    msg_id = f"in_msg_{uuid.uuid4().hex[:12]}"
    delivery_id = f"dlv_{uuid.uuid4().hex}"
    idempotency_key = f"msg_{req.sessionId}_{msg_id}"

    payload = {
        "event": "message.received",
        "sessionId": req.sessionId,
        "idempotencyKey": idempotency_key,
        "deliveryId": delivery_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "data": {
            "id": msg_id,
            "from": req.chatId,
            "to": "918000000000@c.us",
            "chatId": req.chatId,
            "body": req.body,
            "type": req.type,
            "fromMe": False,
            "isGroup": False,
            "kind": "individual",
            "senderPhone": req.senderPhone,
            "media": req.media,
            "timestamp": int(time.time()),
        },
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    results = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        for wh in wh_list:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "OpenWA-Webhook/1.0.0",
                "X-OpenWA-Event": "message.received",
                "X-OpenWA-Idempotency-Key": idempotency_key,
                "X-OpenWA-Delivery-Id": delivery_id,
                "X-OpenWA-Retry-Count": "0",
            }
            secret = wh.get("secret")
            if secret:
                sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
                headers["X-OpenWA-Signature"] = f"sha256={sig}"

            try:
                res = await client.post(wh["url"], content=body_bytes, headers=headers)
                results.append({"url": wh["url"], "status": res.status_code, "response": res.text})
            except Exception as e:
                results.append({"url": wh["url"], "error": str(e)})

    return {"dispatched": len(results), "results": results, "payload": payload}


@app.get("/simulator/sent-messages")
async def get_sent_messages():
    return {"count": len(sent_messages), "messages": sent_messages}


@app.delete("/simulator/sent-messages")
async def clear_sent_messages():
    sent_messages.clear()
    return {"status": "cleared"}
