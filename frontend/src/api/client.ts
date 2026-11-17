import {
  AdminOrderSummary,
  AdminRefundSummary,
  Agent,
  CartDetail,
  CartItemDetail,
  CategoryItem,
  ChatRequestPayload,
  ChatResponsePayload,
  CustomerAccount,
  DemoCustomer,
  EscalationFullDetail,
  EscalationsListResponse,
  EscalationStats,
  HealthResponsePayload,
  OrderDetail,
  OrderItemDetail,
  OrderStatusHistoryItem,
  ProductItem,
  ProductListResponse,
  StoreConfig,
  StorePolicy,
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
  if (typeof window !== 'undefined' && window.location && window.location.origin) {
    return `${window.location.origin}/api`;
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

// ==========================================
// Customer Storefront Endpoints
// ==========================================

export async function getStoreConfig(): Promise<StoreConfig> {
  const url = `${getBaseUrl()}/config`;
  return requestWithTimeout<StoreConfig>(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  });
}

export async function getStorePolicy(lang = 'en'): Promise<StorePolicy> {
  const url = `${getBaseUrl()}/policy/${lang}`;
  return requestWithTimeout<StorePolicy>(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  });
}

export async function customerRegister(payload: {
  email: string;
  password: string;
  name: string;
  phone: string;
  preferred_language?: string;
}): Promise<CustomerAccount> {
  const url = `${getBaseUrl()}/auth/register`;
  return requestWithTimeout<CustomerAccount>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'shop-web',
    },
    credentials: 'include',
    body: JSON.stringify(payload),
  });
}

export async function customerLogin(payload: {
  email: string;
  password: string;
}): Promise<CustomerAccount> {
  const url = `${getBaseUrl()}/auth/login`;
  return requestWithTimeout<CustomerAccount>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'shop-web',
    },
    credentials: 'include',
    body: JSON.stringify(payload),
  });
}

export async function customerLogout(): Promise<{ message: string }> {
  const url = `${getBaseUrl()}/auth/logout`;
  return requestWithTimeout<{ message: string }>(url, {
    method: 'POST',
    headers: {
      'X-Requested-With': 'shop-web',
    },
    credentials: 'include',
  });
}

export async function getCustomerMe(): Promise<CustomerAccount> {
  const url = `${getBaseUrl()}/auth/me`;
  return requestWithTimeout<CustomerAccount>(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    credentials: 'include',
  });
}

function normalizeProductItem(p: unknown): ProductItem {
  const obj = (p && typeof p === 'object' ? p : {}) as Record<string, unknown>;
  const stock = Number(obj.stock ?? obj.stock_qty ?? 0);
  return {
    id: String(obj.id || ''),
    sku: String(obj.sku || ''),
    title: String(obj.title || obj.name_en || ''),
    title_ta: obj.title_ta || obj.name_ta ? String(obj.title_ta || obj.name_ta) : null,
    description: obj.description || obj.description_en ? String(obj.description || obj.description_en) : null,
    description_ta: obj.description_ta ? String(obj.description_ta) : null,
    category: String(obj.category || ''),
    price_inr:
      typeof obj.price_inr === 'string' || typeof obj.price_inr === 'number'
        ? obj.price_inr
        : typeof obj.price === 'string' || typeof obj.price === 'number'
        ? obj.price
        : 0,
    stock: isNaN(stock) ? 0 : stock,
    is_active: Boolean(obj.is_active ?? true),
    rating: typeof obj.rating === 'number' ? obj.rating : null,
    image_url: obj.image_url ? String(obj.image_url) : undefined,
  };
}

