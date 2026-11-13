from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    customer_id: UUID
    session_id: UUID | None = None
    message: str = Field(..., min_length=1)
    input_mode: str = Field(default="text")


class SourceItem(BaseModel):
    type: Literal["policy", "product"]
    id: str
    title: str


# ============================================================================
# Structured Output Data Models
# ============================================================================


class OrderItemSummary(BaseModel):
    product_title: str
    quantity: int = 1
    unit_price_inr: Decimal | float = 0.0


class OrderSummary(BaseModel):
    order_number: str
    status: str
    total_amount_inr: Decimal | float = 0.0
    placed_at: str | None = None
    delivered_at: str | None = None
    estimated_delivery: str | None = None
    items: list[OrderItemSummary] = Field(default_factory=list)


class OrderStatusData(BaseModel):
    single_order: OrderSummary | None = None
    multiple_orders: list[OrderSummary] = Field(default_factory=list)
    missing_order_number: bool = False
    not_found: bool = False


class RefundData(BaseModel):
    order_number: str | None = None
    refund_id: str | None = None
    status: str | None = None
    amount_inr: Decimal | float | None = None
    auto_approved: bool = False
    reason: str | None = None
    resolution_notes: str | None = None


class PolicyData(BaseModel):
    topic: str | None = None
    matched_sections: list[str] = Field(default_factory=list)
    key_rules: list[str] = Field(default_factory=list)


class ProductCard(BaseModel):
    id: str
    title: str
    category: str | None = None
    price_inr: Decimal | float = 0.0
    in_stock: bool = True
    stock_qty: int | None = None
    rating: float | None = None


class ProductListData(BaseModel):
    products: list[ProductCard] = Field(default_factory=list)
    total_found: int = 0
    search_query: str | None = None


class EscalationData(BaseModel):
    ticket_id: str | None = None
    reason: str | None = None
    agent_status: str | None = None
    callback_window: str | None = None


class SmalltalkData(BaseModel):
    greeting_type: str | None = None
    suggested_topics: list[str] = Field(default_factory=list)


class StructuredGeneratorOutput(BaseModel):
    headline: str | None = None
    reply: str
    suggested_actions: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# API Response Models
# ============================================================================


class ChatResponse(BaseModel):
    session_id: UUID
    reply: str
    intent: str
    language: str
    requires_human: bool
    trace_id: UUID
    sources: list[SourceItem] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    structured_output: StructuredGeneratorOutput | None = None


class RouterOutput(BaseModel):
    intent: Literal[
        "order_status",
        "refund_request",
        "policy_question",
        "product_question",
        "escalate",
        "smalltalk",
    ]
    language: Literal["en", "ta", "tanglish"]
    order_number: str | None = None
    refund_reason: str | None = None
    search_query: str | None = None
    category: str | None = None
    max_price_inr: Decimal | None = None


class DemoCustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    phone: str
    preferred_language: str


class HealthResponse(BaseModel):
    status: str
    db: str


class TraceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    user_message_id: UUID | None = None
    intent: str
    language: str
    router_raw: dict[str, Any]
    tool_calls: list[dict[str, Any]]
    final_answer: str
    models: dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    cost_inr: Decimal
    latency_ms: int
    error: str | None = None
    created_at: datetime
