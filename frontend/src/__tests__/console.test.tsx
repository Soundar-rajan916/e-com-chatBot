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

      if (url.includes('/admin/orders/ORD-10001/advance')) {
        return Promise.resolve(new Response(JSON.stringify({
          id: 'ord-1',
          order_number: 'ORD-10001',
          customer_id: 'cust-1',
          customer_name: 'Priya Sharma',
          customer_phone: '+919876543210',
          customer_email: 'priya@example.com',
          status: 'processing',
          total_amount: 2999.00,
          total_amount_inr: 2999.00,
          placed_at: '2026-11-13T10:00:00Z',
          delivered_at: null,
          items_count: 1,
          items_summary: '1x Silk Saree',
          payment_method: 'demo_card',
          payment_status: 'paid',
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      if (url.includes('/admin/orders/ORD-10001/cancel')) {
        return Promise.resolve(new Response(JSON.stringify({
          id: 'ord-1',
          order_number: 'ORD-10001',
          customer_id: 'cust-1',
          customer_name: 'Priya Sharma',
          customer_phone: '+919876543210',
          customer_email: 'priya@example.com',
          status: 'cancelled',
          total_amount: 2999.00,
          total_amount_inr: 2999.00,
          placed_at: '2026-11-13T10:00:00Z',
          delivered_at: null,
          items_count: 1,
          items_summary: '1x Silk Saree',
          payment_method: 'demo_card',
          payment_status: 'paid',
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      if (url.includes('/admin/orders')) {
        return Promise.resolve(new Response(JSON.stringify([
          {
            id: 'ord-1',
            order_number: 'ORD-10001',
            customer_id: 'cust-1',
            customer_name: 'Priya Sharma',
            customer_phone: '+919876543210',
            customer_email: 'priya@example.com',
            status: 'placed',
            total_amount: 2999.00,
            total_amount_inr: 2999.00,
            placed_at: '2026-11-13T10:00:00Z',
            delivered_at: null,
            items_count: 1,
            items_summary: '1x Silk Saree',
            payment_method: 'demo_card',
            payment_status: 'paid',
          },
        ]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      if (url.includes('/admin/refunds/refund-1/approve')) {
        return Promise.resolve(new Response(JSON.stringify({
          id: 'refund-1',
          order_id: 'ord-1',
          order_number: 'ORD-10001',
          customer_id: 'cust-1',
          customer_name: 'Priya Sharma',
          amount: 2999.00,
          amount_inr: 2999.00,
          reason: 'Damaged item',
          status: 'processed',
          created_at: '2026-11-13T10:00:00Z',
          decided_by: 'agent:admin@example.com',
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      if (url.includes('/admin/refunds')) {
        return Promise.resolve(new Response(JSON.stringify([
          {
            id: 'refund-1',
            order_id: 'ord-1',
            order_number: 'ORD-10001',
            customer_id: 'cust-1',
            customer_name: 'Priya Sharma',
            amount: 2999.00,
            amount_inr: 2999.00,
            reason: 'Damaged item on delivery',
            status: 'pending_approval',
            created_at: '2026-11-13T10:00:00Z',
          },
        ]), {
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

  it('renders login page and displays streamlined Admin Console with only All Orders and Refunds', async () => {
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

    // Should show the streamlined Admin Console with All Orders active by default
    await waitFor(() => {
      expect(screen.getByText('Regional Bazaar Store Management')).toBeInTheDocument();
      expect(screen.getByText('Store Orders Management')).toBeInTheDocument();
      expect(screen.getByText('ORD-10001')).toBeInTheDocument();
      expect(screen.getByText('Push to Processing ➔')).toBeInTheDocument();
    });

    // Confirm that Support Tickets section has been removed completely
    expect(screen.queryByText('Support Tickets')).not.toBeInTheDocument();
    expect(screen.queryByText('Support Operations Inbox')).not.toBeInTheDocument();
    expect(screen.queryByText('Open Cases')).not.toBeInTheDocument();

    // Check Refunds tab
    const refundsTab = screen.getByText('Refunds');
    fireEvent.click(refundsTab);

    await waitFor(() => {
      expect(screen.getByText('Refunds & Returns Hub')).toBeInTheDocument();
      expect(screen.getByText('RETURN AMOUNT')).toBeInTheDocument();
      expect(screen.getByText('REASON OF RETURN')).toBeInTheDocument();
      expect(screen.getByText(/"Damaged item on delivery"/)).toBeInTheDocument();
      expect(screen.getByText('✓ Approve Refund')).toBeInTheDocument();
    });
  });

  it('allows advancing order stages in the All Orders tab', async () => {
    render(<App />);

    fireEvent.click(screen.getByText('Console'));
    await waitFor(() => expect(screen.getByText('Support Agent Login')).toBeInTheDocument());
    fireEvent.click(screen.getByText('👑 Demo Admin'));
    fireEvent.click(screen.getByText('Sign In to Console'));

    await waitFor(() => expect(screen.getByText('Store Orders Management')).toBeInTheDocument());

    // Click advance stage
    const advanceBtn = screen.getByText('Push to Processing ➔');
    fireEvent.click(advanceBtn);

    await waitFor(() => {
      expect(screen.getByText(/Order ORD-10001 advanced to PROCESSING/i)).toBeInTheDocument();
    });
  });

  it('allows approving refunds in the Refunds tab', async () => {
    render(<App />);

    fireEvent.click(screen.getByText('Console'));
    await waitFor(() => expect(screen.getByText('Support Agent Login')).toBeInTheDocument());
    fireEvent.click(screen.getByText('👑 Demo Admin'));
    fireEvent.click(screen.getByText('Sign In to Console'));

    // Switch to Refunds tab
    await waitFor(() => expect(screen.getByText('Refunds')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Refunds'));

    await waitFor(() => expect(screen.getByText('✓ Approve Refund')).toBeInTheDocument());

    // Approve the pending refund
    fireEvent.click(screen.getByText('✓ Approve Refund'));

    await waitFor(() => {
      expect(screen.getByText(/approved and paid successfully/i)).toBeInTheDocument();
    });
  });
});