export function normalizeCart(raw: unknown): CartDetail {
  if (!raw || typeof raw !== 'object') {
    return {
      items: [],
      total_items: 0,
      subtotal_inr: 0,
      shipping_fee_inr: 0,
      total_inr: 0,
      is_checkout_ready: false,
    };
  }

  const r = raw as Record<string, unknown>;
  const rawItems = Array.isArray(r.items) ? r.items : [];

  const items: CartItemDetail[] = rawItems.map((rawItem: unknown) => {
    const it = (rawItem && typeof rawItem === 'object' ? rawItem : {}) as Record<string, unknown>;
    const stockQty = Number(it.stock_available ?? it.stock_qty ?? 0);
    const quantity = Number(it.quantity ?? 1);
    const isAvail = typeof it.in_stock === 'boolean'
      ? it.in_stock
      : typeof it.is_available === 'boolean'
      ? it.is_available
      : stockQty > 0;

    return {
      product_id: String(it.product_id || it.id || ''),
      sku: String(it.sku || it.product_sku || ''),
      title: String(it.title || it.product_name_en || 'Product'),
      title_ta: it.title_ta || it.product_name_ta ? String(it.title_ta || it.product_name_ta) : null,
      price_inr:
        typeof it.price_inr === 'string' || typeof it.price_inr === 'number'
          ? it.price_inr
          : typeof it.unit_price === 'string' || typeof it.unit_price === 'number'
          ? it.unit_price
          : 0,
      quantity,
      subtotal_inr:
        typeof it.subtotal_inr === 'string' || typeof it.subtotal_inr === 'number'
          ? it.subtotal_inr
          : typeof it.subtotal === 'string' || typeof it.subtotal === 'number'
          ? it.subtotal
          : Number(it.price_inr ?? it.unit_price ?? 0) * quantity,
      in_stock: isAvail && stockQty >= quantity,
      stock_available: isNaN(stockQty) ? 0 : stockQty,
      image_url: it.image_url ? String(it.image_url) : undefined,
    };
  });

  const totalItems = Number(r.total_items ?? items.reduce((sum, i) => sum + i.quantity, 0));
  const subtotal = Number(r.subtotal_inr ?? r.subtotal ?? items.reduce((sum, i) => sum + Number(i.subtotal_inr), 0));
  const shipping = Number(r.shipping_fee_inr ?? r.shipping ?? 0);
  const total = Number(r.total_inr ?? r.total ?? (subtotal + shipping));
  const problems = Array.isArray(r.problems) ? r.problems : [];

  const isCheckoutReady = typeof r.is_checkout_ready === 'boolean'
    ? r.is_checkout_ready
    : (problems.length === 0 && totalItems > 0 && items.every((i) => i.in_stock));

  return {
    items,
    total_items: totalItems,
    subtotal_inr: subtotal,
    shipping_fee_inr: shipping,
    total_inr: total,
    is_checkout_ready: isCheckoutReady,
  };
}

export async function getProducts(params?: {
  q?: string;
  category?: string;
  min_price?: number;
  max_price?: number;
  in_stock_only?: boolean;
  sort?: string;
  page?: number;
  page_size?: number;
}): Promise<ProductListResponse> {
  const query = new URLSearchParams();
  if (params?.q) query.set('q', params.q);
  if (params?.category) query.set('category', params.category);
  if (params?.min_price !== undefined) query.set('min_price', params.min_price.toString());
  if (params?.max_price !== undefined) query.set('max_price', params.max_price.toString());
  if (params?.in_stock_only) query.set('in_stock_only', 'true');
  if (params?.sort) query.set('sort', params.sort);
  if (params?.page) query.set('page', params.page.toString());
  if (params?.page_size) query.set('page_size', params.page_size.toString());

  const qs = query.toString();
  const url = `${getBaseUrl()}/products${qs ? `?${qs}` : ''}`;
  const res = await requestWithTimeout<{
    items?: unknown[];
    total?: number;
    page?: number;
    page_size?: number;
    total_pages?: number;
  }>(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  });

  return {
    items: Array.isArray(res.items) ? res.items.map(normalizeProductItem) : [],
    total: res.total || 0,
    page: res.page || 1,
    page_size: res.page_size || 20,
    total_pages: res.total_pages || 1,
  };
}

export async function getProduct(idOrSku: string): Promise<ProductItem> {
  const url = `${getBaseUrl()}/products/${idOrSku}`;
  const res = await requestWithTimeout<unknown>(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  });
  return normalizeProductItem(res);
}

export async function getRelatedProducts(productId: string): Promise<ProductItem[]> {
  const url = `${getBaseUrl()}/products/${productId}/related`;
  const res = await requestWithTimeout<unknown[]>(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  });
  return Array.isArray(res) ? res.map(normalizeProductItem) : [];
}

