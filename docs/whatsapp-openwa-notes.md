# OpenWA Upstream Integration Technical Notes

**Repository**: `https://github.com/rmyndharis/OpenWA` (MIT License)  
**Pinned Release Tag**: `v0.27.0` (Commit `d99fa201b`, released 2026-10-31, >2 weeks old)  
**Container Image**: `ghcr.io/rmyndharis/openwa:v0.27.0`  
**Default Engine**: `baileys` (lightweight WebAssembly/WebSocket stack; no headless Chromium overhead)  
**Default Port**: `2785` (bound to `127.0.0.1:2785` on host for pairing; internal network `http://openwa:2785`)

---

## 1. Verified REST Endpoints & Schemas

Source reference: `docs/06-api-specification.md` and `src/modules/session/session.controller.ts` in OpenWA `v0.27.0`.

### 1.1 Authentication & Header
- **Header**: `X-API-Key: <key>` (also supports `Authorization: Bearer <key>`)
- **Roles**:
  - `1`: `VIEWER` (read-only)
  - `2`: `OPERATOR` (send messages, manage webhooks, view QR)
  - `3`: `ADMIN` (create sessions, create API keys, configure infra)

### 1.2 Session Management
- **Create Session**:
  - `POST /api/sessions`
  - Auth: `ADMIN`
  - Body:
    ```json
    {
      "sessionId": "ecom-store",
      "engine": "baileys",
      "config": {
        "browser": {
          "name": "EComSupport",
          "platform": "Ubuntu"
        }
      }
    }
    ```
  - Response `201`: Session entity `{ "sessionId": "ecom-store", "status": "created", ... }`

- **Start Session**:
  - `POST /api/sessions/:sessionId/start`
  - Auth: `OPERATOR`
  - Response `200`: `{ "sessionId": "ecom-store", "status": "initializing" | "qr_ready" | "ready" }`

- **Session Status**:
  - `GET /api/sessions/:sessionId/status`
  - Auth: `OPERATOR`
  - Response `200`:
    ```json
    {
      "sessionId": "ecom-store",
      "status": "ready",
      "engine": "baileys",
      "phone": "919876543210",
      "pushName": "Store Support",
      "active": true
    }
    ```
  - Possible `status` values: `created`, `initializing`, `qr_ready`, `authenticating`, `ready`, `disconnected`, `action_required`, `failed`.

- **Session QR Code**:
  - `GET /api/sessions/:sessionId/qr`
  - Auth: `OPERATOR`
  - Response `200`:
    ```json
    {
      "sessionId": "ecom-store",
      "qrCode": "data:image/png;base64,iVBORw0KGgo...",
      "expiresAt": "2026-11-17T10:05:00.000Z"
    }
    ```
  - Note: Returned as a direct base64 PNG data URL suitable for `<img src="...">`.

### 1.3 Message Sending
- **Send Text Message**:
  - `POST /api/sessions/:sessionId/messages/send-text`
  - Auth: `OPERATOR`
  - Headers:
    - `X-API-Key: <key>`
    - `Idempotency-Key: <unique_key>` (supported natively in `src/modules/message/message.controller.ts`)
  - Body:
    ```json
    {
      "chatId": "919876543210@c.us",
      "text": "Your order #1001 status is: Shipped"
    }
    ```
  - Response `200` / `201`:
    ```json
    {
      "id": "3EB0ABC1234567890",
      "sessionId": "ecom-store",
      "chatId": "919876543210@c.us",
      "status": "sent",
      "timestamp": 1750000000
    }
    ```

### 1.4 Webhook Management
- **Register Webhook**:
  - `POST /api/sessions/:sessionId/webhooks`
  - Auth: `OPERATOR`
  - Body:
    ```json
    {
      "url": "http://ecom_backend:8000/whatsapp/openwa/webhook",
      "events": ["message.received", "message.ack", "session.status"],
      "secret": "your_secure_webhook_signing_secret_min16chars"
    }
    ```
  - Secret requirement: Min 16 characters (`src/modules/webhook/dto/create-webhook.dto.ts`).

### 1.5 Scoped API Key Provisioning
- **Create Operator Key**:
  - `POST /api/auth/api-keys`
  - Auth: `ADMIN` (`OPENWA_ADMIN_API_KEY`)
  - Body:
    ```json
    {
      "name": "ecom-backend-operator",
      "role": 2,
      "allowedSessions": ["ecom-store"]
    }
    ```
  - Response `201`: `{ "key": "wa_live_...", "name": "ecom-backend-operator", "role": 2, ... }`
  - The runtime backend only stores this operator key, never the admin key.

---

## 2. Webhook Delivery & Signature Verification

