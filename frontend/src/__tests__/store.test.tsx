import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import App from '../App';

const MOCK_CONFIG = {
  store_name: 'Regional Bazaar',
  return_window_days: 7,
  supported_languages: ['en', 'ta'],
  dev_tools: true,
  chat_widget_enabled: true,
};

const MOCK_CATEGORIES = ['Textiles', 'Cookware', 'Groceries'];

const MOCK_PRODUCTS = {
  items: [
    {
      id: 'prod-1',
      sku: 'SKU-001',
      title: 'Kanchipuram Silk Saree',
      title_ta: 'காஞ்சிபுரம் பட்டுப் புடவை',
      description: 'Pure mulberry silk with zari border',
      description_ta: 'தூய மல்பெரி பட்டு',
      category: 'Textiles',
      price_inr: 8500,
      stock: 12,
      is_active: true,
    },
    {
      id: 'prod-2',
      sku: 'SKU-002',
      title: 'Traditional Kalchatti Stone Cookware',
      title_ta: 'கல்சட்டி',
      description: 'Handcrafted soapstone vessel',
      description_ta: 'பாரம்பரிய மாக்கல் சட்டி',
      category: 'Cookware',
      price_inr: 2200,
      stock: 4,
      is_active: true,
    },
  ],
  total: 2,
  page: 1,
  page_size: 16,
  total_pages: 1,
};

const MOCK_CART = {
  items: [
    {
      product_id: 'prod-1',
      sku: 'SKU-001',
      title: 'Kanchipuram Silk Saree',
      price_inr: 8500,
      quantity: 1,
      subtotal_inr: 8500,
      in_stock: true,
      stock_available: 12,
    },
  ],
  total_items: 1,
  subtotal_inr: 8500,
  shipping_fee_inr: 0,
  total_inr: 8500,
  is_checkout_ready: true,
};

describe('Storefront UI & Customer Workflows', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();

    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes('/health')) {
        return Promise.resolve(
          new Response(JSON.stringify({ status: 'ok', db: 'connected' }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }

      if (url.includes('/config')) {
        return Promise.resolve(
          new Response(JSON.stringify(MOCK_CONFIG), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }

      if (url.includes('/categories')) {
        return Promise.resolve(
          new Response(JSON.stringify(MOCK_CATEGORIES), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }

      if (url.includes('/products/prod-1/related')) {
        return Promise.resolve(
          new Response(JSON.stringify([]), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }

      if (url.includes('/products/prod-1')) {
        return Promise.resolve(
          new Response(JSON.stringify(MOCK_PRODUCTS.items[0]), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }

      if (url.includes('/products')) {
        return Promise.resolve(
          new Response(JSON.stringify(MOCK_PRODUCTS), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }

      if (url.includes('/policy')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              policy_name: 'returns',
              language: 'en',
              content_markdown: '7-day easy return policy',
              updated_at: '2026-11-13T00:00:00Z',
            }),
            {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            }
          )
        );
      }

      if (url.includes('/cart/items')) {
        return Promise.resolve(
          new Response(JSON.stringify(MOCK_CART), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }

      if (url.includes('/cart')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [],
              total_items: 0,
              subtotal_inr: 0,
              shipping_fee_inr: 0,
              total_inr: 0,
              is_checkout_ready: true,
            }),
            {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            }
          )
        );
      }

      if (url.includes('/auth/me')) {
        return Promise.resolve(
          new Response(JSON.stringify({ detail: 'Not authenticated' }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }

      return Promise.reject(new Error(`Unhandled mock URL in test: ${url}`));
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders storefront navigation, hero banner, and featured products', async () => {
    render(<App />);

    // Brand and navigation
    expect(screen.getByText('Regional Bazaar')).toBeInTheDocument();
    expect(screen.getByText('Products')).toBeInTheDocument();

    // Hero title
    expect(
      screen.getByText('Experience the Finest Products of Tamil Nadu')
    ).toBeInTheDocument();

    // Featured products loaded
    await waitFor(() => {
      expect(screen.getByText('Kanchipuram Silk Saree')).toBeInTheDocument();
      expect(screen.getByText('Traditional Kalchatti Stone Cookware')).toBeInTheDocument();
      expect(screen.getByText('₹8,500')).toBeInTheDocument();
    });
  });

  it('adds product to cart and updates cart count', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Kanchipuram Silk Saree')).toBeInTheDocument();
    });

    const addBtns = screen.getAllByRole('button', { name: 'Add to Cart' });
    fireEvent.click(addBtns[0]);

    await waitFor(() => {
      const badge = screen.getByText('1');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('cart-badge');
    });
  });

  it('displays health alert banner when /health reports error', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/health')) {
        return Promise.resolve(
          new Response(JSON.stringify({ status: 'degraded', db: 'disconnected' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify({}), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });
});
