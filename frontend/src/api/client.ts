import {
  Agent,
  ChatRequestPayload,
  ChatResponsePayload,
  DemoCustomer,
  EscalationFullDetail,
  EscalationsListResponse,
  EscalationStats,
  HealthResponsePayload,
  TranscriptMessage,
} from './types';

export class ApiError extends Error {
  public status: number;
  public userMessage: string;

  constructor(status: number, message: string, userMessage?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.userMessage = userMessage || ApiError.getDefaultUserMessage(status, message);
  }

  private static getDefaultUserMessage(status: number, detail: string): string {
    if (status === 422) {
      return detail || 'Invalid message. Please check message length and content.';
    }
    if (status === 403) {
      return detail || 'Access forbidden.';
    }
    if (status === 404) {
      return detail || 'The requested customer or resource was not found.';
    }
    if (status === 409) {
      return detail || 'Conflict detected. Please refresh and try again.';
    }
    if (status >= 500) {
      return 'We are experiencing a temporary server problem. Please retry.';
    }
    return detail || 'An unexpected error occurred.';
  }
}

const DEFAULT_BASE_URL = 'http://127.0.0.1:8000';

export function getBaseUrl(): string {
  if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) {
    return (import.meta.env.VITE_API_BASE_URL as string).replace(/\/$/, '');
  }
  return DEFAULT_BASE_URL;
}

async function requestWithTimeout<T>(
  url: string,
  options: RequestInit = {},
  timeoutMs = 30000
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      let detail = `HTTP Error ${res.status}`;
      try {
        const errJson = await res.json();
        detail = errJson.detail || errJson.message || JSON.stringify(errJson);
      } catch {
        const text = await res.text();
        if (text) detail = text;
      }
      throw new ApiError(res.status, detail);
    }

    return (await res.json()) as T;
  } catch (err: unknown) {
    clearTimeout(timeoutId);

    if (err instanceof ApiError) {
      throw err;
    }

    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(0, 'Request aborted due to timeout', 'Connection timed out. Please try again.');
    }

    const message = err instanceof Error ? err.message : 'Unknown network failure';
    throw new ApiError(0, message, 'Could not connect to the support server. Please check your network.');
  }
}

export async function sendMessage(payload: ChatRequestPayload): Promise<ChatResponsePayload> {
  const url = `${getBaseUrl()}/chat`;
  return requestWithTimeout<ChatResponsePayload>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

export async function getDemoCustomers(): Promise<DemoCustomer[]> {
  const url = `${getBaseUrl()}/customers/demo`;
  return requestWithTimeout<DemoCustomer[]>(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });
}

export async function getHealth(): Promise<HealthResponsePayload> {
  const url = `${getBaseUrl()}/health`;
  return requestWithTimeout<HealthResponsePayload>(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });
}

// ==========================================
// Admin Auth & Escalations Endpoints
// ==========================================

export async function adminLogin(email: string, password: string): Promise<Agent> {
  const url = `${getBaseUrl()}/admin/auth/login`;
  return requestWithTimeout<Agent>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });
}

export async function adminLogout(): Promise<{ message: string }> {
  const url = `${getBaseUrl()}/admin/auth/logout`;
  return requestWithTimeout<{ message: string }>(url, {
    method: 'POST',
    headers: {
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
  });
}

export async function getAdminMe(): Promise<Agent> {
  const url = `${getBaseUrl()}/admin/auth/me`;
  return requestWithTimeout<Agent>(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    credentials: 'include',
  });
}

export async function getEscalations(params?: {
  status?: string;
  priority?: string;
  reason_type?: string;
  assigned?: string;
  q?: string;
  overdue?: boolean;
  limit?: number;
  offset?: number;
}): Promise<EscalationsListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.priority) query.set('priority', params.priority);
  if (params?.reason_type) query.set('reason_type', params.reason_type);
  if (params?.assigned) query.set('assigned', params.assigned);
  if (params?.q) query.set('q', params.q);
  if (params?.overdue) query.set('overdue', 'true');
  if (params?.limit) query.set('limit', params.limit.toString());
  if (params?.offset) query.set('offset', params.offset.toString());

  const qs = query.toString();
  const url = `${getBaseUrl()}/admin/escalations${qs ? `?${qs}` : ''}`;
  return requestWithTimeout<EscalationsListResponse>(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    credentials: 'include',
  });
}

