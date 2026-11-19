import React, { useCallback, useEffect, useState } from 'react';
import {
  adminApproveRefundDirect,
  adminRejectRefundDirect,
  getAdminRefunds,
} from '../../api/client';
import { AdminRefundSummary } from '../../api/types';
import { RefreshIcon, CreditCardIcon, CheckIcon, CloseIcon } from '../../components/icons';

export const AdminRefundsView: React.FC = () => {
  const [refunds, setRefunds] = useState<AdminRefundSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Status Filter: default to pending_approval
  const [statusFilter, setStatusFilter] = useState<string>('pending_approval');

  // Busy states & Reject modal
  const [busyRefundId, setBusyRefundId] = useState<string | null>(null);
  const [rejectModalRefund, setRejectModalRefund] = useState<AdminRefundSummary | null>(null);
  const [rejectReason, setRejectReason] = useState<string>('Item policy or return conditions not met.');

  const fetchRefunds = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminRefunds({
        status: statusFilter || undefined,
      });
      setRefunds(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load refunds.';
      setError(msg);
      setRefunds([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void fetchRefunds();
  }, [fetchRefunds]);

  const handleApprove = async (refund: AdminRefundSummary) => {
    setBusyRefundId(refund.id);
    setError(null);
    setActionSuccess(null);
    try {
      const updated = await adminApproveRefundDirect(refund.id);
      setRefunds((prev) =>
        prev.map((r) => (r.id === updated.id ? updated : r))
      );
      setActionSuccess(`Refund of ₹${Number(refund.amount).toLocaleString('en-IN')} approved and paid successfully!`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to approve refund payout.';
      setError(msg);
    } finally {
      setBusyRefundId(null);
    }
  };

  const handleConfirmReject = async () => {
    if (!rejectModalRefund) return;
    setBusyRefundId(rejectModalRefund.id);
    setError(null);
    setActionSuccess(null);
    try {
      const updated = await adminRejectRefundDirect(
        rejectModalRefund.id,
        rejectReason.trim() || 'Rejected by administrator'
      );
      setRefunds((prev) =>
        prev.map((r) => (r.id === updated.id ? updated : r))
      );
      setActionSuccess(`Refund for order ${rejectModalRefund.order_number} was rejected.`);
      setRejectModalRefund(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to reject refund.';
      setError(msg);
    } finally {
      setBusyRefundId(null);
    }
  };

  const formatPrice = (val: number | string | undefined | null) => {
    const num = Number(val ?? 0);
    return isNaN(num) ? '₹0.00' : `₹${num.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  };

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString('en-IN', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="admin-refunds-view">
      <div className="admin-section-header">
        <div>
          <h3>Refunds & Returns Hub</h3>
          <p className="admin-section-sub">
            Review refund requests with clear return amounts and customer return reasons.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-outline-sm"
          onClick={() => void fetchRefunds()}
          disabled={loading}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshIcon size={13} /> {loading ? 'Refreshing...' : 'Refresh Refunds'}
        </button>
      </div>

      {actionSuccess && (
        <div className="admin-alert admin-alert-success" role="alert">
          {actionSuccess}
        </div>
      )}

      {error && (
        <div className="admin-alert admin-alert-danger" role="alert">
          {error}
        </div>
      )}

      {/* Filter Tabs */}
      <div className="admin-controls-bar">
        <div className="admin-status-tabs">
          {[
            { label: 'Pending Approval', value: 'pending_approval' },
            { label: 'All Refunds', value: '' },
            { label: 'Approved & Paid', value: 'processed' },
            { label: 'Rejected', value: 'rejected' },
          ].map((tab) => (
            <button
              key={tab.value}
              type="button"
              className={`tab-btn ${statusFilter === tab.value ? 'active' : ''}`}
              onClick={() => setStatusFilter(tab.value)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Refunds Cards */}
      {loading ? (
        <div className="admin-loading-state">
          <div className="spinner" />
          <p>Loading refunds...</p>
        </div>
      ) : refunds.length === 0 ? (
        <div className="admin-empty-state">
          <div className="empty-icon" style={{ display: 'flex', justifyContent: 'center', marginBottom: '12px', color: '#848D9A' }}>
            <CreditCardIcon size={44} />
          </div>
          <h4>No refunds found</h4>
          <p>
            {statusFilter === 'pending_approval'
              ? 'Great! There are no refund requests waiting for approval.'
              : 'No refund records match the selected status filter.'}
          </p>
        </div>
      ) : (
        <div className="admin-refunds-grid">
          {refunds.map((refund) => {
            const isBusy = busyRefundId === refund.id;
            const isPending = refund.status === 'pending_approval';
            const isProcessed = refund.status === 'processed' || refund.status === 'approved';
            const isRejected = refund.status === 'rejected';

            return (
              <div
                key={refund.id}
                className={`admin-refund-card ${isPending ? 'card-pending' : ''}`}
              >
                {/* Primary Spotlight 1: Return Amount */}
                <div className="refund-card-amount-block">
                  <span className="refund-field-caption">RETURN AMOUNT</span>
                  <div className="refund-card-amount">
                    {formatPrice(refund.amount_inr ?? refund.amount)}
                  </div>
                </div>

                {/* Primary Spotlight 2: Reason of Return */}
                <div className="refund-card-reason-block">
                  <span className="refund-field-caption">REASON OF RETURN</span>
                  <blockquote className="refund-card-reason-text">
                    "{refund.reason || 'No reason provided by customer.'}"
                  </blockquote>
                </div>

                {/* Metadata details */}
                <div className="refund-card-meta">
                  <div>
                    <span className="meta-sub">Order:</span>{' '}
                    <strong>{refund.order_number}</strong>
                  </div>
                  <div>
                    <span className="meta-sub">Customer:</span>{' '}
                    <span>{refund.customer_name}</span>
                  </div>
                  <div>
                    <span className="meta-sub">Requested:</span>{' '}
                    <span>{formatDate(refund.created_at)}</span>
                  </div>
                  <div>
                    <span className="meta-sub">Status:</span>{' '}
                    {isPending && (
                      <span className="admin-badge badge-pending">Needs Approval</span>
                    )}
                    {isProcessed && (
                      <span className="admin-badge badge-delivered" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <CheckIcon size={12} /> Paid / Approved
                      </span>
                    )}
                    {isRejected && (
                      <span className="admin-badge badge-cancelled" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <CloseIcon size={12} /> Rejected
                      </span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="refund-card-actions">
                  {isPending && (
                    <>
                      <button
                        type="button"
                        className="btn btn-primary-sm admin-approve-btn"
                        onClick={() => void handleApprove(refund)}
                        disabled={isBusy}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                      >
                        <CheckIcon size={13} /> {isBusy ? 'Processing...' : 'Approve Refund'}
                      </button>
                      <button
                        type="button"
                        className="btn btn-outline-danger-sm"
                        onClick={() => {
                          setRejectModalRefund(refund);
                          setRejectReason('Item return conditions not met.');
                        }}
                        disabled={isBusy}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                      >
                        <CloseIcon size={13} /> Reject
                      </button>
                    </>
                  )}
                  {isProcessed && (
                    <div className="refund-status-label status-processed" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <CheckIcon size={13} /> Approved &amp; Payout Complete
                      {refund.decided_by && <small> ({refund.decided_by})</small>}
                    </div>
                  )}
                  {isRejected && (
                    <div className="refund-status-label status-rejected" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <CloseIcon size={13} /> Rejected
                      {refund.decided_by && <small> ({refund.decided_by})</small>}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Reject Modal */}
      {rejectModalRefund && (
        <div className="admin-modal-overlay">
          <div className="admin-modal-content">
            <h4>Reject Refund for {rejectModalRefund.order_number}</h4>
            <p>
              Please enter the reason for rejecting this refund request of{' '}
              <strong>{formatPrice(rejectModalRefund.amount_inr ?? rejectModalRefund.amount)}</strong>:
            </p>
            <div className="form-group" style={{ marginTop: '1rem' }}>
              <label htmlFor="reject-reason-input">Rejection Note:</label>
              <textarea
                id="reject-reason-input"
                className="input-field"
                rows={3}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
              />
            </div>
            <div className="admin-modal-actions">
              <button
                type="button"
                className="btn btn-outline-sm"
                onClick={() => setRejectModalRefund(null)}
                disabled={busyRefundId === rejectModalRefund.id}
              >
                Go Back
              </button>
              <button
                type="button"
                className="btn btn-danger-sm"
                onClick={() => void handleConfirmReject()}
                disabled={busyRefundId === rejectModalRefund.id}
              >
                {busyRefundId === rejectModalRefund.id ? 'Rejecting...' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
