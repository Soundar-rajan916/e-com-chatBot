import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from '../App';

describe('Admin Console Frontend Workflows', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();

    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.includes('/health')) {
        return Promise.resolve(new Response(JSON.stringify({ status: 'ok', db: 'connected' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      if (url.includes('/customers/demo')) {
        return Promise.resolve(new Response(JSON.stringify([]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      if (url.includes('/admin/auth/me')) {
        return Promise.resolve(new Response(JSON.stringify({ detail: 'Authentication required' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      if (url.includes('/admin/auth/login')) {
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        if (body.email === 'admin@example.com' && body.password === 'AdminPass123!') {
          return Promise.resolve(new Response(JSON.stringify({
            id: 'agent-uuid-1',
            email: 'admin@example.com',
            name: 'Demo Admin',
            role: 'admin',
          }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }));
        }
        return Promise.resolve(new Response(JSON.stringify({ detail: 'Invalid email or password.' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      if (url.includes('/admin/escalations/stats')) {
        return Promise.resolve(new Response(JSON.stringify({
          open_count: 3,
          in_progress_count: 1,
          resolved_count: 5,
          overdue_count: 1,
          unassigned_count: 2,
          my_open_count: 1,
          by_reason_type: { refund_pending_approval: 1, user_requested: 2 },
          avg_response_time_seconds: 45,
          avg_resolution_time_seconds: 320,
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      if (url.includes('/admin/escalations/esc-123')) {
        return Promise.resolve(new Response(JSON.stringify({
          escalation: {
            id: 'esc-123',
            session_id: 'sess-123',
            customer_id: 'cust-1',
            customer_name: 'Priya Sharma',
            customer_phone_masked: '+9198*** **210',
            reason: 'High-value refund request for silk saree',
            reason_type: 'refund_pending_approval',
            status: 'open',
            priority: 'high',
            assigned_to: null,
            assigned_agent_name: null,
            refund_id: 'refund-1',
            order_number: 'ORD-10001',
            is_overdue: true,
            version: 1,
            created_at: '2026-11-13T10:00:00Z',
            updated_at: '2026-11-13T10:00:00Z',
            first_response_at: null,
            resolved_at: null,
            resolution_note: null,
          },
          customer: {
            id: 'cust-1',
            name: 'Priya Sharma',
            phone: '+919876543210',
            preferred_language: 'en',
            created_at: '2026-11-01T00:00:00Z',
          },
          recent_orders: [
            {
              id: 'ord-1',
              order_number: 'ORD-10001',
              status: 'delivered',
              total_amount_inr: '2999.00',
              created_at: '2026-11-08T00:00:00Z',
              items: [{ product_title: 'Silk Saree', quantity: 1, unit_price_inr: '2999.00' }],
            },
          ],
          refund: {
            id: 'refund-1',
            order_id: 'ord-1',
            order_number: 'ORD-10001',
            amount: '2999.00',
            reason: 'Damaged item',
            status: 'pending_approval',
            created_at: '2026-11-13T10:00:00Z',
          },
          messages: [
            {
              id: 'msg-1',
              session_id: 'sess-123',
              role: 'user',
              content: 'I want a refund for ORD-10001',
              agent_id: null,
              agent_name: null,
              input_mode: 'text',
              created_at: '2026-11-13T10:00:00Z',
            },
          ],
          traces: [],
          notes: [],
          events: [
            {
              id: 'ev-1',
              actor_type: 'system',
              actor_id: null,
              actor_name: 'System',
              action: 'created',
              detail: {},
              created_at: '2026-11-13T10:00:00Z',
            },
          ],
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      if (url.includes('/admin/escalations')) {
        return Promise.resolve(new Response(JSON.stringify({
          items: [
            {
              id: 'esc-123',
              session_id: 'sess-123',
              customer_id: 'cust-1',
              customer_name: 'Priya Sharma',
              customer_phone_masked: '+9198*** **210',
              reason: 'High-value refund request for silk saree',
              reason_type: 'refund_pending_approval',
              status: 'open',
              priority: 'high',
              assigned_to: null,
              assigned_agent_name: null,
              refund_id: 'refund-1',
              order_number: 'ORD-10001',
              is_overdue: true,
              version: 1,
              created_at: '2026-11-13T10:00:00Z',
              updated_at: '2026-11-13T10:00:00Z',
              first_response_at: null,
              resolved_at: null,
              resolution_note: null,
            },
          ],
          total: 1,
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      return Promise.reject(new Error(`Unhandled mock URL: ${url}`));
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders login page when clicking Console tab and logs in successfully', async () => {
    render(<App />);

    // Click Console nav link
    const consoleLink = screen.getByText('Console');
    fireEvent.click(consoleLink);

    // Should see Support Agent Login
    await waitFor(() => {
      expect(screen.getByText('Support Agent Login')).toBeInTheDocument();
    });

    // Click quick fill Demo Admin
    const adminBtn = screen.getByText('👑 Demo Admin');
    fireEvent.click(adminBtn);

    const submitBtn = screen.getByText('Sign In to Console');
    fireEvent.click(submitBtn);

    // Should transition to Support Operations Inbox
    await waitFor(() => {
      expect(screen.getByText('Support Operations Inbox')).toBeInTheDocument();
      expect(screen.getByText('Open Cases')).toBeInTheDocument();
      expect(screen.getByText('Priya Sharma')).toBeInTheDocument();
      expect(screen.getByText('+9198*** **210')).toBeInTheDocument();
    });
  });

  it('navigates to case detail workspace and displays unmasked phone, orders, and refund action', async () => {
    render(<App />);

    // Click Console nav link
    fireEvent.click(screen.getByText('Console'));
    await waitFor(() => expect(screen.getByText('Support Agent Login')).toBeInTheDocument());

    // Login
    fireEvent.click(screen.getByText('👑 Demo Admin'));
    fireEvent.click(screen.getByText('Sign In to Console'));

    await waitFor(() => expect(screen.getByText('Support Operations Inbox')).toBeInTheDocument());

    // Click Open Case button
    const openBtn = screen.getByText('Open Case');
    fireEvent.click(openBtn);

    // Should be in case workspace
    await waitFor(() => {
      expect(screen.getByText(/Case #esc-123/)).toBeInTheDocument();
      expect(screen.getByText('+919876543210')).toBeInTheDocument(); // Unmasked in detail
      expect(screen.getByText('Recent Orders (1)')).toBeInTheDocument();
      expect(screen.getByText('Linked Refund Action')).toBeInTheDocument();
      expect(screen.getByText('✅ Approve & Payout')).toBeInTheDocument();
      expect(screen.getByText('Conversation Transcript')).toBeInTheDocument();
    });
  });
});
