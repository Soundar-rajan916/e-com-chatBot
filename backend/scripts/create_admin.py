import argparse
import asyncio
import getpass
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.auth.security import hash_password
from app.db import async_session_factory
from app.models import Agent


async def create_or_update_agent(email: str, name: str, role: str, password: str | None = None) -> None:
    email_clean = email.strip().lower()
    if not email_clean or "@" not in email_clean:
        print("Error: Invalid email address.")
        sys.exit(1)

    if role not in ("admin", "agent"):
        print("Error: Role must be either 'admin' or 'agent'.")
        sys.exit(1)

    if password is None:
        p1 = getpass.getpass("Enter password (min 10 characters): ")
        if len(p1) < 10:
            print("Error: Password must be at least 10 characters long.")
            sys.exit(1)
        p2 = getpass.getpass("Confirm password: ")
        if p1 != p2:
            print("Error: Passwords do not match.")
            sys.exit(1)
        password = p1
    elif len(password) < 10:
        print("Error: Password must be at least 10 characters long.")
        sys.exit(1)

    hashed = hash_password(password)

    async with async_session_factory() as session:
        result = await session.execute(select(Agent).where(Agent.email == email_clean))
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = name
            existing.role = role
            existing.password_hash = hashed
            existing.is_active = True
            existing.failed_attempts = 0
            existing.locked_until = None
            await session.commit()
            print(f"Updated existing agent: {email_clean} (role={role})")
        else:
            new_agent = Agent(
                email=email_clean,
                name=name,
                password_hash=hashed,
                role=role,
                is_active=True,
            )
            session.add(new_agent)
            await session.commit()
            print(f"Created new agent: {email_clean} (role={role})")


def main():
    parser = argparse.ArgumentParser(description="Create or update an admin/agent account.")
    parser.add_argument("--email", required=True, help="Agent email address")
    parser.add_argument("--name", required=True, help="Agent full name")
    parser.add_argument("--role", default="admin", choices=["admin", "agent"], help="Agent role")
    parser.add_argument("--password", help="Optional password argument (prompts if omitted)")

    args = parser.parse_args()
    asyncio.run(create_or_update_agent(args.email, args.name, args.role, args.password))


if __name__ == "__main__":
    main()
