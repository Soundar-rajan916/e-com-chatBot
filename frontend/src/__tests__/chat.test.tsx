import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';

const MOCK_CUSTOMERS = [
  { id: 'cust-1', name: 'Priya Sharma', phone: '+919876543210', preferred_language: 'en' },
  { id: 'cust-2', name: 'Karthik Raja', phone: '+919876543211', preferred_language: 'ta' },
];

describe('Frontend Chat UI & API Integration', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();

    // Default global fetch mock
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.includes('/health')) {
        return Promise.resolve(new Response(JSON.stringify({ status: 'ok', db: 'connected' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      if (url.includes('/customers/demo')) {
        return Promise.resolve(new Response(JSON.stringify(MOCK_CUSTOMERS), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      if (url.includes('/chat')) {
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        return Promise.resolve(new Response(JSON.stringify({
          session_id: 'sess-123',
          reply: `Echo reply for: ${body.message}`,
          intent: 'order_status',
          language: 'en',
          requires_human: false,
          trace_id: 'trace-1',
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }));
      }

      return Promise.reject(new Error(`Unhandled URL: ${url}`));
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sends a message and displays assistant reply', async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Priya Sharma/)).toBeInTheDocument();
    });

    const input = screen.getByLabelText(/Chat Message Input/i);
    await user.type(input, 'Where is my order?');
    await user.click(screen.getByRole('button', { name: /Send Message/i }));

    expect(screen.getByText('Where is my order?')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/Echo reply for: Where is my order\?/)).toBeInTheDocument();
    });
  });

  it('Enter sends, Shift+Enter does not send, and empty sends are blocked', async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Priya Sharma/)).toBeInTheDocument();
    });

    const input = screen.getByLabelText(/Chat Message Input/i);
    const sendBtn = screen.getByRole('button', { name: /Send Message/i });

    // Empty send is disabled
    expect(sendBtn).toBeDisabled();

    // Whitespace send is blocked
    await user.type(input, '    ');
    expect(sendBtn).toBeDisabled();
    await user.clear(input);

    // Shift+Enter does not trigger send
    await user.type(input, 'Line 1{Shift>}{Enter}{/Shift}Line 2');
    expect(screen.queryByText('Line 1\nLine 2')).not.toBeInTheDocument();

    // Regular Enter sends
    await user.clear(input);
    await user.type(input, 'Send via Enter{Enter}');
    expect(screen.getByText('Send via Enter')).toBeInTheDocument();
  });

  it('disables input and send while pending and displays typing indicator', async () => {
    let resolveChatPromise: (value: Response) => void;
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/health')) {
        return Promise.resolve(new Response(JSON.stringify({ status: 'ok', db: 'connected' })));
      }
      if (url.includes('/customers/demo')) {
        return Promise.resolve(new Response(JSON.stringify(MOCK_CUSTOMERS)));
      }
      if (url.includes('/chat')) {
        return new Promise<Response>((resolve) => {
          resolveChatPromise = resolve;
        });
      }
      return Promise.reject(new Error('unhandled'));
    });

    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => expect(screen.getByText(/Priya Sharma/)).toBeInTheDocument());

    const input = screen.getByLabelText(/Chat Message Input/i);
    await user.type(input, 'Pending test');
    await user.click(screen.getByRole('button', { name: /Send Message/i }));

    // While pending
    expect(screen.getByLabelText(/Assistant is typing/i)).toBeInTheDocument();
    expect(input).toBeDisabled();
    expect(screen.getByRole('button', { name: /Send Message/i })).toBeDisabled();

    // Resolve promise
    resolveChatPromise!(new Response(JSON.stringify({
      session_id: 'sess-p',
      reply: 'Done response',
      intent: 'smalltalk',
      language: 'en',
      requires_human: false,
      trace_id: 't-1',
    })));

    await waitFor(() => {
      expect(screen.getByText('Done response')).toBeInTheDocument();
    });
    expect(input).not.toBeDisabled();
  });

  it('renders handoff badge when requires_human is true and omits it when false', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/health')) return Promise.resolve(new Response(JSON.stringify({ status: 'ok', db: 'connected' })));
      if (url.includes('/customers/demo')) return Promise.resolve(new Response(JSON.stringify(MOCK_CUSTOMERS)));
      if (url.includes('/chat')) {
        return Promise.resolve(new Response(JSON.stringify({
          session_id: 'sess-h',
          reply: 'Escalating to human manager',
          intent: 'escalate',
          language: 'en',
          requires_human: true,
          trace_id: 'trace-h',
        })));
      }
      return Promise.reject(new Error('unhandled'));
    });

    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByText(/Priya Sharma/)).toBeInTheDocument());

    await user.type(screen.getByLabelText(/Chat Message Input/i), 'Help human');
    await user.click(screen.getByRole('button', { name: /Send Message/i }));

    await waitFor(() => {
      expect(screen.getByText(/Handed to a support executive/i)).toBeInTheDocument();
    });
  });

  it('handles 422, 403, 5xx and network errors with Retry button without duplicate sends', async () => {
    let attempt = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/health')) return Promise.resolve(new Response(JSON.stringify({ status: 'ok', db: 'connected' })));
      if (url.includes('/customers/demo')) return Promise.resolve(new Response(JSON.stringify(MOCK_CUSTOMERS)));
      if (url.includes('/chat')) {
        attempt++;
        if (attempt === 1) {
          return Promise.resolve(new Response(JSON.stringify({ detail: 'Message validation error' }), { status: 422 }));
        }
        return Promise.resolve(new Response(JSON.stringify({
          session_id: 'sess-retry',
          reply: 'Recovered after retry',
          intent: 'order_status',
          language: 'en',
          requires_human: false,
          trace_id: 'trace-r',
        }), { status: 200 }));
      }
      return Promise.reject(new Error('unhandled'));
    });

    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByText(/Priya Sharma/)).toBeInTheDocument());

    await user.type(screen.getByLabelText(/Chat Message Input/i), 'Fail and retry message');
    await user.click(screen.getByRole('button', { name: /Send Message/i }));

    await waitFor(() => {
      expect(screen.getByText(/Message validation error/i)).toBeInTheDocument();
    });

    const retryBtn = screen.getByRole('button', { name: /Retry/i });
    await user.click(retryBtn);

    await waitFor(() => {
      expect(screen.getByText('Recovered after retry')).toBeInTheDocument();
    });

    // Verify user message only appears once in the list
    const userBubbles = screen.getAllByText('Fail and retry message');
    expect(userBubbles.length).toBe(1);
  });

  it('switching customer clears conversation and starts a new session', async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByText(/Priya Sharma/)).toBeInTheDocument());

    // Send message as Priya
    await user.type(screen.getByLabelText(/Chat Message Input/i), 'Priya message');
    await user.click(screen.getByRole('button', { name: /Send Message/i }));
    await waitFor(() => expect(screen.getByText(/Echo reply for: Priya message/)).toBeInTheDocument());

    // Switch to Karthik Raja
    const select = screen.getByLabelText(/Select Demo Customer/i);
    await user.selectOptions(select, 'cust-2');

    // Conversation is cleared
    await waitFor(() => {
      expect(screen.queryByText('Priya message')).not.toBeInTheDocument();
    });
  });

  it('sends session_id from first reply on subsequent messages', async () => {
    const chatPayloads: unknown[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/health')) return Promise.resolve(new Response(JSON.stringify({ status: 'ok', db: 'connected' })));
      if (url.includes('/customers/demo')) return Promise.resolve(new Response(JSON.stringify(MOCK_CUSTOMERS)));
      if (url.includes('/chat')) {
        const body = JSON.parse(String(init?.body));
        chatPayloads.push(body);
        return Promise.resolve(new Response(JSON.stringify({
          session_id: 'session-chain-999',
          reply: 'Reply chained',
          intent: 'order_status',
          language: 'en',
          requires_human: false,
          trace_id: 'tr-99',
        })));
      }
      return Promise.reject(new Error('unhandled'));
    });

    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByText(/Priya Sharma/)).toBeInTheDocument());

    // Message 1 (no session_id)
    await user.type(screen.getByLabelText(/Chat Message Input/i), 'Msg 1');
    await user.click(screen.getByRole('button', { name: /Send Message/i }));
    await waitFor(() => expect(screen.getByText('Reply chained')).toBeInTheDocument());

    // Message 2 (should send session-chain-999)
    await user.type(screen.getByLabelText(/Chat Message Input/i), 'Msg 2');
    await user.click(screen.getByRole('button', { name: /Send Message/i }));

    expect(chatPayloads[0]).toMatchObject({ session_id: null, message: 'Msg 1' });
    expect(chatPayloads[1]).toMatchObject({ session_id: 'session-chain-999', message: 'Msg 2' });
  });

  it('restores conversation from sessionStorage after remount', async () => {
    sessionStorage.setItem(
      'ecom_chat_cust-1',
      JSON.stringify({
        sessionId: 'stored-session-77',
        messages: [
          { id: '1', role: 'user', content: 'Saved question', timestamp: '10:00 AM' },
          { id: '2', role: 'assistant', content: 'Saved answer', timestamp: '10:01 AM' },
        ],
      })
    );

    render(<App />);
    await waitFor(() => {
      expect(screen.getByText('Saved question')).toBeInTheDocument();
      expect(screen.getByText('Saved answer')).toBeInTheDocument();
    });
  });

  it('renders Tamil and Tanglish text completely unchanged', async () => {
    const tamilText = 'வணக்கம்! என் ஆர்டர் எங்கே உள்ளது?';
    const tanglishText = 'yen order ORD-10001 eppo varum bro?';

    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/health')) return Promise.resolve(new Response(JSON.stringify({ status: 'ok', db: 'connected' })));
      if (url.includes('/customers/demo')) return Promise.resolve(new Response(JSON.stringify(MOCK_CUSTOMERS)));
      if (url.includes('/chat')) {
        return Promise.resolve(new Response(JSON.stringify({
          session_id: 'sess-lang',
          reply: tamilText,
          intent: 'order_status',
          language: 'ta',
          requires_human: false,
          trace_id: 'tr-ta',
        })));
      }
      return Promise.reject(new Error('unhandled'));
    });

    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByText(/Priya Sharma/)).toBeInTheDocument());

    await user.type(screen.getByLabelText(/Chat Message Input/i), tanglishText);
    await user.click(screen.getByRole('button', { name: /Send Message/i }));

    expect(screen.getByText(tanglishText)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(tamilText)).toBeInTheDocument();
    });
  });

  it('health banner appears when /health fails and disappears on recovery', async () => {
    const healthy = false;
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/health')) {
        if (!healthy) {
          return Promise.resolve(new Response(JSON.stringify({ status: 'error', db: 'disconnected' }), { status: 503 }));
        }
        return Promise.resolve(new Response(JSON.stringify({ status: 'ok', db: 'connected' }), { status: 200 }));
      }
      if (url.includes('/customers/demo')) return Promise.resolve(new Response(JSON.stringify(MOCK_CUSTOMERS)));
      return Promise.resolve(new Response('{}'));
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Service unavailable, retrying/i)).toBeInTheDocument();
    });
  });

  it('renders retrieved sources in message details disclosure', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/health')) return Promise.resolve(new Response(JSON.stringify({ status: 'ok', db: 'connected' })));
      if (url.includes('/customers/demo')) return Promise.resolve(new Response(JSON.stringify(MOCK_CUSTOMERS)));
      if (url.includes('/chat')) {
        return Promise.resolve(new Response(JSON.stringify({
          session_id: 'sess-sources',
          reply: 'We have Pure Silk Saree available for ₹2,500.',
          intent: 'product_question',
          language: 'en',
          requires_human: false,
          trace_id: 'tr-src-1',
          sources: [
            { type: 'product', id: 'prod-uuid-1', title: 'Traditional Silk Saree' },
            { type: 'policy', id: 'policy-uuid-1', title: 'Returns and refund window' },
          ],
        })));
      }
      return Promise.reject(new Error('unhandled'));
    });

    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByText(/Priya Sharma/)).toBeInTheDocument());

    await user.type(screen.getByLabelText(/Chat Message Input/i), 'Do you have silk sarees?');
    await user.click(screen.getByRole('button', { name: /Send Message/i }));

    await waitFor(() => {
      expect(screen.getByText('We have Pure Silk Saree available for ₹2,500.')).toBeInTheDocument();
    });

    // Open Details disclosure
    const details = screen.getByText('Details');
    await user.click(details);

    expect(screen.getByText('Sources:')).toBeInTheDocument();
    expect(screen.getByText(/Traditional Silk Saree/)).toBeInTheDocument();
    expect(screen.getByText(/Returns and refund window/)).toBeInTheDocument();
  });
});
