import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  addEscalationNote,
  ApiError,
  approveRefund,
  assignEscalation,
  getEscalationDetail,
  rejectRefund,
  reopenEscalation,
  replyEscalation,
  resolveEscalation,
  unassignEscalation,
  updatePriority,
} from '../../api/client';
import { Agent, EscalationFullDetail } from '../../api/types';

interface CaseDetailPageProps {
  currentAgent: Agent | null;
}

export const CaseDetailPage: React.FC<CaseDetailPageProps> = ({ currentAgent }) => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [detail, setDetail] = useState<EscalationFullDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form states
  const [replyMessage, setReplyMessage] = useState('');
  const [noteBody, setNoteBody] = useState('');
  const [resolutionNote, setResolutionNote] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [expandedTraceId, setExpandedTraceId] = useState<string | null>(null);

  const loadCase = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getEscalationDetail(id);
      setDetail(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.userMessage || err.message);
      } else {
        setError('Could not load case details.');
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadCase();
  }, [loadCase]);

  const showNotification = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 4000);
  };

  // Assign to current agent
  const handleAssignToMe = async () => {
    if (!detail) return;
    setActionLoading(true);
    setError(null);
    try {
      await assignEscalation(detail.escalation.id, detail.escalation.version, currentAgent?.id);
      showNotification('Assigned case to yourself.');
      await loadCase();
    } catch (err) {
      if (err instanceof ApiError) setError(err.userMessage);
      else setError('Failed to assign case.');
    } finally {
      setActionLoading(false);
    }
  };

  // Unassign
  const handleUnassign = async () => {
    if (!detail) return;
    setActionLoading(true);
    setError(null);
    try {
      await unassignEscalation(detail.escalation.id, detail.escalation.version);
      showNotification('Case moved back to unassigned queue.');
      await loadCase();
    } catch (err) {
      if (err instanceof ApiError) setError(err.userMessage);
      else setError('Failed to unassign case.');
    } finally {
      setActionLoading(false);
    }
  };

  // Change priority
  const handlePriorityChange = async (newPriority: 'low' | 'normal' | 'high') => {
    if (!detail || detail.escalation.priority === newPriority) return;
    setActionLoading(true);
    setError(null);
    try {
      await updatePriority(detail.escalation.id, newPriority, detail.escalation.version);
      showNotification(`Priority updated to ${newPriority}.`);
      await loadCase();
    } catch (err) {
      if (err instanceof ApiError) setError(err.userMessage);
      else setError('Failed to update priority.');
    } finally {
      setActionLoading(false);
    }
  };

  // Send human reply to customer
  const handleSendReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail || !replyMessage.trim()) return;

    setActionLoading(true);
    setError(null);
    try {
      await replyEscalation(detail.escalation.id, replyMessage.trim());
      setReplyMessage('');
      showNotification('Reply delivered to customer chat.');
      await loadCase();
    } catch (err) {
      if (err instanceof ApiError) setError(err.userMessage);
      else setError('Failed to send reply.');
    } finally {
      setActionLoading(false);
    }
  };

  // Add internal note
  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail || !noteBody.trim()) return;

    setActionLoading(true);
    setError(null);
    try {
      await addEscalationNote(detail.escalation.id, noteBody.trim());
      setNoteBody('');
      showNotification('Internal note added.');
      await loadCase();
    } catch (err) {
      if (err instanceof ApiError) setError(err.userMessage);
      else setError('Failed to add note.');
    } finally {
      setActionLoading(false);
    }
  };

  // Approve refund
  const handleApproveRefund = async () => {
    if (!detail) return;
    if (!window.confirm(`Approve payout of ₹${detail.refund?.amount} to the customer?`)) return;

    setActionLoading(true);
    setError(null);
    try {
      await approveRefund(detail.escalation.id, detail.escalation.version);
      showNotification('Refund approved and payout initiated!');
      await loadCase();
    } catch (err) {
      if (err instanceof ApiError) setError(err.userMessage);
      else setError('Refund approval failed.');
    } finally {
      setActionLoading(false);
    }
  };

  // Reject refund
  const handleRejectRefund = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail || !rejectReason.trim()) return;

    setActionLoading(true);
    setError(null);
    try {
      await rejectRefund(detail.escalation.id, rejectReason.trim(), detail.escalation.version);
      setShowRejectModal(false);
      setRejectReason('');
      showNotification('Refund rejected and customer notified.');
      await loadCase();
    } catch (err) {
      if (err instanceof ApiError) setError(err.userMessage);
      else setError('Failed to reject refund.');
    } finally {
      setActionLoading(false);
    }
  };

  // Resolve case
  const handleResolve = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail || !resolutionNote.trim()) return;

    setActionLoading(true);
    setError(null);
    try {
      await resolveEscalation(detail.escalation.id, resolutionNote.trim(), detail.escalation.version);
      setResolutionNote('');
      showNotification('Case marked as resolved.');
      await loadCase();
    } catch (err) {
      if (err instanceof ApiError) setError(err.userMessage);
      else setError('Failed to resolve case.');
    } finally {
      setActionLoading(false);
    }
  };

  // Reopen case
  const handleReopen = async () => {
    if (!detail) return;
    setActionLoading(true);
    setError(null);
    try {
      await reopenEscalation(detail.escalation.id, detail.escalation.version);
      showNotification('Case reopened.');
      await loadCase();
    } catch (err) {
      if (err instanceof ApiError) setError(err.userMessage);
      else setError('Failed to reopen case.');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="case-detail-container">
        <div className="loading-state">⏳ Loading case details...</div>
      </div>
    );
  }

  if (error && !detail) {
    return (
      <div className="case-detail-container">
        <div className="error-banner">⚠️ {error}</div>
        <button type="button" className="btn btn-outline-sm" onClick={() => navigate('/console')}>
          ← Back to Inbox
        </button>
      </div>
    );
  }

  if (!detail) return null;

  const esc = detail.escalation;
  const isAssignedToMe = esc.assigned_to === currentAgent?.id;

  return (
    <div className="case-detail-container">
      {/* Notifications */}
      {successMsg && <div className="toast-success">✅ {successMsg}</div>}
      {error && <div className="error-banner">⚠️ {error}</div>}

      {/* Top Header Workspace Bar */}
      <div className="case-top-bar">
        <div className="top-bar-left">
          <button type="button" className="btn btn-outline-sm" onClick={() => navigate('/console')}>
            ← Back to Inbox
          </button>
          <div className="case-title-group">
            <h3>Case #{esc.id.slice(0, 8)}</h3>
            <span className={`badge-status badge-status-${esc.status}`}>
              {(esc.status || 'open').replace('_', ' ').toUpperCase()}
            </span>
            {esc.is_overdue && <span className="badge-overdue">⚠️ SLA BREACH</span>}
          </div>
        </div>

        <div className="top-bar-right">
          <div className="priority-control">
            <label htmlFor="case-priority">Priority:</label>
            <select
              id="case-priority"
              value={esc.priority}
              onChange={(e) =>
                void handlePriorityChange(e.target.value as 'low' | 'normal' | 'high')
              }
              disabled={actionLoading}
            >
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
            </select>
          </div>

          <div className="assignment-control">
            {esc.assigned_to ? (
              <div className="assigned-badge">
                <span>👤 {esc.assigned_agent_name || 'Assigned'}</span>
                {isAssignedToMe ? (
                  <button
                    type="button"
                    className="btn btn-outline-xs"
                    onClick={() => void handleUnassign()}
                    disabled={actionLoading}
                  >
                    Unassign
                  </button>
                ) : (
                  currentAgent?.role === 'admin' && (
                    <button
                      type="button"
                      className="btn btn-outline-xs"
                      onClick={() => void handleAssignToMe()}
                      disabled={actionLoading}
                    >
                      Take Over
                    </button>
                  )
                )}
              </div>
            ) : (
              <button
                type="button"
                className="btn btn-primary-sm"
                onClick={() => void handleAssignToMe()}
                disabled={actionLoading}
              >
                Assign to Me
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 3-Column Structured Layout */}
      <div className="case-workspace-grid">
        {/* ======================================================== */}
        {/* COLUMN 1: Customer Profile & Order Context */}
        {/* ======================================================== */}
        <div className="workspace-col col-customer">
          {/* Customer Profile Card */}
          <div className="workspace-card">
            <h4>Customer Profile</h4>
            <div className="profile-details">
              <div className="profile-row">
                <span className="profile-label">Name:</span>
                <strong>{detail.customer.name}</strong>
              </div>
              <div className="profile-row">
                <span className="profile-label">Phone:</span>
                <span className="phone-unmasked">{detail.customer.phone}</span>
              </div>
              <div className="profile-row">
                <span className="profile-label">Language:</span>
                <span className="lang-tag">{(detail.customer?.preferred_language || 'en').toUpperCase()}</span>
              </div>
              <div className="profile-row">
                <span className="profile-label">Channel:</span>
                <span className="badge badge-channel" style={{ background: '#dcfce7', color: '#15803d', padding: '0.15rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600 }}>
                  💬 WhatsApp / Web
                </span>
              </div>
              <div className="profile-row">
                <span className="profile-label">Reply Guard:</span>
                <span style={{ fontSize: '0.75rem', color: '#16a34a', fontWeight: 500 }}>
                  Active (72h window)
                </span>
              </div>
              <div className="profile-row">
                <span className="profile-label">Reason:</span>
                <span className="reason-highlight">{esc.reason}</span>
              </div>
            </div>
          </div>

          {/* Linked Refund Card (if high-value refund is pending) */}
          {detail.refund && (
            <div className="workspace-card refund-card">
              <div className="card-header-row">
                <h4>Linked Refund Action</h4>
                <span className={`refund-status-tag status-${detail.refund.status}`}>
                  {detail.refund.status.replace('_', ' ')}
                </span>
              </div>

              <div className="refund-amount-display">
                <span className="amount-label">Requested Amount:</span>
                <span className="amount-value">₹{detail.refund.amount}</span>
              </div>
              <p className="refund-reason">
                <strong>Reason:</strong> {detail.refund.reason}
              </p>

              {detail.refund.status === 'pending_approval' && (
                <div className="refund-action-buttons">
                  <button
                    type="button"
                    className="btn btn-success"
                    onClick={() => void handleApproveRefund()}
                    disabled={actionLoading}
                  >
                    ✅ Approve & Payout
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger"
                    onClick={() => setShowRejectModal(true)}
                    disabled={actionLoading}
                  >
                    ❌ Reject Refund
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Recent Orders Accordion */}
          <div className="workspace-card">
            <h4>Recent Orders ({detail.recent_orders.length})</h4>
            {detail.recent_orders.length === 0 ? (
              <p className="muted-text">No previous orders found.</p>
            ) : (
              <div className="orders-list">
                {detail.recent_orders.map((ord) => (
                  <div key={ord.id} className="order-item-card">
                    <div className="order-card-header">
                      <strong>{ord.order_number}</strong>
                      <span className={`order-status-badge status-${ord.status}`}>
                        {ord.status}
                      </span>
                    </div>
                    <div className="order-card-meta">
                      <span>Total: ₹{ord.total_amount_inr}</span>
                      <span className="order-date">
                        {new Date(ord.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <ul className="order-items-sublist">
                      {ord.items.map((it, idx) => (
                        <li key={idx}>
                          {it.quantity}x {it.product_title} (@ ₹{it.unit_price_inr})
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ======================================================== */}
        {/* COLUMN 2: Live Conversation & Human Agent Reply */}
        {/* ======================================================== */}
        <div className="workspace-col col-conversation">
          <div className="workspace-card transcript-card">
            <div className="card-header-row">
              <h4>Conversation Transcript</h4>
              <span className="message-count">{detail.messages.length} messages</span>
            </div>

            {/* Transcript Messages Thread */}
            <div className="transcript-thread">
              {detail.messages.map((m) => (
                <div key={m.id} className={`transcript-bubble bubble-${m.role}`}>
                  <div className="bubble-header">
                    <span className="bubble-sender">
                      {m.role === 'user'
                        ? `👤 ${detail.customer.name}`
                        : m.role === 'agent'
                          ? `🎧 Support Agent (${m.agent_name || 'Staff'})`
                          : '🤖 AI Assistant'}
                    </span>
                    {m.input_mode === 'voice' && (
                      <span className="voice-input-tag" title="Sent as Voice Note">
                        🎤 Voice Note
                      </span>
                    )}
                    <span className="bubble-time">
                      {new Date(m.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                      {m.role !== 'user' && (
                        <span title="Delivered via WhatsApp" style={{ marginLeft: '4px', color: '#38bdf8' }}>✓✓</span>
                      )}
                    </span>
                  </div>

                  {/* Render plain text safely */}
                  <div className="bubble-content">{m.content}</div>
                </div>
              ))}
            </div>

            {/* Collapsible Bot Execution Traces */}
            {detail.traces.length > 0 && (
              <div className="traces-section">
                <h5>Bot Traces & Intent Logs</h5>
                <div className="traces-accordion">
                  {detail.traces.map((trace) => {
                    const isExpanded = expandedTraceId === trace.id;
                    return (
                      <div key={trace.id} className="trace-row">
                        <button
                          type="button"
                          className="trace-toggle-btn"
                          onClick={() => setExpandedTraceId(isExpanded ? null : trace.id)}
                        >
                          <span>
                            {isExpanded ? '▼' : '▶'} Intent: <strong>{trace.intent}</strong> ({trace.language})
                          </span>
                          <span className="trace-cost">
                            {trace.prompt_tokens + trace.completion_tokens} tokens • ₹{trace.cost_inr} • {trace.latency_ms}ms
                          </span>
                        </button>
                        {isExpanded && (
                          <div className="trace-details-body">
                            <pre>{JSON.stringify(trace.router_raw, null, 2)}</pre>
                            {trace.tool_calls.length > 0 && (
                              <div className="trace-tools">
                                <strong>Tool Calls:</strong>
                                <pre>{JSON.stringify(trace.tool_calls, null, 2)}</pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Agent Live Customer Reply Box */}
            <div className="agent-reply-box">
              <form onSubmit={handleSendReply}>
                <label htmlFor="agent-reply-input">
                  <strong>Reply to Customer (Appears in their Chat):</strong>
                </label>
                <textarea
                  id="agent-reply-input"
                  rows={3}
                  value={replyMessage}
                  onChange={(e) => setReplyMessage(e.target.value)}
                  placeholder="Type a direct message to the customer..."
                  disabled={actionLoading || esc.status === 'resolved'}
                />
                <div className="reply-actions-row">
                  <span className="reply-hint">
                    {esc.status === 'resolved'
                      ? 'Reopen case to send further replies.'
                      : 'Sending a reply updates case to in_progress and records first response SLA.'}
                  </span>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={actionLoading || !replyMessage.trim() || esc.status === 'resolved'}
                  >
                    💬 Send to Customer
                  </button>
                </div>
              </form>
            </div>

            {/* Case Resolution Action */}
            <div className="case-resolution-box">
              {esc.status === 'resolved' ? (
                <div className="resolution-resolved-display">
                  <div className="resolved-banner">
                    ✅ <strong>Case Resolved</strong> on{' '}
                    {esc.resolved_at ? new Date(esc.resolved_at).toLocaleString() : 'N/A'}
                  </div>
                  {esc.resolution_note && (
                    <p className="resolution-note-text">
                      <strong>Resolution Note:</strong> {esc.resolution_note}
                    </p>
                  )}
                  <button
                    type="button"
                    className="btn btn-outline-sm"
                    onClick={() => void handleReopen()}
                    disabled={actionLoading}
                  >
                    🔄 Reopen Case
                  </button>
                </div>
              ) : (
                <form onSubmit={handleResolve} className="resolve-form">
                  <label htmlFor="resolution-note-input">
                    <strong>Resolution Note (Mandatory to Close Case):</strong>
                  </label>
                  <input
                    id="resolution-note-input"
                    type="text"
                    value={resolutionNote}
                    onChange={(e) => setResolutionNote(e.target.value)}
                    placeholder="e.g. Refund approved & replacement tracking sent to customer."
                    required
                    disabled={actionLoading}
                  />
                  <button
                    type="submit"
                    className="btn btn-success resolve-btn"
                    disabled={actionLoading || !resolutionNote.trim()}
                  >
                    🏁 Resolve & Close Case
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>

        {/* ======================================================== */}
        {/* COLUMN 3: Internal Notes & Audit Timeline */}
        {/* ======================================================== */}
        <div className="workspace-col col-audit">
          {/* Internal Notes Thread */}
          <div className="workspace-card notes-card">
            <h4>Internal Team Notes</h4>
            <p className="internal-hint">Private notes visible only to agents and admins.</p>

            <form onSubmit={handleAddNote} className="note-input-form">
              <textarea
                rows={2}
                value={noteBody}
                onChange={(e) => setNoteBody(e.target.value)}
                placeholder="Add an internal note or observation..."
                disabled={actionLoading}
              />
              <button
                type="submit"
                className="btn btn-secondary-sm"
                disabled={actionLoading || !noteBody.trim()}
              >
                + Add Note
              </button>
            </form>

            <div className="notes-thread">
              {detail.notes.length === 0 ? (
                <p className="muted-text">No internal notes yet.</p>
              ) : (
                detail.notes.map((note) => (
                  <div key={note.id} className="note-item">
                    <div className="note-meta">
                      <strong>{note.agent_name}</strong>
                      <span>
                        {new Date(note.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </span>
                    </div>
                    <div className="note-body">{note.body}</div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Audit Timeline */}
          <div className="workspace-card audit-card">
            <h4>Audit Timeline ({detail.events.length})</h4>
            <div className="timeline-list">
              {detail.events.map((ev) => (
                <div key={ev.id} className="timeline-item">
                  <div className="timeline-marker" />
                  <div className="timeline-content">
                    <div className="timeline-header">
                      <span className="timeline-action">{(ev.action || 'event').toUpperCase()}</span>
                      <span className="timeline-time">
                        {new Date(ev.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <div className="timeline-actor">
                      Actor: <strong>{ev.actor_name || ev.actor_type}</strong>
                    </div>
                    {Object.keys(ev.detail || {}).length > 0 && (
                      <div className="timeline-detail">
                        <pre>{JSON.stringify(ev.detail, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Reject Refund Modal */}
      {showRejectModal && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <h3>Reject Refund Request</h3>
            <p>Please enter the specific reason why this refund is rejected. This will be shared with the customer.</p>
            <form onSubmit={handleRejectRefund}>
              <textarea
                rows={3}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g. Return window expired over 14 days ago according to policy."
                required
              />
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-outline-sm"
                  onClick={() => setShowRejectModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-danger"
                  disabled={actionLoading || !rejectReason.trim()}
                >
                  Confirm Rejection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
