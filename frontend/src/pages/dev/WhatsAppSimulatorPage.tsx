import React, { useEffect, useRef, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { getBaseUrl } from '../../api/client';
import { BagIcon, CheckIcon, ArrowRightIcon, InfoIcon } from '../../components/icons';

interface ChatBubble {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  timestamp: string;
}

export const WhatsAppSimulatorPage: React.FC = () => {
  const [phone, setPhone] = useState('919876543210');
  const [messages, setMessages] = useState<ChatBubble[]>([
    {
      id: 'init-1',
      sender: 'bot',
      text: 'Welcome to Regional Store Support on WhatsApp!\n\nSend *LINK <code>* to connect your customer account, or ask any question about our products and order status.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if (!text || sending) return;

    const userBubble: ChatBubble = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userBubble]);
    if (!textToSend) setInputText('');
    setSending(true);
    setStatusMsg(null);

    try {
      // Deliver simulated incoming message payload to backend webhook
      const chatId = `${phone}@c.us`;
      const payload = {
        event: 'message.received',
        sessionId: 'ecom-store',
        idempotencyKey: `sim_${Date.now()}_${Math.random().toString(36).substring(7)}`,
        deliveryId: `dlv_${Date.now()}`,
        timestamp: new Date().toISOString(),
        data: {
          id: `msg_${Date.now()}`,
          from: chatId,
          to: '918000000000@c.us',
          chatId,
          body: text,
          type: 'text',
          fromMe: false,
          isGroup: false,
          kind: 'individual',
          senderPhone: phone,
          timestamp: Math.floor(Date.now() / 1000),
        },
      };

      const webhookUrl = `${getBaseUrl()}/whatsapp/openwa/webhook`;
      const res = await fetch(webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-OpenWA-Event': 'message.received',
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Webhook returned status ${res.status}`);
      }

      // Simulate network delivery and bot reply delay
      setTimeout(() => {
        // Poll latest reply or simulate pipeline response
        fetch(`${getBaseUrl()}/admin/orders`)
          .catch(() => null);
      }, 1500);

    } catch (err: unknown) {
      setStatusMsg(err instanceof Error ? err.message : 'Error delivering message');
    } finally {
      setSending(false);
    }
  };

  const quickActions = [
    'Where is my order ORD-10001?',
    'Refund ORD-10001 size issue',
    'LINK 123456',
    'YES 7X3K',
    'STOP',
    'START',
    'UNLINK',
  ];

  return (
    <div style={{ maxWidth: '900px', margin: '2rem auto', padding: '0 1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 700, margin: 0 }}>WhatsApp Channel Dev Simulator</h1>
          <p style={{ color: '#6b7280', margin: '0.25rem 0 0' }}>
            Simulate real customer WhatsApp messages and test auto-replies, link codes, and typed confirmations
          </p>
        </div>
        <NavLink
          to="/"
          style={{
            padding: '0.5rem 1rem',
            background: '#f3f4f6',
            color: '#374151',
            borderRadius: '6px',
            textDecoration: 'none',
            fontWeight: 500,
          }}
        >
          ← Storefront
        </NavLink>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 420px) 1fr', gap: '2rem', alignItems: 'flex-start' }}>
        {/* WhatsApp Mobile Frame */}
        <div
          style={{
            width: '100%',
            maxWidth: '400px',
            background: '#efeae2',
            borderRadius: '24px',
            overflow: 'hidden',
            border: '8px solid #1f2937',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
            display: 'flex',
            flexDirection: 'column',
            height: '600px',
          }}
        >
          {/* WhatsApp Header */}
          <div
            style={{
              background: '#075e54',
              color: '#fff',
              padding: '0.75rem 1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
            }}
          >
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: '#25d366',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
              }}
            >
              <BagIcon size={18} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>Store Support</div>
              <div style={{ fontSize: '0.75rem', opacity: 0.85 }}>Online</div>
            </div>
            <div style={{ fontSize: '1.2rem', cursor: 'pointer' }}>⋮</div>
          </div>

          {/* Messages Area */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            {messages.map((m) => (
              <div
                key={m.id}
                style={{
                  alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '80%',
                  background: m.sender === 'user' ? '#d9fdd3' : '#ffffff',
                  borderRadius: '8px',
                  padding: '0.5rem 0.75rem',
                  fontSize: '0.9rem',
                  color: '#111827',
                  boxShadow: '0 1px 0.5px rgba(0,0,0,0.13)',
                  whiteSpace: 'pre-wrap',
                }}
              >
                <div>{m.text}</div>
                <div
                  style={{
                    fontSize: '0.65rem',
                    color: '#6b7280',
                    textAlign: 'right',
                    marginTop: '0.25rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    gap: '0.25rem',
                  }}
                >
                  <span>{m.timestamp}</span>
                  {m.sender === 'user' && (
                    <span style={{ color: '#53bdeb', display: 'inline-flex', alignItems: 'center' }}>
                      <CheckIcon size={11} />
                      <CheckIcon size={11} style={{ marginLeft: '-5px' }} />
                    </span>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            style={{
              background: '#f0f2f5',
              padding: '0.5rem 0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Type a message..."
              disabled={sending}
              style={{
                flex: 1,
                border: 'none',
                borderRadius: '8px',
                padding: '0.5rem 0.75rem',
                fontSize: '0.9rem',
                outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={sending || !inputText.trim()}
              style={{
                background: '#075e54',
                color: '#fff',
                border: 'none',
                borderRadius: '50%',
                width: '36px',
                height: '36px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: sending || !inputText.trim() ? 'not-allowed' : 'pointer',
              }}
              aria-label="Send message"
            >
              <ArrowRightIcon size={16} />
            </button>
          </form>
        </div>

        {/* Controls & Quick Test Triggers */}
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '1.5rem' }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem' }}>Simulator Settings</h2>

          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', color: '#6b7280', marginBottom: '0.25rem' }}>
              Simulated Customer Phone (E.164 without +)
            </label>
            <input
              type="text"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              style={{
                width: '100%',
                padding: '0.5rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '0.9rem',
              }}
            />
          </div>

          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Quick Test Actions</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1.5rem' }}>
            {quickActions.map((qa) => (
              <button
                key={qa}
                type="button"
                onClick={() => handleSend(qa)}
                disabled={sending}
                style={{
                  background: '#f3f4f6',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px',
                  padding: '0.4rem 0.75rem',
                  fontSize: '0.8rem',
                  cursor: sending ? 'not-allowed' : 'pointer',
                  fontWeight: 500,
                }}
              >
                {qa}
              </button>
            ))}
          </div>

          {statusMsg && (
            <div style={{ padding: '0.75rem', background: '#fee2e2', color: '#b91c1c', borderRadius: '6px', fontSize: '0.85rem' }}>
              {statusMsg}
            </div>
          )}

          <div style={{ borderTop: '1px solid #e5e7eb', paddingTop: '1rem', color: '#6b7280', fontSize: '0.85rem', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
            <InfoIcon size={14} style={{ marginTop: '2px', flexShrink: 0 }} />
            <span>Messages sent here hit the backend webhook <code>/whatsapp/openwa/webhook</code>, trigger the inbound worker under advisory locking, and run the assistant pipeline.</span>
          </div>
        </div>
      </div>
    </div>
  );
};
