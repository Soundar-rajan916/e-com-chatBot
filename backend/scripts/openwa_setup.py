"""OpenWA Upstream Gateway One-Time Idempotent Setup Script.

Usage:
    python -m scripts.openwa_setup [--base-url http://localhost:2785] [--admin-key KEY]

Performs:
1. Connects to OpenWA gateway.
2. Creates session (engine=baileys) if missing.
3. Starts the session.
4. Generates an OPERATOR API key scoped to the session (if not already set).
5. Registers the backend webhook with HMAC-SHA256 signing secret.
6. Displays session connection status and QR code link.
"""

import argparse
import asyncio
import os
import sys

import httpx

from app.config import get_settings


async def setup_openwa(
    base_url: str,
    admin_key: str | None,
    session_id: str,
    webhook_url: str,
    webhook_secret: str,
) -> None:
    print(f"=== OpenWA Setup for Session: {session_id} ===")
    print(f"Gateway URL: {base_url}")
    print(f"Webhook URL: {webhook_url}")

    admin_headers = {"Content-Type": "application/json"}
    if admin_key:
        admin_headers["X-API-Key"] = admin_key

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Health / Connection Check
        try:
            res = await client.get(f"{base_url}/api/sessions", headers=admin_headers)
        except Exception as exc:
            print(f"\n[ERROR] Could not connect to OpenWA at {base_url}: {exc}")
            print("Please ensure the OpenWA container or fake simulator is running.")
            sys.exit(1)

        if res.status_code == 401:
            print("\n[ERROR] 401 Unauthorized from OpenWA. OPENWA_ADMIN_API_KEY is missing or invalid.")
            sys.exit(1)

        sessions = res.json() if res.status_code == 200 else []
        matched_session = next(
            (s for s in sessions if isinstance(s, dict) and (s.get("name") == session_id or s.get("id") == session_id or s.get("sessionId") == session_id)),
            None
        )

        target_session_id = session_id
        if matched_session:
            target_session_id = matched_session.get("id") or matched_session.get("sessionId") or session_id
            print(f"[1/4] Session '{session_id}' found (UUID: {target_session_id}).")
        else:
            print(f"[1/4] Creating session '{session_id}'...")
            create_payload = {
                "name": session_id,
            }
            res = await client.post(
                f"{base_url}/api/sessions",
                json=create_payload,
                headers=admin_headers,
            )
            if res.status_code in (200, 201):
                created_data = res.json()
                target_session_id = created_data.get("id") or session_id
                print(f"  -> Session '{session_id}' created successfully (UUID: {target_session_id}).")
            elif res.status_code == 409:
                print(f"  -> Session '{session_id}' already exists.")
            else:
                print(f"  [WARN] Failed to create session ({res.status_code}): {res.text}")

        # 3. Start Session
        print(f"[2/4] Starting session '{session_id}' (ID: {target_session_id})...")
        res = await client.post(
            f"{base_url}/api/sessions/{target_session_id}/start",
            headers=admin_headers,
        )
        if res.status_code in (200, 201):
            print(f"  -> Session '{session_id}' start triggered.")
        else:
            print(f"  -> Start response: {res.status_code} ({res.text})")

        # 4. Provision Operator API Key
        operator_key = os.environ.get("OPENWA_API_KEY")
        if not operator_key:
            print("[3/4] Provisioning scoped Operator API Key...")
            key_payload = {
                "name": f"ecom-backend-{session_id}",
                "role": 2,  # Role 2 = OPERATOR
                "allowedSessions": [target_session_id],
            }
            res = await client.post(
                f"{base_url}/api/auth/api-keys",
                json=key_payload,
                headers=admin_headers,
            )
            if res.status_code in (200, 201):
                data = res.json()
                operator_key = data.get("key") or data.get("apiKey")
                print(f"  -> Operator Key created: {operator_key}")
            else:
                print(f"  [WARN] Could not create operator key ({res.status_code}): {res.text}")
                print("  Using admin key or existing OPENWA_API_KEY.")
                operator_key = admin_key or "wa_operator_key_default"
        else:
            print(f"[3/4] Using existing OPENWA_API_KEY from environment.")

        # 5. Register Webhook
        print(f"[4/4] Registering webhook for '{session_id}' (ID: {target_session_id})...")
        operator_headers = {
            "Content-Type": "application/json",
            "X-API-Key": operator_key or admin_key or "",
        }
        # Avoid hostnames with underscores for validator.js compliance in OpenWA
        clean_webhook_url = webhook_url.replace("ecom_backend", "backend")
        webhook_payload = {
            "url": clean_webhook_url,
            "events": ["message.received", "message.ack", "session.status"],
            "secret": webhook_secret,
        }
        res = await client.post(
            f"{base_url}/api/sessions/{target_session_id}/webhooks",
            json=webhook_payload,
            headers=operator_headers,
        )
        if res.status_code in (200, 201):
            print("  -> Webhook registered successfully with HMAC-SHA256 secret.")
        elif res.status_code == 409:
            print("  -> Webhook already registered.")
        else:
            print(f"  [WARN] Webhook registration response ({res.status_code}): {res.text}")

        # 6. Check Current Status and QR
        print("\n=== Current Session Status ===")
        res = await client.get(
            f"{base_url}/api/sessions/{target_session_id}/status",
            headers=operator_headers,
        )
        status_info = res.json() if res.status_code == 200 else {}
        curr_status = status_info.get("status", "unknown")
        print(f"Status: {curr_status}")
        print(f"Phone: {status_info.get('phone', 'Not paired yet')}")

        if curr_status != "ready":
            print("\nPairing required! OpenWA web dashboard is accessible at:")
            print(f"  -> http://localhost:2785")
            print("Open the dashboard in your browser and scan the pairing QR code with your WhatsApp app.")

        print("\n=== Configuration Snippet (.env) ===")
        print(f"WHATSAPP_ENABLED=true")
        print(f"OPENWA_BASE_URL={base_url}")
        print(f"OPENWA_SESSION_ID={session_id}")
        if operator_key:
            print(f"OPENWA_API_KEY={operator_key}")
        print(f"OPENWA_WEBHOOK_SECRET={webhook_secret}")
        print("===================================\n")


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="OpenWA Gateway Setup")
    parser.add_argument("--base-url", default=settings.OPENWA_BASE_URL)
    parser.add_argument("--admin-key", default=settings.OPENWA_ADMIN_API_KEY or os.environ.get("OPENWA_ADMIN_API_KEY"))
    parser.add_argument("--session-id", default=settings.OPENWA_SESSION_ID)
    parser.add_argument(
        "--webhook-url",
        default="http://ecom_backend:8000/whatsapp/openwa/webhook",
    )
    parser.add_argument(
        "--webhook-secret",
        default=settings.OPENWA_WEBHOOK_SECRET or "openwa_dev_secure_webhook_secret_key_16chars",
    )
    args = parser.parse_args()

    asyncio.run(
        setup_openwa(
            base_url=args.base_url,
            admin_key=args.admin_key,
            session_id=args.session_id,
            webhook_url=args.webhook_url,
            webhook_secret=args.webhook_secret,
        )
    )


if __name__ == "__main__":
    main()
