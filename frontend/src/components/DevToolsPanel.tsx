import React, { useEffect, useState } from 'react';
import { devAdvanceOrder, devSetDeliveredDaysAgo, getStoreConfig } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { SettingsIcon, CloseIcon } from './icons';

export const DevToolsPanel: React.FC = () => {
  const [isEnabled, setIsEnabled] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [orderNumber, setOrderNumber] = useState('');
  const [daysAgo, setDaysAgo] = useState(3);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const { login, customer } = useAuth();

  useEffect(() => {
    void getStoreConfig()
      .then((cfg) => {
        setIsEnabled(cfg.dev_tools);
      })
      .catch(() => {
        setIsEnabled(false);
      });
  }, []);

  if (!isEnabled) return null;

  const handleQuickLogin = async (num: number) => {
    try {
      setStatusMsg(`Switching to customer${num}...`);
      await login(`customer${num}@example.com`, 'CustomerPass123!');
      setStatusMsg(`Logged in as customer${num}@example.com`);
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (err: any) {
      setStatusMsg(`Login failed: ${err.message}`);
    }
  };

  const handleAdvance = async () => {
    if (!orderNumber.trim()) return;
    try {
      setStatusMsg(`Advancing order ${orderNumber}...`);
      const updated = await devAdvanceOrder(orderNumber.trim());
      setStatusMsg(`Order advanced to: ${updated.status}`);
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (err: any) {
      setStatusMsg(`Advance failed: ${err.message}`);
    }
  };

  const handleSetDeliveredDays = async () => {
    if (!orderNumber.trim()) return;
    try {
      setStatusMsg(`Setting order ${orderNumber} delivered ${daysAgo} days ago...`);
      const updated = await devSetDeliveredDaysAgo(orderNumber.trim(), daysAgo);
      setStatusMsg(`Updated delivery: ${daysAgo} days ago (Status: ${updated.status})`);
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (err: any) {
      setStatusMsg(`Failed: ${err.message}`);
    }
  };

  return (
    <aside className="dev-tools-wrapper" aria-label="Developer Tools">
      {!isOpen ? (
        <button
          type="button"
          className="dev-tools-toggle-btn"
          onClick={() => setIsOpen(true)}
          title="Open Developer Testing Tools"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <SettingsIcon size={14} /> Dev Tools
        </button>
      ) : (
        <div className="dev-tools-panel">
          <div className="dev-tools-header">
            <h3 style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <SettingsIcon size={16} /> Store Dev Tools
            </h3>
            <button
              type="button"
              className="dev-tools-close-btn"
              onClick={() => setIsOpen(false)}
              aria-label="Close Dev Tools"
            >
              <CloseIcon size={16} />
            </button>
          </div>

          {statusMsg && <div className="dev-tools-status">{statusMsg}</div>}

          <div className="dev-tools-section">
            <h4>Quick Switch Demo Customer</h4>
            <p className="dev-sub">
              Current: <strong>{customer ? customer.email : 'Guest (Logged Out)'}</strong>
            </p>
            <div className="demo-users-grid">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  type="button"
                  className="btn-demo-user"
                  onClick={() => void handleQuickLogin(n)}
                >
                  Cust {n}
                </button>
              ))}
            </div>
          </div>

          <div className="dev-tools-section">
            <h4>Order State Manipulation</h4>
            <div className="dev-input-row">
              <input
                type="text"
                placeholder="Order Number (e.g. ORD-202611-001)"
                value={orderNumber}
                onChange={(e) => setOrderNumber(e.target.value)}
              />
            </div>
            <div className="dev-actions-row">
              <button
                type="button"
                className="btn-dev-action"
                onClick={() => void handleAdvance()}
              >
                Advance Status &rarr;
              </button>
            </div>

            <div className="dev-input-row" style={{ marginTop: '0.5rem' }}>
              <input
                type="number"
                min="0"
                max="30"
                value={daysAgo}
                onChange={(e) => setDaysAgo(parseInt(e.target.value, 10) || 0)}
                style={{ width: '80px' }}
              />
              <button
                type="button"
                className="btn-dev-action"
                onClick={() => void handleSetDeliveredDays()}
              >
                Set Delivered Days Ago
              </button>
            </div>
          </div>

          <div className="dev-tools-section">
            <h4>Console &amp; Chat</h4>
            <div className="dev-links-row">
              <a href="/console" target="_blank" rel="noreferrer" className="btn-dev-link">
                Open Staff Console ↗
              </a>
              <a href="/dev/chat" className="btn-dev-link">
                Widget Debugger ↗
              </a>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
