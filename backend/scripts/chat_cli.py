import argparse
import sys

import httpx


def run_cli():
    parser = argparse.ArgumentParser(description="Terminal Chat CLI for Multilingual E-Commerce Assistant")
    parser.add_argument("--customer-id", required=True, help="UUID of customer")
    parser.add_argument("--base-url", default="http://localhost:8000", help="FastAPI backend base URL")
    args = parser.parse_args()

    customer_id = args.customer_id
    base_url = args.base_url.rstrip("/")
    chat_url = f"{base_url}/chat"

    print("=" * 60)
    print("REGIONAL E-COMMERCE SUPPORT ASSISTANT - TERMINAL CLIENT")
    print(f"Base URL: {base_url}")
    print(f"Customer ID: {customer_id}")
    print("Type your message and press Enter. Type 'exit' or 'quit' to end.")
    print("=" * 60)

    session_id: str | None = None

    while True:
        try:
            user_input = input("\nYou > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat. Goodbye!")
            sys.exit(0)

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        payload = {
            "customer_id": customer_id,
            "session_id": session_id,
            "message": user_input,
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(chat_url, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                session_id = data.get("session_id")
                reply = data.get("reply", "")
                intent = data.get("intent", "unknown")
                language = data.get("language", "unknown")
                requires_human = data.get("requires_human", False)
                trace_id = data.get("trace_id", "")

                print(f"\nAssistant [{intent} | {language}] > {reply}")
                if requires_human:
                    print("  [HANDED TO HUMAN - Support executive has been notified]")
                print(f"  (Session: {session_id} | Trace: {trace_id})")
            else:
                print(f"\n[HTTP Error {resp.status_code}] {resp.text}")

        except httpx.RequestError as exc:
            print(f"\n[Network Error] Could not connect to {chat_url}: {exc}")


if __name__ == "__main__":
    run_cli()
