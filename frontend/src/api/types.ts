export interface DemoCustomer {
  id: string;
  name: string;
  phone: string;
  preferred_language: string;
}

export interface ChatRequestPayload {
  customer_id: string;
  session_id?: string | null;
  message: string;
  input_mode?: string;
}

export interface SourceItem {
  type: 'policy' | 'product';
  id: string;
  title: string;
}

export interface ChatResponsePayload {
  session_id: string;
  reply: string;
  intent: string;
  language: string;
  requires_human: boolean;
  trace_id: string;
  sources?: SourceItem[];
  suggested_actions?: string[];
  structured_output?: Record<string, unknown>;
}

export interface HealthResponsePayload {
  status: string;
  db: string;
}

export interface ChatMessageItem {
  id: string;
  role: 'user' | 'assistant' | 'agent';
  content: string;
  timestamp: string;
  intent?: string;
  language?: string;
  requires_human?: boolean;
  trace_id?: string;
  sources?: SourceItem[];
  suggested_actions?: string[];
  structured_output?: Record<string, unknown>;
  agent_id?: string | null;
  agent_name?: string | null;
  input_mode?: string;
}

// ==========================================
// Admin Console & Escalations Types
// ==========================================

export interface Agent {
  id: string;
  email: string;
  name: string;
  role: 'agent' | 'admin';
}

export type EscalationStatus = 'open' | 'in_progress' | 'resolved';
export type EscalationPriority = 'low' | 'normal' | 'high';
export type EscalationReasonType =
  | 'user_requested'
  | 'router_fallback'
  | 'llm_failure'
  | 'refund_pending_approval';

export interface EscalationSummary {
  id: string;
  session_id: string;
  customer_id: string;
  customer_name: string;
  customer_phone_masked: string;
  reason: string;
  reason_type: EscalationReasonType | string;
  status: EscalationStatus;
  priority: EscalationPriority;
  assigned_to: string | null;
  assigned_agent_name: string | null;
  refund_id: string | null;
  order_number: string | null;
  resolution_note: string | null;
  is_overdue: boolean;
  version: number;
  created_at: string;
  updated_at: string;
  first_response_at: string | null;
  resolved_at: string | null;
}

export interface EscalationsListResponse {
  items: EscalationSummary[];
  total: number;
}

export interface EscalationStats {
  open_count: number;
  in_progress_count: number;
  resolved_count: number;
  overdue_count: number;
  unassigned_count: number;
  my_open_count: number;
  by_reason_type: Record<string, number>;
  avg_response_time_seconds: number | null;
  avg_resolution_time_seconds: number | null;
}

export interface CustomerDetail {
  id: string;
  name: string;
  phone: string;
  preferred_language: string;
  created_at: string;
}

export interface CustomerOrderItemDetail {
  product_title: string;
  quantity: number;
  unit_price_inr: string | number;
}

export interface CustomerOrderDetail {
  id: string;
  order_number: string;
  status: string;
  total_amount_inr: string | number;
  created_at: string;
  items: CustomerOrderItemDetail[];
}

export interface LinkedRefundDetail {
  id: string;
  order_id: string;
  order_number: string | null;
  amount: string | number;
  reason: string;
  status: string;
  created_at: string;
}

export interface TranscriptMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'agent';
  content: string;
  agent_id: string | null;
  agent_name: string | null;
  input_mode: string;
  created_at: string;
}

export interface TraceDetail {
  id: string;
  session_id: string;
  intent: string;
  language: string;
  router_raw: Record<string, unknown>;
  tool_calls: Array<Record<string, unknown>>;
  final_answer: string;
  models: Record<string, unknown>;
  prompt_tokens: number;
  completion_tokens: number;
  cost_inr: string | number;
  latency_ms: number;
  error: string | null;
  created_at: string;
}

export interface EscalationNoteItem {
  id: string;
  agent_id: string;
  agent_name: string;
  body: string;
  created_at: string;
}

export interface EscalationEventItem {
  id: string;
  actor_type: 'system' | 'agent';
  actor_id: string | null;
  actor_name: string | null;
  action: string;
  detail: Record<string, unknown>;
  created_at: string;
}

export interface EscalationFullDetail {
  escalation: EscalationSummary;
  customer: CustomerDetail;
  recent_orders: CustomerOrderDetail[];
  refund: LinkedRefundDetail | null;
  messages: TranscriptMessage[];
  traces: TraceDetail[];
  notes: EscalationNoteItem[];
  events: EscalationEventItem[];
}

// ==========================================
// E-Commerce Store & Customer Types
// ==========================================

export interface CustomerAccount {
  id: string;
  email: string;
  name: string;
  phone: string;
  preferred_language: string;
  created_at: string;
}

export interface StoreConfig {
  store_name: string;
  return_window_days: number;
  supported_languages: string[];
  dev_tools: boolean;
  chat_widget_enabled: boolean;
}

export interface StorePolicy {
  policy_name: string;
  language: string;
  content_markdown: string;
  updated_at: string;
}

export interface CategoryItem {
  category: string;
  count?: number;
  min_price?: string;
  max_price?: string;
  icon?: string;
}

export interface ProductItem {
  id: string;
  sku: string;
  title: string;
  title_ta?: string | null;
  description?: string | null;
  description_ta?: string | null;
  category: string;
  price_inr: string | number;
  stock: number;
  is_active: boolean;
  rating?: number | null;
  image_url?: string;
}

export interface ProductListResponse {
  items: ProductItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CartItemDetail {
  product_id: string;
  sku: string;
  title: string;
  title_ta?: string | null;
  price_inr: string | number;
  quantity: number;
  subtotal_inr: string | number;
  in_stock: boolean;
  stock_available: number;
  image_url?: string;
}

export interface CartDetail {
  items: CartItemDetail[];
  total_items: number;
  subtotal_inr: string | number;
  shipping_fee_inr: string | number;
  total_inr: string | number;
  is_checkout_ready: boolean;
}

export interface OrderStatusHistoryItem {
  id: string;
  status: string;
  note?: string | null;
  created_at: string;
}

export interface OrderItemDetail {
  id: string;
  product_id: string;
  title: string;
  quantity: number;
  unit_price_inr: string | number;
  subtotal_inr: string | number;
}

export interface OrderDetail {
  id: string;
  order_number: string;
  status: string;
  total_amount_inr: string | number;
  payment_method: string;
  payment_status: string;
  shipping_address: {
    full_name: string;
    street: string;
    city: string;
    state: string;
    pincode: string;
  };
  is_cancellable: boolean;
  is_returnable: boolean;
  days_since_delivery: number | null;
  delivered_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  created_at: string;
  items: OrderItemDetail[];
  status_history: OrderStatusHistoryItem[];
  refund?: LinkedRefundDetail | null;
}

export interface AdminOrderSummary {
  id: string;
  order_number: string;
  customer_id: string;
  customer_name: string;
  customer_phone: string;
  customer_email: string;
  status: string;
  total_amount: number | string;
  total_amount_inr?: number | string;
  placed_at: string;
  delivered_at: string | null;
  items_count: number;
  items_summary: string;
  payment_method: string;
  payment_status: string;
}

export interface AdminRefundSummary {
  id: string;
  order_id: string;
  order_number: string;
  customer_id: string;
  customer_name: string;
  amount: number | string;
  amount_inr?: number | string;
  reason: string;
  status: string;
  created_at: string;
  decided_by?: string | null;
}

