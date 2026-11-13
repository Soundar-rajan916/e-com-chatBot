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
