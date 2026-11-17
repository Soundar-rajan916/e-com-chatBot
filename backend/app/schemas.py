from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatContext(BaseModel):
    type: Literal["none", "product", "order"] = "none"
    id: str | None = None


class ChatRequest(BaseModel):
    customer_id: UUID | None = None
    session_id: UUID | None = None
    message: str = Field(..., min_length=1)
    input_mode: str = Field(default="text")
    context: ChatContext | None = None


class SourceItem(BaseModel):
    type: Literal["policy", "product"]
    id: str
    title: str


# ============================================================================
# Structured Output Data Models
# ============================================================================


class OrderItemSummary(BaseModel):
    id: UUID | str | None = None
    product_id: UUID | str | None = None
    product_title: str
    title: str | None = None
    quantity: int = 1
    unit_price_inr: Decimal | float = 0.0
    subtotal_inr: Decimal | float = 0.0


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
    actions: list[dict[str, Any]] = Field(default_factory=list)
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


# ============================================================================
# Customer Auth & Account Schemas
# ============================================================================


class CustomerRegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=7, max_length=50)
    preferred_language: str = Field(default="en", max_length=20)


class CustomerLoginRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class CustomerChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class CustomerUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    preferred_language: str | None = Field(default=None, max_length=20)


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    name: str
    phone: str
    preferred_language: str
    created_at: datetime


# ============================================================================
# Store Config Schema
# ============================================================================


class StoreConfigResponse(BaseModel):
    env: str
    dev_tools: bool
    voice_enabled: bool
    voice_max_seconds: int
    store_name: str
    refund_auto_approve_limit_inr: Decimal
    return_window_days: int


# ============================================================================
# Product Catalog Schemas
# ============================================================================


class ProductDetailResponse(BaseModel):
    id: UUID
    sku: str
    name_en: str
    name_ta: str
    title: str | None = None
    title_ta: str | None = None
    category: str
    subcategory: str | None = None
    description_en: str
    description_ta: str
    price: Decimal
    price_inr: Decimal | None = None
    stock_qty: int
    stock: int | None = None
    is_active: bool
    rating: Decimal | None = None
    image_url: str

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            data = {k: v for k, v in data.__dict__.items() if not k.startswith("_")}
        if isinstance(data, dict):
            if "title" not in data and "name_en" in data:
                data["title"] = data["name_en"]
            if "title_ta" not in data and "name_ta" in data:
                data["title_ta"] = data["name_ta"]
            if "price_inr" not in data and "price" in data:
                data["price_inr"] = data["price"]
            if "stock" not in data and "stock_qty" in data:
                data["stock"] = data["stock_qty"]
        return data


class ProductListItemResponse(BaseModel):
    id: UUID
    sku: str
    name_en: str
    name_ta: str
    title: str | None = None
    title_ta: str | None = None
    category: str
    subcategory: str | None = None
    price: Decimal
    price_inr: Decimal | None = None
    stock_qty: int
    stock: int | None = None
    rating: Decimal | None = None
    image_url: str

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            data = {k: v for k, v in data.__dict__.items() if not k.startswith("_")}
        if isinstance(data, dict):
            if "title" not in data and "name_en" in data:
                data["title"] = data["name_en"]
            if "title_ta" not in data and "name_ta" in data:
                data["title_ta"] = data["name_ta"]
            if "price_inr" not in data and "price" in data:
                data["price_inr"] = data["price"]
            if "stock" not in data and "stock_qty" in data:
                data["stock"] = data["stock_qty"]
        return data


