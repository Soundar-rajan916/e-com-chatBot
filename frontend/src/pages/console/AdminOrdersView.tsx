import React, { useCallback, useEffect, useState } from 'react';
import { adminAdvanceOrder, adminCancelOrder, getAdminOrders } from '../../api/client';
import { AdminOrderSummary } from '../../api/types';
import { CheckIcon, RefreshIcon, PackageIcon } from '../../components/icons';

export const AdminOrdersView: React.FC = () => {
  const [orders, setOrders] = useState<AdminOrderSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Processing state per order
  const [busyOrderId, setBusyOrderId] = useState<string | null>(null);
  const [cancelModalOrder, setCancelModalOrder] = useState<AdminOrderSummary | null>(null);
  const [cancelReason, setCancelReason] = useState<string>('');

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminOrders({
        status: statusFilter || undefined,
        q: searchQuery.trim() || undefined,
      });
      setOrders(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load orders.';
      setError(msg);
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchQuery]);

  useEffect(() => {
    void fetchOrders();
  }, [fetchOrders]);

  const handleAdvance = async (order: AdminOrderSummary) => {
    setBusyOrderId(order.order_number);
    setError(null);
    setActionSuccess(null);
    try {
      const updated = await adminAdvanceOrder(order.order_number);
      setOrders((prev) =>
        prev.map((o) => (o.order_number === updated.order_number ? updated : o))
      );
      setActionSuccess(`Order ${order.order_number} advanced to ${updated.status.toUpperCase()}.`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to advance order stage.';
      setError(msg);
    } finally {
      setBusyOrderId(null);
    }
  };

  const handleConfirmCancel = async () => {
    if (!cancelModalOrder) return;
    setBusyOrderId(cancelModalOrder.order_number);
    setError(null);
    setActionSuccess(null);
    try {
      const updated = await adminCancelOrder(
        cancelModalOrder.order_number,
        cancelReason.trim() || 'Cancelled by administrator'
      );
      setOrders((prev) =>
        prev.map((o) => (o.order_number === updated.order_number ? updated : o))
      );
      setActionSuccess(`Order ${cancelModalOrder.order_number} has been cancelled and stock restocked.`);
      setCancelModalOrder(null);
      setCancelReason('');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to cancel order.';
      setError(msg);
    } finally {
      setBusyOrderId(null);
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
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    switch (s) {
      case 'placed':
        return <span className="admin-badge badge-placed">Placed</span>;
      case 'processing':
        return <span className="admin-badge badge-processing">Processing</span>;
      case 'shipped':
        return <span className="admin-badge badge-shipped">Shipped</span>;
      case 'delivered':
        return (
          <span className="admin-badge badge-delivered" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <CheckIcon size={12} /> Delivered
          </span>
        );
      case 'cancelled':
        return <span className="admin-badge badge-cancelled">Cancelled</span>;
      default:
        return <span className="admin-badge">{status}</span>;
    }
  };

  const getNextStageLabel = (currentStatus: string) => {
    const s = currentStatus.toLowerCase();
    if (s === 'placed') return 'Push to Processing';
    if (s === 'processing') return 'Push to Shipped';
    if (s === 'shipped') return 'Mark as Delivered';
    return null;
  };

  return (
    <div className="admin-orders-view">
      <div className="admin-section-header">
        <div>
          <h3>Store Orders Management</h3>
          <p className="admin-section-sub">
            View all incoming and fulfilled orders. Advance stages or cancel orders with automatic inventory restocking.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-outline-sm"
          onClick={() => void fetchOrders()}
          disabled={loading}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshIcon size={13} /> {loading ? 'Refreshing...' : 'Refresh Orders'}
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

      {/* Filter and Search Bar */}
      <div className="admin-controls-bar">
        <div className="admin-status-tabs">
          {[
            { label: 'All Orders', value: '' },
            { label: 'Placed', value: 'placed' },
            { label: 'Processing', value: 'processing' },
            { label: 'Shipped', value: 'shipped' },
            { label: 'Delivered', value: 'delivered' },
            { label: 'Cancelled', value: 'cancelled' },
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

        <div className="admin-search-box">
          <input
            type="text"
            placeholder="Search order #, customer, email, phone..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Orders List Table */}
      {loading ? (
        <div className="admin-loading-state">
          <div className="spinner" />
          <p>Loading orders...</p>
        </div>
      ) : orders.length === 0 ? (
        <div className="admin-empty-state">
          <div className="empty-icon" style={{ display: 'flex', justifyContent: 'center', marginBottom: '12px', color: '#848D9A' }}>
            <PackageIcon size={44} />
          </div>
          <h4>No orders found</h4>
          <p>There are no customer orders matching the selected filter criteria.</p>
        </div>
      ) : (
        <div className="admin-table-container">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Order Number</th>
                <th>Customer</th>
                <th>Items Ordered</th>
                <th>Amount</th>
                <th>Current Stage</th>
                <th>Placed At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => {
                const isBusy = busyOrderId === order.order_number;
                const nextAction = getNextStageLabel(order.status);
                const canCancel = ['placed', 'processing'].includes(order.status.toLowerCase());

                return (
                  <tr key={order.id} className="admin-table-row">
                    <td>
                      <strong className="order-num-text">{order.order_number}</strong>
                      <div className="order-sub-meta">
                        {order.payment_method.toUpperCase()} • {order.payment_status}
                      </div>
                    </td>
                    <td>
                      <div className="customer-name-text">{order.customer_name}</div>
                      <div className="order-sub-meta">
                        {order.customer_email || order.customer_phone || '—'}
                      </div>
                    </td>
                    <td>
                      <div className="items-summary-text" title={order.items_summary}>
                        {order.items_summary}
                      </div>
                      <div className="order-sub-meta">{order.items_count} item(s)</div>
                    </td>
                    <td>
                      <span className="order-amount-text">
                        {formatPrice(order.total_amount_inr ?? order.total_amount)}
                      </span>
                    </td>
                    <td>{getStatusBadge(order.status)}</td>
                    <td>
                      <span className="order-date-text">{formatDate(order.placed_at)}</span>
                    </td>
                    <td>
                      <div className="admin-action-btn-group">
                        {nextAction && (
                          <button
                            type="button"
                            className="btn btn-primary-sm admin-advance-btn"
                            onClick={() => void handleAdvance(order)}
                            disabled={isBusy}
                          >
                            {isBusy ? 'Updating...' : nextAction}
                          </button>
                        )}
                        {canCancel && (
                          <button
                            type="button"
                            className="btn btn-outline-danger-sm"
                            onClick={() => {
                              setCancelModalOrder(order);
                              setCancelReason('');
                            }}
                            disabled={isBusy}
                          >
                            Cancel
                          </button>
                        )}
                        {!nextAction && !canCancel && (
                          <span className="text-muted text-sm">— Completed —</span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Cancel Order Confirmation Modal */}
      {cancelModalOrder && (
        <div className="admin-modal-overlay">
          <div className="admin-modal-content">
            <h4>Cancel Order {cancelModalOrder.order_number}</h4>
            <p>
              Are you sure you want to cancel this order for{' '}
              <strong>{cancelModalOrder.customer_name}</strong>?
            </p>
            <p className="admin-modal-hint">
              Products will automatically be restocked back into store inventory.
            </p>
            <div className="form-group" style={{ marginTop: '1rem' }}>
              <label htmlFor="cancel-reason-input">Reason for Cancellation:</label>
              <input
                id="cancel-reason-input"
                type="text"
                className="input-field"
                placeholder="e.g. Customer requested cancellation / Payment issue"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
              />
            </div>
            <div className="admin-modal-actions">
              <button
                type="button"
                className="btn btn-outline-sm"
                onClick={() => setCancelModalOrder(null)}
                disabled={busyOrderId === cancelModalOrder.order_number}
              >
                Go Back
              </button>
              <button
                type="button"
                className="btn btn-danger-sm"
                onClick={() => void handleConfirmCancel()}
                disabled={busyOrderId === cancelModalOrder.order_number}
              >
                {busyOrderId === cancelModalOrder.order_number ? 'Cancelling...' : 'Confirm Cancellation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
