export type Locale = 'en' | 'ta' | 'tanglish';

export interface WidgetContext {
  type: 'none' | 'product' | 'order';
  id?: string;
  title?: string;
}

export interface WidgetConfig {
  apiUrl?: string;
  storeName?: string;
  initialLocale?: Locale;
  defaultOpen?: boolean;
  theme?: {
    primaryColor?: string;
  };
  onAction?: (action: { type: string; payload: Record<string, unknown> }) => void;
}

export interface ChatMessageItem {
  id: string;
  role: 'user' | 'assistant' | 'agent';
  content: string;
  input_mode?: 'text' | 'voice';
  timestamp: string;
  agent_name?: string;
  requires_human?: boolean;
  suggested_actions?: string[];
  intent?: string;
  language?: string;
  trace_id?: string;
  sources?: Array<{ type: string; id: string; title: string }>;
  actions?: Array<{ type: string; payload: Record<string, unknown> }>;
}

export interface SupportWidgetApi {
  init: (config?: WidgetConfig) => void;
  open: () => void;
  close: () => void;
  toggle: () => void;
  setContext: (context: WidgetContext) => void;
  setLocale: (locale: Locale) => void;
  identify: (customer: { id: string; name?: string; email?: string }) => void;
  destroy: () => void;
  isOpen: () => boolean;
}

declare global {
  interface Window {
    SupportWidget?: SupportWidgetApi;
  }
}
