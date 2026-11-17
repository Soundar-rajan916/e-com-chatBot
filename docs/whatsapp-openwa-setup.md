# WhatsApp OpenWA Channel Integration & Real-Device Setup Guide

This document describes how to deploy, configure, pair, and operate the WhatsApp integration in the Multilingual Regional E-Commerce Support Assistant using the containerized OpenWA upstream gateway (`ghcr.io/rmyndharis/openwa:v0.27.0`).

---

## 1. Operational Risk Statement

> **IMPORTANT RISK STATEMENT**:  
> `open-wa` is an unofficial WhatsApp Web automation gateway. WhatsApp may ban or restrict numbers that use unofficial clients, and WhatsApp Web protocol changes can break automation without advance notice.  
> - **Use a DEDICATED phone number** that is not critical to personal or business operations.  
> - **Reply-Only Policy**: Only reply to customers who message the store first. Never send bulk, unsolicited, or promotional broadcast messages.  
> - **72-Hour Reply Guard**: The system will automatically refuse outbound messages to contacts who have been inactive for more than 72 hours until the contact messages again.  
> - **Production Upgrade Path**: Keep the official WhatsApp Business Cloud API as the documented enterprise upgrade path (the provider interface abstraction `WhatsAppProvider` makes this an in-place swap).

---

## 2. Architecture & Components

```
[Customer on WhatsApp]
       ▲
       │ WhatsApp Web Protocol
       ▼
[OpenWA Upstream Service] (ghcr.io/rmyndharis/openwa:v0.27.0, engine: baileys)
       ▲
       │ REST API (POST /api/sessions/:id/messages/send-text) with X-API-Key
       │ Webhooks (POST /whatsapp/openwa/webhook) with X-OpenWA-Signature (HMAC-SHA256)
       ▼
[FastAPI Backend]
  ├─ Webhook Ingress: immediate 200 ACK + deduplication
  ├─ Database: postgresql (whatsapp_contacts, whatsapp_outbound, whatsapp_inbound_events)
  ├─ Inbound Worker: pg_advisory_xact_lock serialization per contact, typed confirmations
  ├─ Outbound Worker: 1500ms delay + 50% random jitter, 72h reply window guard
  └─ Chat Pipeline: channel-agnostic multilingual AI assistance (EN, TA, Tanglish)
```

---

## 3. Configuration Variables (`.env`)

Add the following environment variables to `backend/.env`:

```env
# Enable WhatsApp Channel
WHATSAPP_ENABLED=true

# Upstream OpenWA Gateway
OPENWA_BASE_URL=http://openwa:2785
OPENWA_SESSION_ID=ecom-store

# Operator-scoped key for backend runtime
OPENWA_API_KEY=wa_live_default_operator_key

# Webhook signing secret (minimum 16 characters)
OPENWA_WEBHOOK_SECRET=openwa_dev_secure_webhook_secret_key_16chars

# Admin key (used solely by one-time setup script; not stored in app runtime)
OPENWA_ADMIN_API_KEY=admin_secret_key_change_me

# Storefront WhatsApp Support Number (E.164 format)
WHATSAPP_PHONE_NUMBER=+919876543210

# Pacing & Safety Limits
WHATSAPP_REPLY_ONLY_HOURS=72
WHATSAPP_OUTBOUND_MIN_DELAY_MS=1500
WHATSAPP_OUTBOUND_MAX_PER_MINUTE=15
WHATSAPP_OUTBOUND_MAX_PER_HOUR=250
WHATSAPP_LINK_CODE_EXPIRE_MINUTES=10
WHATSAPP_CONFIRMATION_EXPIRE_MINUTES=15
```

---

## 4. Setup & Real-Device Pairing Checklist

### Step 1: Start the Stack with OpenWA
To run with upstream OpenWA:
```powershell
docker compose up -d
```

*(For fast offline development / CI without pulling the OpenWA image, run with the fake simulator:)*
```powershell
docker compose -f docker-compose.yml -f docker-compose.fake-whatsapp.yml up -d
```

### Step 2: Run One-Time Idempotent Setup
Execute the setup script inside the backend container or locally:
```powershell
docker exec ecom_backend python -m scripts.openwa_setup
```
This script will:
1. Verify connectivity with OpenWA.
2. Create session `ecom-store` with engine `baileys`.
3. Start the session.
4. Provision an operator-scoped API key.
5. Register the backend webhook with HMAC-SHA256 signature secret.

### Step 3: Scan QR Code with Real Device
1. Open the OpenWA Web Dashboard at:
   ```
   http://localhost:2785
   ```
   *(Or navigate to the Staff Console at `http://localhost:5173/console/whatsapp`)*
2. On your dedicated WhatsApp test phone:
   - Open **WhatsApp**
   - Tap **Settings** (or top-right three dots on Android)
   - Tap **Linked Devices**
   - Tap **Link a Device**
3. Scan the QR code displayed on the screen.
4. Within 3-5 seconds, the status will transition from `qr_ready` to `ready`.

---

## 5. End-to-End Smoke Verification

To verify that the entire integration works cleanly (webhook HMAC signatures, deduplication, opt-out/in, account linking, typed refund confirmations, and rate pacing), run:

```powershell
docker exec ecom_backend python -m scripts.smoke_whatsapp
```

Expected output:
```
================================================================
🚀 WhatsApp Integration End-to-End Smoke Verification
================================================================
✅ 1. Backend service is healthy and reachable.
✅ 2. Webhook rejected invalid HMAC signature with 401 Unauthorized.
✅ 3. Webhook accepted valid HMAC signature with immediate 200 OK.
✅ 4. Webhook ingress deduplication caught identical deliveryId/idempotencyKey.
✅ 5. Inbound worker processed pending event(s) under advisory locking.
✅ 6. WhatsApp contact created and phone normalized.
✅ 7. Inbound 'STOP' opt-out command marked contact.opted_out = True.
✅ 8. Inbound 'START' command resumed opt-in status.
✅ 9. Customer successfully linked to WhatsAppContact via 'LINK <code>'.
✅ 10. Outbound worker delivered rate-paced response(s) via provider.
================================================================
🎉 ALL 10 SMOKE VERIFICATION CHECKS PASSED WITH 100% SUCCESS!
================================================================
```

---

## 6. Staff Console & Dev Simulator

- **Staff Console**: Open `http://localhost:5173/console/whatsapp` to view connection status, device pairing QR, heartbeat, risk statement, and pause/resume controls.
- **Customer Storefront**: Under `http://localhost:5173/account`, customers can generate a 6-digit link code with a live countdown and click **Open in WhatsApp** to pair their account.
- **Dev Simulator**: Open `http://localhost:5173/dev/whatsapp` to interact with an emulated WhatsApp phone UI and test commands (`LINK`, `YES`, `STOP`, `START`, and queries).