Source reference: `src/modules/webhook/utils/deliver-once.ts` (lines 51–85) & `docs/06-api-specification.md` (lines 7500–7538).

### 2.1 Request Headers
When OpenWA sends a webhook to the backend:
- `Content-Type`: `application/json`
- `User-Agent`: `OpenWA-Webhook/1.0.0`
- `X-OpenWA-Event`: Event name (`message.received`, `message.ack`, `session.status`)
- `X-OpenWA-Idempotency-Key`: Derived unique key (e.g. `msg_{sessionId}_{messageId}_{webhookId}`)
- `X-OpenWA-Delivery-Id`: Unique delivery UUID (`dlv_...`)
- `X-OpenWA-Retry-Count`: Number of retries (`0` for first attempt)
- `X-OpenWA-Signature`: `sha256=<hex_hmac>`

### 2.2 Signature Calculation & Verification
- **Signing Algorithm**: HMAC-SHA256
- **Signing Input**: The **raw unparsed JSON request body bytes** (not re-serialized JSON).
- **Format**: `sha256=${hmac.digest('hex')}`
- **Verification Rule**:
  - Backend must read `await request.body()` as raw bytes.
  - Calculate `hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()`.
  - Prefix with `sha256=` and use `hmac.compare_digest(header_val, expected_val)`.
  - Reject `401 Unauthorized` if signature is invalid or missing when a secret is configured.

### 2.3 Webhook Payload Envelope
```json
{
  "event": "message.received",
  "timestamp": "2026-11-17T06:55:00.000Z",
  "sessionId": "ecom-store",
  "idempotencyKey": "msg_ecom-store_3EB0...",
  "deliveryId": "dlv_550e8400...",
  "data": { ... }
}
```

### 2.4 Payload Shapes by Event
- **`message.received`**:
  ```json
  {
    "id": "3EB0ABC12345",
    "from": "919876543210@c.us",
    "to": "918000000000@c.us",
    "chatId": "919876543210@c.us",
    "body": "Where is my order #1001?",
    "type": "text",
    "timestamp": 1750000000,
    "isGroup": false,
    "fromMe": false,
    "kind": "individual",
    "senderPhone": "919876543210",
    "media": {
      "mimetype": "audio/ogg; codecs=opus",
      "data": "GkXfo59ChoEBQveBAULygQ8U...",
      "sizeBytes": 14200
    }
  }
  ```
  - Ignored inbound messages: `fromMe: true`, `isGroup: true`, `kind: "group" | "status" | "broadcast" | "channel"`.
- **`message.ack`**:
  ```json
  {
    "id": "3EB0ABC12345",
    "messageId": "3EB0ABC12345",
    "status": "delivered",
    "ack": 2,
    "chatId": "919876543210@c.us"
  }
  ```
  - `status` values: `pending`, `sent`, `delivered`, `read`, `failed`.
- **`session.status`**:
  ```json
  {
    "sessionId": "ecom-store",
    "status": "ready"
  }
  ```

---

## 3. Chat IDs & Privacy IDs (`@c.us` vs `@lid`)

Source reference: `docs/06-api-specification.md` (lines 7420–7430) and `src/modules/session/session-lid-resolver.service.ts`.
- Standard user chat ID: `<E.164-digits-without-+>@c.us` (e.g. `919876543210@c.us`).
- Privacy-masked ID: `<digits>@lid`.
- When `RESOLVE_LID_TO_PHONE=true` is set on OpenWA, OpenWA attaches `senderPhone` to `message.received`.
- We normalize all contact phone numbers into E.164 format `+<country><digits>` (e.g., `+919876543210`) for consistent database identity matching.

---

## 4. Rate Pacing & Engine Constraints

- OpenWA has daily send pacing (`SEND_PACING_ENABLED`), but short-burst throttling must be handled by the backend outbound worker.
- **Backend Pacing**:
  - Minimum delay between sends: `1500ms` with `50%` randomized jitter.
  - Maximum sends per minute: `15`.
  - Maximum sends per hour: `250`.
  - Reply-only rule: No outbound messages sent to a contact after 72 hours of customer silence unless customer messages again.

---

## 5. Media Handling
- Voice notes arrive with `type: "voice"` or `"audio"`, with `media.data` containing base64 audio payload (or URL if external storage configured).
- OpenWA sheds inline media if exceeding `WEBHOOK_MAX_PAYLOAD_BYTES` (default 5MB).
- Audio is validated for MIME type (`audio/ogg`, `audio/mp4`, `audio/webm`, `audio/wav`, `audio/mpeg`) and size limit (<= 2MB), passed in-memory to STT (`/voice/transcribe` or local whisper/vosk service), and discarded immediately after transcription without writing to disk.
