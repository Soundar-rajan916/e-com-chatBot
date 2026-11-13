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
  structured_output?: any;
}

export interface HealthResponsePayload {
  status: string;
  db: string;
}

export interface ChatMessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  intent?: string;
  language?: string;
  requires_human?: boolean;
  trace_id?: string;
  sources?: SourceItem[];
  suggested_actions?: string[];
  structured_output?: any;
}