export async function getCategories(): Promise<CategoryItem[]> {
  const url = `${getBaseUrl()}/categories`;
  try {
    const raw = await requestWithTimeout<unknown[]>(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    });
    if (!Array.isArray(raw)) return [];
    return raw.map((item) => {
      if (typeof item === 'string') {
        return { category: item, icon: '📦' };
      }
      if (item && typeof item === 'object') {
        const obj = item as Record<string, unknown>;
        return {
          category: String(obj.category || obj.name || ''),
          count: typeof obj.count === 'number' ? obj.count : undefined,
          min_price: typeof obj.min_price === 'string' ? obj.min_price : undefined,
          max_price: typeof obj.max_price === 'string' ? obj.max_price : undefined,
          icon: typeof obj.icon === 'string' ? obj.icon : '📦',
        };
      }
      return { category: String(item), icon: '📦' };
    });
  } catch (err) {
    console.warn('Failed to fetch categories, falling back to empty list', err);
    return [];
  }
}

export async function getCart(): Promise<CartDetail> {
  const url = `${getBaseUrl()}/cart`;
  const raw = await requestWithTimeout<unknown>(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    credentials: 'include',
  });
  return normalizeCart(raw);
}

export async function addToCart(productId: string, quantity = 1): Promise<CartDetail> {
  const url = `${getBaseUrl()}/cart/items`;
  const raw = await requestWithTimeout<unknown>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'shop-web',
    },
    credentials: 'include',
    body: JSON.stringify({ product_id: productId, quantity }),
  });
  return normalizeCart(raw);
}

export async function updateCartItem(productId: string, quantity: number): Promise<CartDetail> {
  const url = `${getBaseUrl()}/cart/items/${productId}`;
  const raw = await requestWithTimeout<unknown>(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'shop-web',
    },
    credentials: 'include',
    body: JSON.stringify({ quantity }),
  });
  return normalizeCart(raw);
}

export async function removeCartItem(productId: string): Promise<CartDetail> {
  const url = `${getBaseUrl()}/cart/items/${productId}`;
  const raw = await requestWithTimeout<unknown>(url, {
    method: 'DELETE',
    headers: {
      'X-Requested-With': 'shop-web',
    },
    credentials: 'include',
  });
  return normalizeCart(raw);
}

export async function clearCart(): Promise<CartDetail> {
  const url = `${getBaseUrl()}/cart`;
  const raw = await requestWithTimeout<unknown>(url, {
    method: 'DELETE',
    headers: {
      'X-Requested-With': 'shop-web',
    },
    credentials: 'include',
  });
  return normalizeCart(raw);
}

