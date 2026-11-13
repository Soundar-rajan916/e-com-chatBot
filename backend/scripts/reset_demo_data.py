import asyncio
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import async_session_factory, engine
from app.models import ChatMessage, ChatSession, Escalation, Refund, Trace
from scripts.seed import seed_data


async def reset_demo_data() -> None:
    print("Resetting demo transaction and chat data...")
    async with async_session_factory() as session:
        for model in [Trace, ChatMessage, ChatSession, Escalation, Refund]:
            await session.execute(model.__table__.delete())
        await session.commit()
        print("Truncated traces, chat_messages, chat_sessions, escalations, refunds.")

        # Re-seed demo customers and orders cleanly
        await seed_data(session)

    await engine.dispose()
    print("Demo data reset complete.")


if __name__ == "__main__":
    asyncio.run(reset_demo_data())
