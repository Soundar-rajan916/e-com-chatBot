from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, get_settings
from app.db import get_session
from app.main import create_app
from app.models import Base
from app.services.llm import GroqLLMClient, LLMResponse


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    settings = get_settings()
    engine = create_async_engine(
        settings.TEST_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=pool.NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session


class FakeGroqClient(GroqLLMClient):
    """Configurable scriptable fake Groq client for deterministic testing."""

    def __init__(self, settings: Settings | None = None):
        super().__init__(settings or get_settings())
        self.call_history: list[dict[str, Any]] = []
        self.router_responses: list[Any] = []
        self.generator_responses: list[Any] = []
        self.fail_all = False

    def enqueue_router(self, content_or_exc: Any):
        self.router_responses.append(content_or_exc)

    def enqueue_generator(self, content_or_exc: Any):
        self.generator_responses.append(content_or_exc)

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.1,
        response_format: dict[str, str] | None = None,
    ) -> LLMResponse:
        self.call_history.append(
            {
                "model": model,
                "messages": messages,
                "response_format": response_format,
            }
        )

        if self.fail_all:
            raise RuntimeError("Fake Groq network failure")

        is_router = model == self.settings.ROUTER_MODEL
        queue = self.router_responses if is_router else self.generator_responses

        if queue:
            next_resp = queue.pop(0)
            if isinstance(next_resp, Exception):
                raise next_resp
            content = next_resp
        else:
            if is_router:
                content = (
                    '{"intent": "smalltalk", "language": "en", "order_number": null, "refund_reason": null}'
                )
            else:
                content = "Hello! How can I assist you with your orders today?"

        cost = self._calculate_cost(model, 100, 50)
        return LLMResponse(
            content=content,
            model=model,
            prompt_tokens=100,
            completion_tokens=50,
            cost_inr=cost,
            latency_ms=15,
        )


@pytest.fixture
def fake_groq():
    return FakeGroqClient()


@pytest_asyncio.fixture(scope="function")
async def client(test_engine, fake_groq, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async def override_get_session():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session

    # In chat endpoint, handle_message uses llm_client; monkeypatch to return fake_groq
    monkeypatch.setattr("app.services.pipeline.GroqLLMClient", lambda *args, **kwargs: fake_groq)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