export function normalizeOrderDetail(raw: unknown): OrderDetail {
  if (!raw || typeof raw !== 'object') {
    return {
      id: '',
      order_number: '',
      status: 'pending',
      total_amount_inr: 0,
      payment_method: '',
      payment_status: '',
      shipping_address: {
        full_name: '',
        street: '',
        city: '',
        state: '',
        pincode: '',
      },
      is_cancellable: false,
      is_returnable: false,
      days_since_delivery: null,
      delivered_at: null,
      cancelled_at: null,
      cancellation_reason: null,
      created_at: new Date().toISOString(),
      items: [],
      status_history: [],
      refund: null,
    };
  }

  const r = raw as Record<string, unknown>;
  const rawAddr = (r.shipping_address && typeof r.shipping_address === 'object' ? r.shipping_address : {}) as Record<string, unknown>;

  const streetParts = [r.shipping_line1, r.shipping_line2].filter(Boolean);
  const fallbackStreet = streetParts.length > 0 ? streetParts.join(', ') : '';

  const shipping_address = {
    full_name: String(rawAddr.full_name || rawAddr.name || r.shipping_name || ''),
    street: String(rawAddr.street || rawAddr.line1 || fallbackStreet || ''),
    city: String(rawAddr.city || r.shipping_city || ''),
    state: String(rawAddr.state || r.shipping_state || ''),
    pincode: String(rawAddr.pincode || r.shipping_pincode || ''),
  };

  const rawItems = Array.isArray(r.items) ? r.items : [];
  const items: OrderItemDetail[] = rawItems.map((it: unknown, idx: number) => {
    const itemObj = (it && typeof it === 'object' ? it : {}) as Record<string, unknown>;
    const qty = Number(itemObj.quantity || 1);
    const unitPrice =
      typeof itemObj.unit_price_inr === 'string' || typeof itemObj.unit_price_inr === 'number'
        ? itemObj.unit_price_inr
        : typeof itemObj.unit_price === 'string' || typeof itemObj.unit_price === 'number'
        ? itemObj.unit_price
        : 0;
    const subtotal =
      typeof itemObj.subtotal_inr === 'string' || typeof itemObj.subtotal_inr === 'number'
        ? itemObj.subtotal_inr
        : Number(unitPrice) * qty;

    return {
      id: String(itemObj.id || itemObj.product_id || `item_${idx}`),
      product_id: String(itemObj.product_id || itemObj.id || ''),
      title: String(itemObj.title || itemObj.product_title || itemObj.name_en || 'Product'),
      quantity: qty,
      unit_price_inr: unitPrice,
      subtotal_inr: subtotal,
    };
  });

  const rawHistory = Array.isArray(r.status_history) ? r.status_history : [];
  const status_history: OrderStatusHistoryItem[] = rawHistory.map((h: unknown, idx: number) => {
    const histObj = (h && typeof h === 'object' ? h : {}) as Record<string, unknown>;
    return {
      id: String(histObj.id || `hist_${idx}`),
      status: String(histObj.status || ''),
      note: histObj.note ? String(histObj.note) : null,
      created_at: String(histObj.created_at || histObj.at || ''),
    };
  });

  const retInfo = (r.return_info && typeof r.return_info === 'object' ? r.return_info : {}) as Record<string, unknown>;
  const isCancellable = typeof r.is_cancellable === 'boolean'
    ? r.is_cancellable
    : ['placed', 'confirmed', 'processing', 'pending'].includes(String(r.status || '').toLowerCase());
  const isReturnable = typeof r.is_returnable === 'boolean'
    ? r.is_returnable
    : Boolean(retInfo.eligible);

  return {
    id: String(r.id || r.order_number || ''),
    order_number: String(r.order_number || ''),
    status: String(r.status || 'placed'),
    total_amount_inr:
      typeof r.total_amount_inr === 'string' || typeof r.total_amount_inr === 'number'
        ? r.total_amount_inr
        : typeof r.total_amount === 'string' || typeof r.total_amount === 'number'
        ? r.total_amount
        : 0,
    payment_method: String(r.payment_method || ''),
    payment_status: String(r.payment_status || ''),
    shipping_address,
    is_cancellable: isCancellable,
    is_returnable: isReturnable,
    days_since_delivery: typeof r.days_since_delivery === 'number' ? r.days_since_delivery : (typeof retInfo.days_remaining === 'number' ? retInfo.days_remaining : null),
    delivered_at: r.delivered_at ? String(r.delivered_at) : null,
    cancelled_at: r.cancelled_at ? String(r.cancelled_at) : null,
    cancellation_reason: r.cancellation_reason || r.cancel_reason ? String(r.cancellation_reason || r.cancel_reason) : null,
    created_at: String(r.created_at || r.placed_at || ''),
    items,
    status_history,
    refund: (r.refund as OrderDetail['refund']) || null,
  };
}

export async function checkoutOrder(
  payload: {
    shipping_address: {
      full_name: string;
      street: string;
      city: string;
      state: string;
      pincode: string;
    };
    payment_method: 'mock_card' | 'cod';
    mock_payment_outcome?: 'success' | 'failure';
  },
  idempotencyKey: string
): Promise<OrderDetail> {
  const url = `${getBaseUrl()}/checkout`;
  const raw = await requestWithTimeout<unknown>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'shop-web',
      'Idempotency-Key': idempotencyKey,
    },
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  return normalizeOrderDetail(raw);
}

export async function getCustomerOrders(): Promise<OrderDetail[]> {
  const url = `${getBaseUrl()}/me/orders`;
  const raw = await requestWithTimeout<unknown[]>(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    credentials: 'include',
  });
  return Array.isArray(raw) ? raw.map(normalizeOrderDetail) : [];
}

