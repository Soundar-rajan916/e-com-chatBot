import {
  ChatRequestPayload,
  ChatResponsePayload,
  DemoCustomer,
  HealthResponsePayload,
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
      return 'Access forbidden. This session does not belong to the selected customer.';
    }
    if (status === 404) {
      return 'The requested customer or resource was not found.';
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
