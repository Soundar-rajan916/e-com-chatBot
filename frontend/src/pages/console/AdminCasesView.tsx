import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getEscalations,
  getEscalationStats,
  getRecentConversations,
} from '../../api/client';
import {
  Agent,
  ConversationItem,
  EscalationStats,
  EscalationSummary,
} from '../../api/types';
import {
  AlertTriangleIcon,
  ChatIcon,
  AlertCircleIcon,
  RefreshIcon,
  CheckIcon,
  SearchIcon,
  CheckCircleIcon,
} from '../../components/icons';

interface AdminCasesViewProps {
  currentAgent: Agent | null;
}

export const AdminCasesView: React.FC<AdminCasesViewProps> = ({ currentAgent: _currentAgent }) => {
  const navigate = useNavigate();

  // Mode: 'escalations' | 'conversations'
  const [viewMode, setViewMode] = useState<'escalations' | 'conversations'>('escalations');

  // Escalations state
  const [stats, setStats] = useState<EscalationStats | null>(null);
  const [escalations, setEscalations] = useState<EscalationSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters for escalations
  const [statusFilter, setStatusFilter] = useState<string>('open');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Conversations state (all chat sessions)
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [convLoading, setConvLoading] = useState<boolean>(false);
  const [channelFilter, setChannelFilter] = useState<string>('all');

  const fetchEscalationsData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, listData] = await Promise.all([
        getEscalationStats(),
        getEscalations({
          status: statusFilter || undefined,
          priority: priorityFilter || undefined,
          q: searchQuery.trim() || undefined,
        }),
      ]);
      setStats(statsData);
      setEscalations(listData.items || []);
    } catch {
      setError('Could not load escalation cases.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, priorityFilter, searchQuery]);

  const fetchConversationsData = useCallback(async () => {
    setConvLoading(true);
    setError(null);
    try {
      const data = await getRecentConversations(50);
      setConversations(data || []);
    } catch {
      setError('Could not load chat conversations.');
    } finally {
      setConvLoading(false);
    }
  }, []);

  useEffect(() => {
    if (viewMode === 'escalations') {
      void fetchEscalationsData();
    } else {
      void fetchConversationsData();
    }
  }, [viewMode, fetchEscalationsData, fetchConversationsData]);

  const getReasonLabel = (reasonType: string): string => {
    switch (reasonType) {
      case 'refund_pending_approval':
        return 'Refund Approval';
      case 'user_requested':
        return 'Human Handoff';
      case 'router_fallback':
        return 'Router Fallback';
      case 'llm_failure':
        return 'LLM Fallback';
      default:
        return reasonType;
    }
  };

  const filteredConversations = conversations.filter((c) => {
    if (channelFilter === 'all') return true;
    return c.channel.toLowerCase() === channelFilter.toLowerCase();
  });

  return (
    <div className="admin-cases-view">
      {/* Sub-Header & Mode Switch */}
      <div className="cases-header-bar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#1e293b' }}>Customer Support Cases & Execution Traces</h3>
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: '#64748b' }}>
            Review customer escalations or inspect the AI assistant's execution traces and decisions.
          </p>
        </div>

        <div className="btn-group" style={{ display: 'inline-flex', background: '#f1f5f9', padding: '4px', borderRadius: '8px' }}>
          <button
            type="button"
            className={`btn-toggle ${viewMode === 'escalations' ? 'active' : ''}`}
            onClick={() => setViewMode('escalations')}
            style={{
              padding: '6px 14px',
              fontSize: '0.85rem',
              fontWeight: 600,
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              background: viewMode === 'escalations' ? '#ffffff' : 'transparent',
              color: viewMode === 'escalations' ? '#1e293b' : '#64748b',
              boxShadow: viewMode === 'escalations' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <AlertTriangleIcon size={14} /> Escalations Queue ({stats?.open_count ?? 0})
          </button>
          <button
            type="button"
            className={`btn-toggle ${viewMode === 'conversations' ? 'active' : ''}`}
            onClick={() => setViewMode('conversations')}
            style={{
              padding: '6px 14px',
              fontSize: '0.85rem',
              fontWeight: 600,
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              background: viewMode === 'conversations' ? '#ffffff' : 'transparent',
              color: viewMode === 'conversations' ? '#1e293b' : '#64748b',
              boxShadow: viewMode === 'conversations' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <ChatIcon size={14} /> All Chats & Bot Traces ({conversations.length > 0 ? conversations.length : 'Browse'})
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <AlertCircleIcon size={16} /> {error}
        </div>
      )}

      {/* VIEW 1: ESCALATIONS QUEUE */}
      {viewMode === 'escalations' && (
        <>
          {/* Stats Summary Bar */}
          {stats && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
              <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Open Cases</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#ef4444', marginTop: '0.25rem' }}>{stats.open_count}</div>
              </div>
              <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>In Progress</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f59e0b', marginTop: '0.25rem' }}>{stats.in_progress_count}</div>
              </div>
              <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Resolved</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#10b981', marginTop: '0.25rem' }}>{stats.resolved_count}</div>
              </div>
              <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Overdue SLA</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#dc2626', marginTop: '0.25rem' }}>{stats.overdue_count}</div>
              </div>
            </div>
          )}

          {/* Filter Bar */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center', marginBottom: '1rem', background: '#f8fafc', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569' }}>Status:</span>
              {(['open', 'in_progress', 'resolved', ''] as const).map((st) => (
                <button
                  key={st || 'all'}
                  type="button"
                  onClick={() => setStatusFilter(st)}
                  style={{
                    padding: '4px 10px',
                    fontSize: '0.8rem',
                    borderRadius: '6px',
                    border: '1px solid',
                    cursor: 'pointer',
                    background: statusFilter === st ? '#3b82f6' : '#ffffff',
                    borderColor: statusFilter === st ? '#3b82f6' : '#cbd5e1',
                    color: statusFilter === st ? '#ffffff' : '#475569',
                    fontWeight: statusFilter === st ? 600 : 500,
                  }}
                >
                  {st === '' ? 'All' : st.replace('_', ' ')}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569' }}>Priority:</span>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                style={{
                  padding: '4px 8px',
                  fontSize: '0.8rem',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  background: '#ffffff',
                  color: '#475569',
                }}
              >
                <option value="">All Priorities</option>
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="low">Low</option>
              </select>
            </div>

            <input
              type="text"
              placeholder="Search customer, phone, or reason..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                marginLeft: 'auto',
                padding: '6px 12px',
                fontSize: '0.85rem',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                width: '260px',
              }}
            />

            <button
              type="button"
              onClick={() => void fetchEscalationsData()}
              disabled={loading}
              style={{
                padding: '6px 12px',
                fontSize: '0.85rem',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                background: '#ffffff',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <RefreshIcon size={13} /> {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          {/* Table */}
          {loading && escalations.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>Loading escalation cases...</div>
          ) : escalations.length === 0 ? (
            <div style={{ padding: '3rem 1rem', textAlign: 'center', background: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '0.5rem' }}>
                <CheckCircleIcon size={36} color="#10b981" />
              </div>
              <h4 style={{ margin: '0.5rem 0 0.25rem', color: '#1e293b' }}>No Escalations Found</h4>
              <p style={{ margin: 0, color: '#64748b', fontSize: '0.875rem' }}>
                All customer queries are currently resolved or handled by the assistant.
              </p>
            </div>
          ) : (
            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
                <thead style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                  <tr>
                    <th style={{ padding: '0.75rem 1rem' }}>Priority</th>
                    <th style={{ padding: '0.75rem 1rem' }}>Status</th>
                    <th style={{ padding: '0.75rem 1rem' }}>Reason / Query</th>
                    <th style={{ padding: '0.75rem 1rem' }}>Customer</th>
                    <th style={{ padding: '0.75rem 1rem' }}>Order</th>
                    <th style={{ padding: '0.75rem 1rem' }}>Created</th>
                    <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {escalations.map((esc) => (
                    <tr
                      key={esc.id}
                      onClick={() => navigate(`/console/cases/${esc.id}`)}
                      style={{ borderBottom: '1px solid #f1f5f9', cursor: 'pointer', transition: 'background 0.15s' }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f8fafc')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#ffffff')}
                    >
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <span style={{
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          background: esc.priority === 'high' ? '#fee2e2' : esc.priority === 'normal' ? '#ffedd5' : '#e0f2fe',
                          color: esc.priority === 'high' ? '#991b1b' : esc.priority === 'normal' ? '#9a3412' : '#0369a1',
                        }}>
                          {esc.priority}
                        </span>
                      </td>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <span style={{
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          textTransform: 'capitalize',
                          background: esc.status === 'open' ? '#fef3c7' : esc.status === 'in_progress' ? '#e0e7ff' : '#dcfce7',
                          color: esc.status === 'open' ? '#92400e' : esc.status === 'in_progress' ? '#3730a3' : '#166534',
                        }}>
                          {esc.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td style={{ padding: '0.75rem 1rem', maxWidth: '320px' }}>
                        <div style={{ display: 'inline-block', fontSize: '0.75rem', background: '#f1f5f9', color: '#475569', padding: '2px 6px', borderRadius: '4px', marginBottom: '2px' }}>
                          {getReasonLabel(esc.reason_type)}
                        </div>
                        <div style={{ color: '#1e293b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {esc.reason}
                        </div>
                      </td>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <div style={{ fontWeight: 600, color: '#1e293b' }}>{esc.customer_name}</div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{esc.customer_phone_masked}</div>
                      </td>
                      <td style={{ padding: '0.75rem 1rem', color: '#64748b' }}>
                        {esc.order_number || '—'}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', color: '#64748b', fontSize: '0.8rem' }}>
                        {new Date(esc.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/console/cases/${esc.id}`);
                          }}
                          style={{
                            background: '#2563eb',
                            color: '#ffffff',
                            border: 'none',
                            borderRadius: '6px',
                            padding: '6px 12px',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          View Case & Traces →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* VIEW 2: ALL CUSTOMER CHATS & TRACES */}
      {viewMode === 'conversations' && (
        <>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '1rem', background: '#f8fafc', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569' }}>Channel:</span>
            {(['all', 'whatsapp', 'web'] as const).map((ch) => (
              <button
                key={ch}
                type="button"
                onClick={() => setChannelFilter(ch)}
                style={{
                  padding: '4px 10px',
                  fontSize: '0.8rem',
                  borderRadius: '6px',
                  border: '1px solid',
                  cursor: 'pointer',
                  background: channelFilter === ch ? '#2563eb' : '#ffffff',
                  borderColor: channelFilter === ch ? '#2563eb' : '#cbd5e1',
                  color: channelFilter === ch ? '#ffffff' : '#475569',
                  fontWeight: channelFilter === ch ? 600 : 500,
                  textTransform: 'capitalize',
                }}
              >
                {ch === 'all' ? 'All Channels' : ch === 'whatsapp' ? 'WhatsApp' : 'Web Chat'}
              </button>
            ))}

            <button
              type="button"
              onClick={() => void fetchConversationsData()}
              disabled={convLoading}
              style={{
                marginLeft: 'auto',
                padding: '6px 12px',
                fontSize: '0.85rem',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                background: '#ffffff',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <RefreshIcon size={13} /> {convLoading ? 'Refreshing...' : 'Refresh Chats'}
            </button>
          </div>

          {convLoading && conversations.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>Loading customer chat sessions...</div>
          ) : filteredConversations.length === 0 ? (
            <div style={{ padding: '3rem 1rem', textAlign: 'center', background: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '0.5rem' }}>
                <ChatIcon size={36} color="#64748b" />
              </div>
              <h4 style={{ margin: '0.5rem 0 0.25rem', color: '#1e293b' }}>No Conversations Found</h4>
              <p style={{ margin: 0, color: '#64748b', fontSize: '0.875rem' }}>No chat sessions match the selected filter.</p>
            </div>
          ) : (
            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
                <thead style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                  <tr>
                    <th style={{ padding: '0.75rem 1rem' }}>Channel</th>
                    <th style={{ padding: '0.75rem 1rem' }}>Customer</th>
                    <th style={{ padding: '0.75rem 1rem' }}>Messages</th>
                    <th style={{ padding: '0.75rem 1rem' }}>Last Message</th>
                    <th style={{ padding: '0.75rem 1rem' }}>Traces Status</th>
                    <th style={{ padding: '0.75rem 1rem' }}>Created</th>
                    <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Inspect</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredConversations.map((conv) => (
                    <tr
                      key={conv.session_id}
                      onClick={() => navigate(`/console/cases/${conv.escalation_id || conv.session_id}`)}
                      style={{ borderBottom: '1px solid #f1f5f9', cursor: 'pointer', transition: 'background 0.15s' }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f8fafc')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#ffffff')}
                    >
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <span style={{
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          background: conv.channel === 'whatsapp' ? '#dcfce7' : '#e0f2fe',
                          color: conv.channel === 'whatsapp' ? '#166534' : '#0369a1',
                        }}>
                          {conv.channel === 'whatsapp' ? 'WhatsApp' : 'Web'}
                        </span>
                      </td>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <div style={{ fontWeight: 600, color: '#1e293b' }}>{conv.customer_name}</div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{conv.customer_phone}</div>
                      </td>
                      <td style={{ padding: '0.75rem 1rem', color: '#64748b' }}>
                        {conv.message_count} turn{conv.message_count === 1 ? '' : 's'}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', maxWidth: '300px', color: '#334155' }}>
                        <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {conv.last_message}
                        </div>
                      </td>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        {conv.has_traces ? (
                          <span style={{ padding: '3px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, background: '#f0fdf4', color: '#15803d', border: '1px solid #bbf7d0', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            <CheckIcon size={12} /> Traces Logged
                          </span>
                        ) : (
                          <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>No traces</span>
                        )}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', color: '#64748b', fontSize: '0.8rem' }}>
                        {new Date(conv.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/console/cases/${conv.escalation_id || conv.session_id}`);
                          }}
                          style={{
                            background: '#0284c7',
                            color: '#ffffff',
                            border: 'none',
                            borderRadius: '6px',
                            padding: '6px 12px',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <SearchIcon size={13} /> Inspect Traces
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
};