export async function getCustomerOrderDetail(orderNumber: string): Promise<OrderDetail> {
  const url = `${getBaseUrl()}/me/orders/${orderNumber}`;
  const raw = await requestWithTimeout<unknown>(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    credentials: 'include',
  });
  return normalizeOrderDetail(raw);
}

export async function cancelCustomerOrder(
  orderNumber: string,
  reason: string
): Promise<OrderDetail> {
  const url = `${getBaseUrl()}/me/orders/${orderNumber}/cancel`;
  const raw = await requestWithTimeout<unknown>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'shop-web',
    },
    credentials: 'include',
    body: JSON.stringify({ reason }),
  });
  return normalizeOrderDetail(raw);
}

export async function returnCustomerOrder(
  orderNumber: string,
  items: Array<{ product_id: string; quantity: number }>,
  reason: string
): Promise<{ message: string; refund_id: string; status: string; amount_inr: string | number }> {
  const url = `${getBaseUrl()}/me/orders/${orderNumber}/return`;
  return requestWithTimeout<{
    message: string;
    refund_id: string;
    status: string;
    amount_inr: string | number;
  }>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'shop-web',
    },
    credentials: 'include',
    body: JSON.stringify({ items, reason }),
  });
}

export async function devAdvanceOrder(orderNumber: string): Promise<OrderDetail> {
  const url = `${getBaseUrl()}/dev/orders/${orderNumber}/advance`;
  return requestWithTimeout<OrderDetail>(url, {
    method: 'POST',
    headers: {
      'X-Requested-With': 'shop-web',
    },
  });
}

export async function devSetDeliveredDaysAgo(
  orderNumber: string,
  daysAgo: number
): Promise<OrderDetail> {
  const url = `${getBaseUrl()}/dev/orders/${orderNumber}/set-delivered-days-ago`;
  return requestWithTimeout<OrderDetail>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'shop-web',
    },
    body: JSON.stringify({ days_ago: daysAgo }),
  });
}

// ==========================================
// Admin Operations (Orders & Simplified Refunds)
// ==========================================

export async function getAdminOrders(params?: {
  status?: string;
  q?: string;
}): Promise<AdminOrderSummary[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.q) query.set('q', params.q);
  const qs = query.toString();
  const url = `${getBaseUrl()}/admin/orders${qs ? `?${qs}` : ''}`;
  return requestWithTimeout<AdminOrderSummary[]>(url, {
    method: 'GET',
    credentials: 'include',
  });
}

export async function adminAdvanceOrder(orderNumber: string): Promise<AdminOrderSummary> {
  const url = `${getBaseUrl()}/admin/orders/${orderNumber}/advance`;
  return requestWithTimeout<AdminOrderSummary>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
  });
}

export async function adminCancelOrder(
  orderNumber: string,
  reason?: string
): Promise<AdminOrderSummary> {
  const url = `${getBaseUrl()}/admin/orders/${orderNumber}/cancel`;
  return requestWithTimeout<AdminOrderSummary>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
    body: JSON.stringify({ reason: reason || 'Cancelled by administrator' }),
  });
}

export async function getAdminRefunds(params?: {
  status?: string;
}): Promise<AdminRefundSummary[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  const qs = query.toString();
  const url = `${getBaseUrl()}/admin/refunds${qs ? `?${qs}` : ''}`;
  return requestWithTimeout<AdminRefundSummary[]>(url, {
    method: 'GET',
    credentials: 'include',
  });
}

export async function adminApproveRefundDirect(refundId: string): Promise<AdminRefundSummary> {
  const url = `${getBaseUrl()}/admin/refunds/${refundId}/approve`;
  return requestWithTimeout<AdminRefundSummary>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
  });
}

export async function adminRejectRefundDirect(
  refundId: string,
  reason: string
): Promise<AdminRefundSummary> {
  const url = `${getBaseUrl()}/admin/refunds/${refundId}/reject`;
  return requestWithTimeout<AdminRefundSummary>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'admin-console',
    },
    credentials: 'include',
    body: JSON.stringify({ reason }),
  });
}


