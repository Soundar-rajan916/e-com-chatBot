import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getEscalations, getEscalationStats } from '../../api/client';
import { Agent, EscalationStats, EscalationSummary } from '../../api/types';

interface InboxPageProps {
  currentAgent: Agent | null;
  onLogout: () => void;
}

export const InboxPage: React.FC<InboxPageProps> = ({ currentAgent, onLogout }) => {
  const navigate = useNavigate();

  const [stats, setStats] = useState<EscalationStats | null>(null);
  const [escalations, setEscalations] = useState<EscalationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('open');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [reasonTypeFilter, setReasonTypeFilter] = useState<string>('');
  const [assignedFilter, setAssignedFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [overdueOnly, setOverdueOnly] = useState<boolean>(false);

  const fetchQueueData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, listData] = await Promise.all([
        getEscalationStats(),
        getEscalations({
          status: statusFilter || undefined,
          priority: priorityFilter || undefined,
          reason_type: reasonTypeFilter || undefined,
          assigned: assignedFilter || undefined,
          q: searchQuery.trim() || undefined,
          overdue: overdueOnly,
        }),
      ]);
      setStats(statsData);
      setEscalations(listData.items);
    } catch {
      setError('Could not load escalations. Please check your session or refresh.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, priorityFilter, reasonTypeFilter, assignedFilter, searchQuery, overdueOnly]);

  useEffect(() => {
    void fetchQueueData();
  }, [fetchQueueData]);

  // Format seconds into readable time
  const formatSeconds = (sec: number | null | undefined): string => {
    if (sec === null || sec === undefined) return 'N/A';
    if (sec < 60) return `${Math.round(sec)}s`;
    const mins = Math.floor(sec / 60);
    const remainingSec = Math.round(sec % 60);
    if (mins < 60) return `${mins}m ${remainingSec}s`;
    const hrs = Math.floor(mins / 60);
    const remMins = mins % 60;
    return `${hrs}h ${remMins}m`;
  };

  const getReasonLabel = (reasonType: string): string => {
    switch (reasonType) {
      case 'refund_pending_approval':
        return '💰 Refund Approval';
      case 'user_requested':
        return '👤 Human Handoff';
      case 'router_fallback':
        return '🔀 Router Fallback';
      case 'llm_failure':
        return '⚡ LLM Fallback';
      default:
        return reasonType;
    }
  };

  return (
    <div className="inbox-container">
      {/* Top Header */}
      <div className="inbox-header">
        <div>
          <h2>Support Operations Inbox</h2>
          <p className="inbox-subtitle">
            Unified queue for customer escalations, LLM fallbacks, and high-value refund approvals.
          </p>
        </div>
        <div className="inbox-agent-badge">
          <span className="agent-avatar">🎧</span>
          <div className="agent-meta">
            <strong>{currentAgent?.name || 'Agent'}</strong>
            <span className="agent-role">({currentAgent?.role || 'agent'})</span>
          </div>
          <button type="button" className="btn btn-outline-sm logout-btn" onClick={onLogout}>
            Sign Out
          </button>
        </div>
      </div>

      {/* KPI Stats Bar */}
      {stats && (
        <div className="stats-grid">
          <div
            className={`stat-card ${statusFilter === 'open' ? 'active-stat' : ''}`}
            onClick={() => setStatusFilter('open')}
          >
            <span className="stat-label">Open Cases</span>
            <span className="stat-value stat-open">{stats.open_count}</span>
          </div>
          <div
            className={`stat-card ${statusFilter === 'in_progress' ? 'active-stat' : ''}`}
            onClick={() => setStatusFilter('in_progress')}
          >
            <span className="stat-label">In Progress</span>
            <span className="stat-value stat-inprogress">{stats.in_progress_count}</span>
          </div>
          <div
            className={`stat-card ${statusFilter === 'resolved' ? 'active-stat' : ''}`}
            onClick={() => setStatusFilter('resolved')}
          >
            <span className="stat-label">Resolved</span>
            <span className="stat-value stat-resolved">{stats.resolved_count}</span>
          </div>
          <div
            className={`stat-card ${overdueOnly ? 'active-stat' : ''} ${stats.overdue_count > 0 ? 'stat-alert' : ''}`}
            onClick={() => setOverdueOnly(!overdueOnly)}
          >
            <span className="stat-label">Overdue SLA</span>
            <span className="stat-value stat-overdue">{stats.overdue_count}</span>
          </div>
          <div
            className={`stat-card ${assignedFilter === 'unassigned' ? 'active-stat' : ''}`}
            onClick={() => setAssignedFilter(assignedFilter === 'unassigned' ? '' : 'unassigned')}
          >
            <span className="stat-label">Unassigned</span>
            <span className="stat-value">{stats.unassigned_count}</span>
          </div>
          <div
            className={`stat-card ${assignedFilter === 'me' ? 'active-stat' : ''}`}
            onClick={() => setAssignedFilter(assignedFilter === 'me' ? '' : 'me')}
          >
            <span className="stat-label">Assigned to Me</span>
            <span className="stat-value stat-mine">{stats.my_open_count}</span>
          </div>
          <div className="stat-card stat-metric">
            <span className="stat-label">Avg First Response (7d)</span>
            <span className="stat-value-sm">{formatSeconds(stats.avg_response_time_seconds)}</span>
          </div>
          <div className="stat-card stat-metric">
            <span className="stat-label">Avg Resolution (7d)</span>
            <span className="stat-value-sm">{formatSeconds(stats.avg_resolution_time_seconds)}</span>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="queue-controls">
        <div className="status-tabs">
          <button
            type="button"
            className={`tab-btn ${statusFilter === '' ? 'active' : ''}`}
            onClick={() => setStatusFilter('')}
          >
            All Statuses
          </button>
          <button
            type="button"
            className={`tab-btn ${statusFilter === 'open' ? 'active' : ''}`}
            onClick={() => setStatusFilter('open')}
          >
            Open
          </button>
          <button
            type="button"
            className={`tab-btn ${statusFilter === 'in_progress' ? 'active' : ''}`}
            onClick={() => setStatusFilter('in_progress')}
          >
            In Progress
          </button>
          <button
            type="button"
            className={`tab-btn ${statusFilter === 'resolved' ? 'active' : ''}`}
            onClick={() => setStatusFilter('resolved')}
          >
            Resolved
          </button>
        </div>

        <div className="filters-row">
          <div className="search-box">
            <input
              type="text"
              placeholder="Search customer, phone, reason..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <select
            className="filter-select"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
          >
            <option value="">All Priorities</option>
            <option value="high">High Priority</option>
            <option value="normal">Normal Priority</option>
            <option value="low">Low Priority</option>
          </select>

          <select
            className="filter-select"
            value={reasonTypeFilter}
            onChange={(e) => setReasonTypeFilter(e.target.value)}
          >
            <option value="">All Reason Types</option>
            <option value="refund_pending_approval">Refund Pending Approval</option>
            <option value="user_requested">User Requested Handoff</option>
            <option value="router_fallback">Router Fallback</option>
            <option value="llm_failure">LLM Failure</option>
          </select>

          <select
            className="filter-select"
            value={assignedFilter}
            onChange={(e) => setAssignedFilter(e.target.value)}
          >
            <option value="">All Assignments</option>
            <option value="me">Assigned to Me</option>
            <option value="unassigned">Unassigned Only</option>
          </select>

          <label className="checkbox-filter">
            <input
              type="checkbox"
              checked={overdueOnly}
              onChange={(e) => setOverdueOnly(e.target.checked)}
            />
            <span>Overdue SLA Only</span>
          </label>

          <button
            type="button"
            className="btn btn-outline-sm refresh-btn"
            onClick={() => void fetchQueueData()}
            disabled={loading}
          >
            {loading ? 'Refreshing...' : '🔄 Refresh'}
          </button>
        </div>
      </div>

      {/* Main Escalation Queue List */}
      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
        </div>
      )}

      {loading && escalations.length === 0 ? (
        <div className="loading-state">
          <span className="spinner">⏳</span> Loading escalation cases...
        </div>
      ) : escalations.length === 0 ? (
        <div className="empty-queue-state">
          <span className="empty-icon">🎉</span>
          <h3>Inbox Zero!</h3>
          <p>No escalations match your current filter criteria.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="queue-table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Status</th>
                <th>Reason</th>
                <th>Customer</th>
                <th>Order</th>
                <th>Assignee</th>
                <th>SLA</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {escalations.map((esc) => (
                <tr
                  key={esc.id}
                  className={`queue-row ${esc.is_overdue ? 'row-overdue' : ''}`}
                  onClick={() => navigate(`/console/cases/${esc.id}`)}
                >
                  <td>
                    <span className={`badge-priority badge-priority-${esc.priority}`}>
                      {esc.priority.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <span className={`badge-status badge-status-${esc.status}`}>
                      {esc.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td>
                    <div className="reason-cell">
                      <span className="reason-tag">{getReasonLabel(esc.reason_type)}</span>
                      <span className="reason-text" title={esc.reason}>
                        {esc.reason}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="customer-cell">
                      <strong>{esc.customer_name}</strong>
                      <span className="customer-phone">{esc.customer_phone_masked}</span>
                    </div>
                  </td>
                  <td>
                    <span className="order-number">{esc.order_number || '—'}</span>
                  </td>
                  <td>
                    <span className="assignee-text">
                      {esc.assigned_agent_name ? `👤 ${esc.assigned_agent_name}` : '⚪ Unassigned'}
                    </span>
                  </td>
                  <td>
                    {esc.is_overdue ? (
                      <span className="badge-overdue" title="Case has breached SLA window">
                        ⚠️ Overdue
                      </span>
                    ) : (
                      <span className="sla-ok">Within SLA</span>
                    )}
                  </td>
                  <td>
                    <span className="time-text">
                      {new Date(esc.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-primary-sm open-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/console/cases/${esc.id}`);
                      }}
                    >
                      Open Case
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
