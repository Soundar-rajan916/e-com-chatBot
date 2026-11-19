import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  generateCustomerWhatsAppLinkCode,
  getCustomerMe,
  getCustomerWhatsAppStatus,
  unlinkCustomerWhatsApp,
} from '../../api/client';
import { CustomerAccount } from '../../api/types';
import { ChatIcon, CheckIcon, LinkIcon, ClockIcon } from '../../components/icons';

export const AccountPage: React.FC = () => {
  const [customer, setCustomer] = useState<CustomerAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [waStatus, setWaStatus] = useState<{
    is_linked: boolean;
    phone_masked: string | null;
    opted_out: boolean;
  } | null>(null);

  // Link code state
  const [generatingCode, setGeneratingCode] = useState(false);
  const [linkData, setLinkData] = useState<{
    code: string;
    expires_in_seconds: number;
    wa_link: string | null;
  } | null>(null);
  const [timeLeft, setTimeLeft] = useState(0);

  // Unlink loading
  const [unlinking, setUnlinking] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (timeLeft <= 0) return;
    const interval = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [timeLeft]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [cust, wa] = await Promise.all([
        getCustomerMe(),
        getCustomerWhatsAppStatus().catch(() => null),
      ]);
      setCustomer(cust);
      if (wa) setWaStatus(wa);
    } catch {
      setCustomer(null);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateLinkCode = async () => {
    setGeneratingCode(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const data = await generateCustomerWhatsAppLinkCode();
      setLinkData({
        code: data.code,
        expires_in_seconds: data.expires_in_seconds,
        wa_link: data.wa_link,
      });
      setTimeLeft(data.expires_in_seconds);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to generate link code');
    } finally {
      setGeneratingCode(false);
    }
  };

  const handleUnlink = async () => {
    if (!window.confirm('Are you sure you want to unlink your WhatsApp account?')) return;
    setUnlinking(true);
    setErrorMsg(null);
    try {
      await unlinkCustomerWhatsApp();
      setWaStatus({ is_linked: false, phone_masked: null, opted_out: false });
      setLinkData(null);
      setSuccessMsg('WhatsApp account unlinked successfully.');
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to unlink WhatsApp');
    } finally {
      setUnlinking(false);
    }
  };

  if (loading) {
    return (
      <div className="store-container" style={{ padding: '3rem 1rem', textAlign: 'center' }}>
        <p>Loading account details...</p>
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="store-container" style={{ padding: '3rem 1rem', textAlign: 'center' }}>
        <h2>Sign In Required</h2>
        <p>Please sign in to view your account settings.</p>
        <NavLink to="/login" className="btn-primary" style={{ display: 'inline-block', marginTop: '1rem' }}>
          Sign In
        </NavLink>
      </div>
    );
  }

  return (
    <div className="store-container" style={{ maxWidth: '800px', margin: '2rem auto', padding: '0 1rem' }}>
      <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '1.5rem' }}>My Account</h1>

      {/* Customer Information Card */}
      <div
        style={{
          background: 'var(--card-bg, #fff)',
          borderRadius: '8px',
          border: '1px solid var(--border-color, #e5e7eb)',
          padding: '1.5rem',
          marginBottom: '1.5rem',
        }}
      >
        <h2 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '1rem' }}>Profile Information</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>Name</div>
            <div style={{ fontWeight: 500 }}>{customer.name}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>Phone</div>
            <div style={{ fontWeight: 500 }}>{customer.phone}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>Email</div>
            <div style={{ fontWeight: 500 }}>{customer.email || 'Not provided'}</div>
          </div>
        </div>
      </div>

      {/* WhatsApp Integration Card */}
      <div
        style={{
          background: 'var(--card-bg, #fff)',
          borderRadius: '8px',
          border: '1px solid var(--border-color, #e5e7eb)',
          padding: '1.5rem',
          marginBottom: '1.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ChatIcon size={22} />
            <h2 style={{ fontSize: '1.2rem', fontWeight: 600, margin: 0 }}>WhatsApp Assistant Support</h2>
          </div>
          {waStatus?.is_linked ? (
            <span
              style={{
                background: '#dcfce7',
                color: '#15803d',
                padding: '0.25rem 0.75rem',
                borderRadius: '9999px',
                fontSize: '0.8rem',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <CheckIcon size={12} /> Linked ({waStatus.phone_masked})
            </span>
          ) : (
            <span
              style={{
                background: '#f3f4f6',
                color: '#4b5563',
                padding: '0.25rem 0.75rem',
                borderRadius: '9999px',
                fontSize: '0.8rem',
                fontWeight: 600,
              }}
            >
              Not Linked
            </span>
          )}
        </div>

        <p style={{ color: '#4b5563', fontSize: '0.9rem', marginBottom: '1.25rem' }}>
          Connect your WhatsApp account to receive live order delivery updates, track packages, and initiate returns directly through WhatsApp chat.
        </p>

        {errorMsg && (
          <div style={{ background: '#fee2e2', color: '#b91c1c', padding: '0.75rem', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.9rem' }}>
            {errorMsg}
          </div>
        )}

        {successMsg && (
          <div style={{ background: '#dcfce7', color: '#15803d', padding: '0.75rem', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.9rem' }}>
            {successMsg}
          </div>
        )}

        {waStatus?.is_linked ? (
          <div>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <button
                type="button"
                onClick={handleUnlink}
                disabled={unlinking}
                style={{
                  background: '#fee2e2',
                  color: '#b91c1c',
                  border: 'none',
                  padding: '0.5rem 1rem',
                  borderRadius: '6px',
                  fontWeight: 500,
                  cursor: unlinking ? 'not-allowed' : 'pointer',
                }}
              >
                {unlinking ? 'Unlinking...' : 'Unlink WhatsApp'}
              </button>
            </div>
          </div>
        ) : (
          <div>
            {!linkData || timeLeft <= 0 ? (
              <button
                type="button"
                onClick={handleGenerateLinkCode}
                disabled={generatingCode}
                className="btn-primary"
                style={{
                  padding: '0.6rem 1.25rem',
                  fontWeight: 600,
                  cursor: generatingCode ? 'not-allowed' : 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <LinkIcon size={14} /> {generatingCode ? 'Generating Code...' : 'Link WhatsApp Account'}
              </button>
            ) : (
              <div
                style={{
                  background: '#f8fafc',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  padding: '1.25rem',
                }}
              >
                <div style={{ fontSize: '0.9rem', color: '#334155', marginBottom: '0.5rem' }}>
                  Your one-time linking code:
                </div>
                <div
                  style={{
                    fontSize: '2rem',
                    fontWeight: 700,
                    letterSpacing: '0.2em',
                    color: '#0f172a',
                    fontFamily: 'monospace',
                    marginBottom: '0.75rem',
                  }}
                >
                  {linkData.code}
                </div>
                <div style={{ fontSize: '0.85rem', color: timeLeft < 60 ? '#dc2626' : '#64748b', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <ClockIcon size={14} /> Code expires in <strong>{Math.floor(timeLeft / 60)}m {timeLeft % 60}s</strong>
                </div>

                <div style={{ fontSize: '0.9rem', color: '#334155', marginBottom: '1rem' }}>
                  Send <strong>LINK {linkData.code}</strong> to our WhatsApp support number.
                </div>

                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                  {linkData.wa_link && (
                    <a
                      href={linkData.wa_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-primary"
                      style={{
                        background: '#25D366',
                        borderColor: '#25D366',
                        color: '#fff',
                        textDecoration: 'none',
                        padding: '0.5rem 1rem',
                        borderRadius: '6px',
                        fontWeight: 600,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                      }}
                    >
                      <ChatIcon size={16} />
                      <span>Open in WhatsApp</span>
                    </a>
                  )}
                  <button
                    type="button"
                    onClick={handleGenerateLinkCode}
                    style={{
                      background: 'transparent',
                      border: '1px solid #cbd5e1',
                      padding: '0.5rem 1rem',
                      borderRadius: '6px',
                      cursor: 'pointer',
                    }}
                  >
                    Generate New Code
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
