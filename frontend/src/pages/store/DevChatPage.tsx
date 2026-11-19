import React, { useEffect } from 'react';
import { useSupportWidget } from '../../hooks/useSupportWidget';
import { SettingsIcon } from '../../components/icons';

export const DevChatPage: React.FC = () => {
  const { openWidget, closeWidget, toggleWidget, setWidgetContext } = useSupportWidget();

  useEffect(() => {
    // Open the widget automatically when mounting the dev chat page
    const timer = setTimeout(() => {
      openWidget();
    }, 300);
    return () => clearTimeout(timer);
  }, [openWidget]);

  return (
    <div className="dev-chat-page">
      <div className="dev-chat-card">
        <h1 style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
          <SettingsIcon size={24} /> Widget Dev &amp; Debugging Harness
        </h1>
        <p>
          This route (<code>/dev/chat</code>) verifies and exercises the standalone Support Chat
          Widget embedded in the Shadow DOM.
        </p>

        <div className="harness-actions">
          <h3>Widget Controls</h3>
          <div className="btn-group">
            <button type="button" className="btn-harness" onClick={openWidget}>
              Open Widget
            </button>
            <button type="button" className="btn-harness" onClick={closeWidget}>
              Close Widget
            </button>
            <button type="button" className="btn-harness" onClick={toggleWidget}>
              Toggle Widget
            </button>
          </div>

          <h3>Context Injection</h3>
          <div className="btn-group">
            <button
              type="button"
              className="btn-harness"
              onClick={() =>
                setWidgetContext({
                  type: 'product',
                  id: 'prod_demo_1',
                  title: 'Pure Kanchipuram Silk Saree (Gold Zari)',
                  price_inr: 8500,
                })
              }
            >
              Pin Product Context
            </button>
            <button
              type="button"
              className="btn-harness"
              onClick={() =>
                setWidgetContext({
                  type: 'order',
                  order_number: 'ORD-202611-001',
                  status: 'delivered',
                  total_amount_inr: 8500,
                })
              }
            >
              Pin Order Context
            </button>
            <button
              type="button"
              className="btn-harness"
              onClick={() => setWidgetContext({ type: 'none' })}
            >
              Clear Context
            </button>
          </div>

          <h3>Locale Switcher</h3>
          <div className="btn-group">
            <button
              type="button"
              className="btn-harness"
              onClick={() => {
                if (typeof window !== 'undefined' && window.SupportWidget) {
                  window.SupportWidget.setLocale('ta');
                }
              }}
            >
              Set Tamil (தமிழ்)
            </button>
            <button
              type="button"
              className="btn-harness"
              onClick={() => {
                if (typeof window !== 'undefined' && window.SupportWidget) {
                  window.SupportWidget.setLocale('en');
                }
              }}
            >
              Set English
            </button>
          </div>
        </div>

        <div className="harness-info">
          <h4>Features to test in Widget:</h4>
          <ul>
            <li>
              <strong>Bilingual Chat:</strong> Try asking in Tanglish (e.g., <em>"En order status enna?"</em>) or Tamil script or English.
            </li>
            <li>
              <strong>Context Awareness:</strong> Pinned products and orders are passed with chat messages.
            </li>
            <li>
              <strong>Order Lookups:</strong> When authenticated, asking <em>"Where is my order?"</em> looks up your orders.
            </li>
            <li>
              <strong>Anonymous Session Claiming:</strong> Chatting while logged out, then signing in preserves your chat history.
            </li>
            <li>
              <strong>Human Escalation &amp; Polling:</strong> When escalated, support executive responses appear automatically in real-time.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