class ProductListResponse(BaseModel):
    items: list[ProductListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    categories: list[str]
    price_min: Decimal
    price_max: Decimal


# ============================================================================
# Cart Schemas
# ============================================================================


class CartItemAddRequest(BaseModel):
    product_id: UUID
    quantity: int = Field(default=1, ge=1, le=10)


class CartItemUpdateRequest(BaseModel):
    quantity: int = Field(..., ge=1, le=10)


class CartItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_sku: str
    sku: str | None = None
    product_name_en: str
    title: str | None = None
    product_name_ta: str
    title_ta: str | None = None
    unit_price: Decimal
    price_inr: Decimal | None = None
    quantity: int
    subtotal: Decimal
    subtotal_inr: Decimal | None = None
    stock_qty: int
    stock_available: int | None = None
    is_available: bool
    in_stock: bool | None = None
    image_url: str

    @model_validator(mode="before")
    @classmethod
    def populate_cart_item_aliases(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            data = {k: v for k, v in data.__dict__.items() if not k.startswith("_")}
        if isinstance(data, dict):
            if "sku" not in data and "product_sku" in data:
                data["sku"] = data["product_sku"]
            if "title" not in data and "product_name_en" in data:
                data["title"] = data["product_name_en"]
            if "title_ta" not in data and "product_name_ta" in data:
                data["title_ta"] = data["product_name_ta"]
            if "price_inr" not in data and "unit_price" in data:
                data["price_inr"] = data["unit_price"]
            if "subtotal_inr" not in data and "subtotal" in data:
                data["subtotal_inr"] = data["subtotal"]
            if "stock_available" not in data and "stock_qty" in data:
                data["stock_available"] = data["stock_qty"]
            if "in_stock" not in data and "is_available" in data:
                data["in_stock"] = data["is_available"]
        return data


class CartProblem(BaseModel):
    code: str
    product_id: UUID
    message: str


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    total_items: int
    subtotal: Decimal
    subtotal_inr: Decimal | None = None
    tax: Decimal
    shipping: Decimal
    shipping_fee_inr: Decimal | None = None
    total: Decimal
    total_inr: Decimal | None = None
    is_checkout_ready: bool | None = None
    problems: list[CartProblem] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def populate_cart_aliases(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            data = {k: v for k, v in data.__dict__.items() if not k.startswith("_")}
        if isinstance(data, dict):
            if "subtotal_inr" not in data and "subtotal" in data:
                data["subtotal_inr"] = data["subtotal"]
            if "shipping_fee_inr" not in data and "shipping" in data:
                data["shipping_fee_inr"] = data["shipping"]
            if "total_inr" not in data and "total" in data:
                data["total_inr"] = data["total"]
            if "is_checkout_ready" not in data:
                problems = data.get("problems", [])
                total_items = data.get("total_items", 0)
                data["is_checkout_ready"] = len(problems) == 0 and total_items > 0
        return data


# ============================================================================
# Checkout & Order Schemas
# ============================================================================


class CheckoutAddress(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(default="9876543210", min_length=7, max_length=50)
    line1: str = Field(..., min_length=1, max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    pincode: str = Field(..., min_length=4, max_length=20)

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "name" not in data and "full_name" in data:
                data["name"] = data["full_name"]
            if "line1" not in data and "street" in data:
                data["line1"] = data["street"]
            if "phone" not in data or not data["phone"]:
                data["phone"] = "9876543210"
        return data


class CheckoutRequest(BaseModel):
    shipping_address: CheckoutAddress
    payment_method: Literal["cod", "demo_card"] = "cod"
    demo_payment_result: Literal["success", "failure"] = "success"

    @model_validator(mode="before")
    @classmethod
    def map_payment_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            pm = data.get("payment_method")
            if pm in ("mock_card", "card"):
                data["payment_method"] = "demo_card"
            res = data.get("mock_payment_outcome") or data.get("payment_outcome")
            if res and "demo_payment_result" not in data:
                data["demo_payment_result"] = res
        return data


class ReturnInfo(BaseModel):
    eligible: bool
    reason_ineligible: str | None = None
    days_remaining: int | None = None
    active_refund_status: str | None = None
    active_refund_id: UUID | None = None


class OrderDetailResponse(BaseModel):
    id: UUID | str | None = None
    order_number: str
    status: str
    total_amount: Decimal
    total_amount_inr: Decimal | None = None
    placed_at: datetime
    created_at: str | None = None
    estimated_delivery: datetime | None = None
    delivered_at: datetime | None = None
    tracking_note: str | None = None
    payment_method: str
    payment_status: str
    shipping_name: str | None = None
    shipping_phone: str | None = None
    shipping_line1: str | None = None
    shipping_line2: str | None = None
    shipping_city: str | None = None
    shipping_state: str | None = None
    shipping_pincode: str | None = None
    shipping_address: dict[str, Any] | None = None
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    cancellation_reason: str | None = None
    is_cancellable: bool | None = None
    is_returnable: bool | None = None
    items: list[OrderItemSummary]
    status_history: list[dict[str, Any]]
    return_info: ReturnInfo

    @model_validator(mode="before")
    @classmethod
    def populate_order_aliases(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            data = {k: v for k, v in data.__dict__.items() if not k.startswith("_")}
        if isinstance(data, dict):
            if "total_amount_inr" not in data and "total_amount" in data:
                data["total_amount_inr"] = data["total_amount"]
            if "created_at" not in data and "placed_at" in data:
                pa = data["placed_at"]
                data["created_at"] = pa.isoformat() if hasattr(pa, "isoformat") else str(pa)
            if "shipping_address" not in data or not data["shipping_address"]:
                name = data.get("shipping_name") or ""
                lines = [data.get("shipping_line1"), data.get("shipping_line2")]
                street = ", ".join([str(l) for l in lines if l])
                data["shipping_address"] = {
                    "full_name": name,
                    "street": street,
                    "city": data.get("shipping_city") or "",
                    "state": data.get("shipping_state") or "",
                    "pincode": data.get("shipping_pincode") or "",
                }
            if "cancellation_reason" not in data and "cancel_reason" in data:
                data["cancellation_reason"] = data["cancel_reason"]
            if "is_cancellable" not in data:
                st = str(data.get("status") or "").lower()
                data["is_cancellable"] = st in ("placed", "confirmed", "processing", "pending")
            if "is_returnable" not in data:
                ret = data.get("return_info")
                if hasattr(ret, "eligible"):
                    data["is_returnable"] = ret.eligible
                elif isinstance(ret, dict):
                    data["is_returnable"] = bool(ret.get("eligible"))
                else:
                    data["is_returnable"] = False
        return data


class OrderListItemResponse(BaseModel):
    order_number: str
    status: str
    total_amount: Decimal
    placed_at: datetime
    delivered_at: datetime | None = None
    items_count: int
    payment_method: str
    payment_status: str


class CancelOrderRequest(BaseModel):
    reason: str | None = None


class ReturnOrderRequest(BaseModel):
    reason: str = Field(..., min_length=3)


class ReturnOrderResponse(BaseModel):
    order_number: str
    refund_id: UUID
    status: str
    auto_approved: bool
    amount: Decimal
    message: str


# ============================================================================
# Admin Operations Schemas (Orders & Streamlined Refunds)
# ============================================================================


class AdminOrderListItem(BaseModel):
    id: UUID
    order_number: str
    customer_id: UUID
    customer_name: str
    customer_phone: str
    customer_email: str
    status: str
    total_amount: Decimal
    total_amount_inr: Decimal | None = None
    placed_at: datetime
    delivered_at: datetime | None = None
    items_count: int
    items_summary: str
    payment_method: str
    payment_status: str

    @model_validator(mode="before")
    @classmethod
    def populate_admin_order_aliases(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            data = {k: v for k, v in data.__dict__.items() if not k.startswith("_")}
        if isinstance(data, dict):
            if "total_amount_inr" not in data and "total_amount" in data:
                data["total_amount_inr"] = data["total_amount"]
        return data


class AdminRefundListItem(BaseModel):
    id: UUID
    order_id: UUID
    order_number: str
    customer_id: UUID
    customer_name: str
    amount: Decimal
    amount_inr: Decimal | None = None
    reason: str
    status: str
    created_at: datetime
    decided_by: str | None = None

    @model_validator(mode="before")
    @classmethod
    def populate_admin_refund_aliases(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            data = {k: v for k, v in data.__dict__.items() if not k.startswith("_")}
        if isinstance(data, dict):
            if "amount_inr" not in data and "amount" in data:
                data["amount_inr"] = data["amount"]
        return data


class AdminRefundRejectRequest(BaseModel):
    reason: str = Field(default="Rejected by administrator", min_length=1, max_length=1000)
