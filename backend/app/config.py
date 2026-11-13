from decimal import Decimal
from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "dev"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ecom_dev"
    TEST_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ecom_test"

    GROQ_API_KEY: str = Field(default="gsk_placeholder")
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    ROUTER_MODEL: str = "openai/gpt-oss-20b"
    GENERATOR_MODEL: str = "openai/gpt-oss-120b"

    LLM_TIMEOUT_SECONDS: float = 20.0
    LLM_MAX_RETRIES: int = 2

    REFUND_AUTO_APPROVE_LIMIT_INR: Decimal = Decimal("2000.00")
    RETURN_WINDOW_DAYS: int = 7

    PRICE_PER_1M_INPUT_TOKENS_USD_ROUTER: Decimal = Decimal("0.05")
    PRICE_PER_1M_OUTPUT_TOKENS_USD_ROUTER: Decimal = Decimal("0.08")
    PRICE_PER_1M_INPUT_TOKENS_USD_GENERATOR: Decimal = Decimal("0.59")
    PRICE_PER_1M_OUTPUT_TOKENS_USD_GENERATOR: Decimal = Decimal("0.79")
    USD_INR_RATE: Decimal = Decimal("84.0")

    MAX_MESSAGE_CHARS: int = 1000
    HISTORY_TURNS: int = 6

    CORS_ORIGINS: str = "http://localhost:5173"

    # Phase 2 RAG & Vector Configurations
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-small"
    EMBEDDING_DIM: int = 384
    VECTOR_BACKEND: str = "numpy"  # "pgvector" | "numpy"
    RAG_TOP_K: int = 4
    RAG_MIN_SCORE: float = 0.82
    PRODUCT_SEARCH_CANDIDATES: int = 20
    EMBEDDING_QUERY_PREFIX: str = "query: "
    EMBEDDING_PASSAGE_PREFIX: str = "passage: "

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