export async function getEscalationStats(): Promise<EscalationStats> {
  const url = `${getBaseUrl()}/admin/escalations/stats`;
  return requestWithTimeout<EscalationStats>(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    credentials: 'include',
  });
}

export async function getEscalationDetail(id: string): Promise<EscalationFullDetail> {
  const url = `${getBaseUrl()}/admin/escalations/${id}`;
  return requestWithTimeout<EscalationFullDetail>(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    credentials: 'include',
  });
}

export async function assignEscalation(
  id: string,
  version: number,
  agentId?: string,
  force = false
): Promise<{ message: string; version: number; status: string }> {
  const url = `${getBaseUrl()}/admin/escalations/${id}/assign`;
  return requestWithTimeout<{ message: string; version: number; status: string }>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
    body: JSON.stringify({ version, agent_id: agentId || null, force }),
  });
}

export async function unassignEscalation(
  id: string,
  version: number
): Promise<{ message: string; version: number; status: string }> {
  const url = `${getBaseUrl()}/admin/escalations/${id}/unassign`;
  return requestWithTimeout<{ message: string; version: number; status: string }>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
    body: JSON.stringify({ version }),
  });
}

export async function addEscalationNote(
  id: string,
  body: string
): Promise<{ message: string; note_id: string }> {
  const url = `${getBaseUrl()}/admin/escalations/${id}/notes`;
  return requestWithTimeout<{ message: string; note_id: string }>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
    body: JSON.stringify({ body }),
  });
}

export async function replyEscalation(
  id: string,
  message: string
): Promise<{ message: string; message_id: string }> {
  const url = `${getBaseUrl()}/admin/escalations/${id}/reply`;
  return requestWithTimeout<{ message: string; message_id: string }>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
    body: JSON.stringify({ message }),
  });
}

export async function approveRefund(
  id: string,
  version: number
): Promise<{ message: string; version: number }> {
  const url = `${getBaseUrl()}/admin/escalations/${id}/refund/approve`;
  return requestWithTimeout<{ message: string; version: number }>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
    body: JSON.stringify({ version }),
  });
}

export async function rejectRefund(
  id: string,
  reason: string,
  version: number
): Promise<{ message: string; version: number }> {
  const url = `${getBaseUrl()}/admin/escalations/${id}/refund/reject`;
  return requestWithTimeout<{ message: string; version: number }>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
    body: JSON.stringify({ reason, version }),
  });
}

export async function resolveEscalation(
  id: string,
  resolutionNote: string,
  version: number
): Promise<{ message: string; version: number }> {
  const url = `${getBaseUrl()}/admin/escalations/${id}/resolve`;
  return requestWithTimeout<{ message: string; version: number }>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
    body: JSON.stringify({ resolution_note: resolutionNote, version }),
  });
}

export async function reopenEscalation(
  id: string,
  version: number
): Promise<{ message: string; version: number; status: string }> {
  const url = `${getBaseUrl()}/admin/escalations/${id}/reopen`;
  return requestWithTimeout<{ message: string; version: number; status: string }>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
    body: JSON.stringify({ version }),
  });
}

export async function updatePriority(
  id: string,
  priority: 'low' | 'normal' | 'high',
  version: number
): Promise<{ message: string; version: number; priority: string }> {
  const url = `${getBaseUrl()}/admin/escalations/${id}/priority`;
  return requestWithTimeout<{ message: string; version: number; priority: string }>(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
    body: JSON.stringify({ priority, version }),
  });
}

export async function pollSessionMessages(
  sessionId: string,
  customerId: string,
  after?: string
): Promise<TranscriptMessage[]> {
  const query = new URLSearchParams({ customer_id: customerId });
  if (after) query.set('after', after);
  const url = `${getBaseUrl()}/sessions/${sessionId}/messages?${query.toString()}`;
  return requestWithTimeout<TranscriptMessage[]>(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });
}
