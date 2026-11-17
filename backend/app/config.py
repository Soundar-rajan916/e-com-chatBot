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
    CHEAP_GENERATOR_MODEL: str = "openai/gpt-oss-20b"

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

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Phase 2 RAG & Vector Configurations
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-small"
    EMBEDDING_DIM: int = 384
    VECTOR_BACKEND: str = "numpy"  # "pgvector" | "numpy"
    RAG_TOP_K: int = 4
    RAG_MIN_SCORE: float = 0.82
    PRODUCT_SEARCH_CANDIDATES: int = 20
    EMBEDDING_QUERY_PREFIX: str = "query: "
    EMBEDDING_PASSAGE_PREFIX: str = "passage: "

    # Phase 3 Part A: Admin & Escalations
    ADMIN_SESSION_HOURS: int = 8
    ESCALATION_SLA_MINUTES: int = 15
    ADMIN_COOKIE_NAME: str = "admin_session"

    # Phase 3 Part B: Budget Governor & Load Control
    REDIS_URL: str = "redis://localhost:6379/0"
    MONTHLY_BUDGET_INR: Decimal = Decimal("50000.00")
    BUDGET_TIMEZONE: str = "Asia/Kolkata"
    MODE_SAVER_AT_PCT: float = 70.0
    MODE_CRITICAL_AT_PCT: float = 90.0
    MODE_EXHAUSTED_AT_PCT: float = 100.0
    RESERVE_PCT: float = 5.0
    DAILY_PACING_BURST_FACTOR: float = 3.0
    CACHE_TTL_SECONDS: int = 86400
    CACHE_ENABLED: bool = True
    RATE_LIMIT_PER_CUSTOMER_PER_MIN: int = 12
    RATE_LIMIT_PER_IP_PER_MIN: int = 60
    GLOBAL_LLM_CONCURRENCY: int = 16
    QUEUE_WAIT_MS: int = 2000
    TRUSTED_PROXY: bool = False
    ESTIMATE_TOKENS_ROUTER_IN: int = 350
    ESTIMATE_TOKENS_ROUTER_OUT: int = 80
    ESTIMATE_TOKENS_GENERATOR_IN: int = 800
    ESTIMATE_TOKENS_GENERATOR_OUT: int = 250
    LLM_MODE: str = "live"  # "live" | "simulated"
    SIM_LATENCY_MS_ROUTER: int = 30
    SIM_LATENCY_MS_GENERATOR: int = 60
    SIM_TOKENS_ROUTER_IN: int = 300
    SIM_TOKENS_ROUTER_OUT: int = 60
    SIM_TOKENS_GENERATOR_IN: int = 700
    SIM_TOKENS_GENERATOR_OUT: int = 200

    # Phase 3 Part C: Voice Notes / STT
    STT_PROVIDER: str = "groq"  # "groq" | "sarvam" | "fake"
    STT_MODEL: str = "whisper-large-v3-turbo"
    STT_LANGUAGE_HINT: str = "auto"
    STT_PROMPT_HINT: str = (
        "Multilingual Indian regional e-commerce store. Customer inquiries in Tamil, English, and Tanglish. "
        "Terms: order, refund, cancel, return, ORD, saree, kurti, delivery, UPI."
    )
    VOICE_MAX_SECONDS: int = 60
    VOICE_MAX_BYTES: int = 3000000
    VOICE_ALLOWED_MIME: str = "audio/webm,audio/ogg,audio/mp4,audio/mpeg,audio/wav"
    VOICE_MIN_CONFIDENCE: float = 0.50
    VOICE_STORE_AUDIO: bool = False
    STT_PRICE_PER_MINUTE_USD: Decimal = Decimal("0.006")
    VOICE_RATE_LIMIT_PER_CUSTOMER_PER_MIN: int = 6
    VOICE_AUTO_SEND: bool = False
    SARVAM_API_KEY: str | None = None
    SARVAM_BASE_URL: str = "https://api.sarvam.ai"

    # Phase 4: E-Commerce Storefront
    SHOP_COOKIE_NAME: str = "shop_session"
    SHOP_SESSION_MAX_AGE_DAYS: int = 14
    ANON_COOKIE_NAME: str = "support_anon"
    CUSTOMER_LOCKOUT_ATTEMPTS: int = 5
    CUSTOMER_LOCKOUT_MINUTES: int = 15
    STORE_NAME: str = "Regional E-Commerce Store"
    ALLOW_CLIENT_CUSTOMER_ID: bool = True
    PRODUCT_SEARCH_EMBED_TIMEOUT_MS: int = 1500

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def voice_allowed_mime_list(self) -> list[str]:
        return [mime.strip().lower() for mime in self.VOICE_ALLOWED_MIME.split(",") if mime.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
