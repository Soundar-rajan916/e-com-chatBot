import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  getAdminWhatsAppStatus,
  pauseAdminWhatsApp,
  resumeAdminWhatsApp,
} from '../../api/client';
import { Agent } from '../../api/types';
import {
  AlertTriangleIcon,
  CheckCircleIcon,
  LinkIcon,
} from '../../components/icons';

interface WhatsAppStatusData {
  enabled: boolean;
  session_id: string;
  status: string;
  is_paused: boolean;
  phone: string | null;
  push_name: string | null;
  qr_code: string | null;
  risk_statement: string;
  dashboard_url: string;
  last_heartbeat: string | null;
}

export const WhatsAppConnectionPage: React.FC<{ currentAgent: Agent }> = ({ currentAgent: _currentAgent }) => {
  const [data, setData] = useState<WhatsAppStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await getAdminWhatsAppStatus();
      setData(res);
      setErrorMsg(null);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to fetch WhatsApp gateway status');
    } finally {
      setLoading(false);
    }
  };

  const handlePause = async () => {
    if (!window.confirm('Pause automated WhatsApp outbound replies? Customer messages will queue but no replies will be sent until resumed.')) {
      return;
    }
    setActionLoading(true);
    try {
      await pauseAdminWhatsApp();
      setSuccessMsg('WhatsApp outbound replies paused.');
      await fetchStatus();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to pause gateway');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async () => {
    setActionLoading(true);
    try {
      await resumeAdminWhatsApp();
      setSuccessMsg('WhatsApp outbound replies resumed.');
      await fetchStatus();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to resume gateway');
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (statusStr: string, isPaused: boolean) => {
    if (isPaused) {
      return { label: 'PAUSED', color: '#f59e0b', bg: '#fef3c7' };
    }
    switch (statusStr.toLowerCase()) {
      case 'ready':
        return { label: 'CONNECTED / READY', color: '#16a34a', bg: '#dcfce7' };
      case 'qr_ready':
      case 'initializing':
        return { label: 'SCAN QR CODE', color: '#ca8a04', bg: '#fef9c3' };
      case 'authenticating':
        return { label: 'AUTHENTICATING...', color: '#2563eb', bg: '#dbeafe' };
      case 'disconnected':
        return { label: 'DISCONNECTED', color: '#dc2626', bg: '#fee2e2' };
      default:
        return { label: statusStr.toUpperCase(), color: '#4b5563', bg: '#f3f4f6' };
    }
  };

  return (
    <div style={{ maxWidth: '1000px', margin: '2rem auto', padding: '0 1rem' }}>
      {/* Header and navigation */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 700, margin: 0 }}>WhatsApp Gateway Connection</h1>
          <p style={{ color: '#6b7280', margin: '0.25rem 0 0' }}>
            OpenWA Upstream Automation Gateway Integration & Channel Controls
          </p>
        </div>
        <NavLink
          to="/console"
          style={{
            padding: '0.5rem 1rem',
            background: '#f3f4f6',
            color: '#374151',
            borderRadius: '6px',
            textDecoration: 'none',
            fontWeight: 500,
          }}
        >
          ← Back to Inbox
        </NavLink>
      </div>

      {/* Prominent Risk Statement Notice */}
      <div
        style={{
          background: '#fffbeb',
          border: '1px solid #fde68a',
          borderRadius: '8px',
          padding: '1.25rem',
          marginBottom: '1.5rem',
        }}
      >
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
          <AlertTriangleIcon size={24} style={{ color: '#d97706', flexShrink: 0, marginTop: '2px' }} />
          <div>
            <h3 style={{ margin: '0 0 0.5rem', color: '#92400e', fontSize: '1rem', fontWeight: 600 }}>
              Operational Risk Disclosure
            </h3>
            <p style={{ margin: 0, color: '#78350f', fontSize: '0.9rem', lineHeight: 1.5 }}>
              {data?.risk_statement ||
                'open-wa is unofficial. WhatsApp may ban numbers that use unofficial clients, and WhatsApp Web changes can break the library without notice. Use a DEDICATED number that is not important to the owner, only REPLY to people who message first, never send bulk or unsolicited messages, and keep the official WhatsApp Business Cloud API as the documented production upgrade path.'}
            </p>
          </div>
        </div>
      </div>

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

      {/* Gateway Status Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Status Overview Card */}
        <div
          style={{
            background: '#fff',
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
            padding: '1.5rem',
          }}
        >
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem' }}>Connection Status</h2>
          {loading ? (
            <p>Loading gateway status...</p>
          ) : data ? (
            <div>
              <div style={{ marginBottom: '1rem' }}>
                <span style={{ fontSize: '0.85rem', color: '#6b7280', display: 'block', marginBottom: '0.25rem' }}>
                  Gateway State
                </span>
                {(() => {
                  const badge = getStatusBadge(data.status, data.is_paused);
                  return (
                    <span
                      style={{
                        background: badge.bg,
                        color: badge.color,
                        padding: '0.35rem 0.85rem',
                        borderRadius: '9999px',
                        fontWeight: 700,
                        fontSize: '0.85rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                    >
                      <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'currentColor' }} />
                      {badge.label}
                    </span>
                  );
                })()}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.9rem' }}>
                <div>
                  <span style={{ color: '#6b7280', fontSize: '0.8rem', display: 'block' }}>Session ID</span>
                  <span style={{ fontWeight: 500 }}>{data.session_id}</span>
                </div>
                <div>
                  <span style={{ color: '#6b7280', fontSize: '0.8rem', display: 'block' }}>Paired Phone</span>
                  <span style={{ fontWeight: 500 }}>{data.phone ? `+${data.phone}` : 'None'}</span>
                </div>
                <div>
                  <span style={{ color: '#6b7280', fontSize: '0.8rem', display: 'block' }}>Profile Push Name</span>
                  <span style={{ fontWeight: 500 }}>{data.push_name || '—'}</span>
                </div>
                <div>
                  <span style={{ color: '#6b7280', fontSize: '0.8rem', display: 'block' }}>Engine</span>
                  <span style={{ fontWeight: 500 }}>baileys (lightweight)</span>
                </div>
              </div>

              {/* Action Controls */}
              <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem' }}>
                {data.is_paused ? (
                  <button
                    type="button"
                    onClick={handleResume}
                    disabled={actionLoading}
                    style={{
                      background: '#16a34a',
                      color: '#fff',
                      border: 'none',
                      padding: '0.5rem 1rem',
                      borderRadius: '6px',
                      fontWeight: 600,
                      cursor: actionLoading ? 'not-allowed' : 'pointer',
                    }}
                  >
                    Resume Outbound Replies
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handlePause}
                    disabled={actionLoading}
                    style={{
                      background: '#f59e0b',
                      color: '#fff',
                      border: 'none',
                      padding: '0.5rem 1rem',
                      borderRadius: '6px',
                      fontWeight: 600,
                      cursor: actionLoading ? 'not-allowed' : 'pointer',
                    }}
                  >
                    Pause Outbound Replies
                  </button>
                )}
                <a
                  href={data.dashboard_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#f3f4f6',
                    color: '#1f2937',
                    borderRadius: '6px',
                    textDecoration: 'none',
                    fontWeight: 500,
                    fontSize: '0.9rem',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                  }}
                >
                  OpenWA Dashboard <LinkIcon size={14} />
                </a>
              </div>
            </div>
          ) : (
            <p>Could not load gateway status.</p>
          )}
        </div>

        {/* Pairing / QR Code Card */}
        <div
          style={{
            background: '#fff',
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
            padding: '1.5rem',
          }}
        >
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem' }}>Device Pairing (QR Code)</h2>
          {data?.qr_code ? (
            <div style={{ textAlign: 'center' }}>
              <div
                style={{
                  display: 'inline-block',
                  background: '#fff',
                  padding: '0.75rem',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  marginBottom: '1rem',
                }}
              >
                <img
                  src={data.qr_code}
                  alt="WhatsApp Pairing QR Code"
                  style={{ width: '220px', height: '220px', display: 'block' }}
                />
              </div>
              <p style={{ fontSize: '0.85rem', color: '#4b5563', margin: 0 }}>
                Open WhatsApp on your support phone &gt; Linked Devices &gt; Link a Device and scan this code.
              </p>
            </div>
          ) : data?.status === 'ready' ? (
            <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '0.75rem' }}>
                <CheckCircleIcon size={44} style={{ color: '#16a34a' }} />
              </div>
              <h3 style={{ fontSize: '1.1rem', color: '#16a34a', margin: '0 0 0.5rem' }}>Device Paired & Online</h3>
              <p style={{ fontSize: '0.85rem', color: '#6b7280', margin: 0 }}>
                This instance is linked and actively listening for incoming customer messages.
              </p>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '2rem 1rem', color: '#6b7280' }}>
              <p>No active pairing QR code requested. Device is starting or disconnected.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
