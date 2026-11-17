import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  cancelCustomerOrder,
  getCustomerOrderDetail,
  returnCustomerOrder,
} from '../../api/client';
import { OrderDetail } from '../../api/types';
import { useSupportWidget } from '../../hooks/useSupportWidget';

const STATUS_STEPS = ['pending', 'confirmed', 'shipped', 'out_for_delivery', 'delivered'];

export const OrderDetailPage: React.FC = () => {
  const { orderNumber } = useParams<{ orderNumber: string }>();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Return modal state
  const [showReturnModal, setShowReturnModal] = useState(false);
  const [returnReason, setReturnReason] = useState('');
  const [returnItems, setReturnItems] = useState<Record<string, number>>({});
  const [isSubmittingReturn, setIsSubmittingReturn] = useState(false);
  const [returnSuccessNotice, setReturnSuccessNotice] = useState<string | null>(null);

  // Cancel state
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [isSubmittingCancel, setIsSubmittingCancel] = useState(false);

  const { askAboutOrder } = useSupportWidget();

  const loadOrder = async () => {
    if (!orderNumber) return;
    setIsLoading(true);
    try {
      const data = await getCustomerOrderDetail(orderNumber);
      setOrder(data);
      // Initialize return items map
      const initialMap: Record<string, number> = {};
      data.items.forEach((it) => {
        initialMap[it.product_id] = it.quantity;
      });
      setReturnItems(initialMap);
    } catch (err: any) {
      setErrorMsg(err.userMessage || err.message || 'Failed to load order');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadOrder();
  }, [orderNumber]);

  const handleCancelOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!order) return;
    setIsSubmittingCancel(true);
    try {
      const updated = await cancelCustomerOrder(order.order_number, cancelReason || 'Customer requested');
      setOrder(updated);
      setShowCancelModal(false);
    } catch (err: any) {
      alert(err.userMessage || err.message || 'Failed to cancel order');
    } finally {
      setIsSubmittingCancel(false);
    }
  };

  const handleReturnSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!order) return;
    setIsSubmittingReturn(true);
    try {
      const itemsToReturn = Object.entries(returnItems)
        .filter(([_, qty]) => qty > 0)
        .map(([product_id, quantity]) => ({ product_id, quantity }));

      if (itemsToReturn.length === 0) {
        alert('Please select at least one item quantity to return.');
        setIsSubmittingReturn(false);
        return;
      }

      const res = await returnCustomerOrder(order.order_number, itemsToReturn, returnReason);
      setReturnSuccessNotice(
        `Return request recorded (${res.status}). Refund ₹${res.amount_inr}.`
      );
      setShowReturnModal(false);
      await loadOrder();

      // Open widget with order context
      askAboutOrder({
        order_number: order.order_number,
        status: order.status,
        total_amount_inr: order.total_amount_inr,
      });
    } catch (err: any) {
      alert(err.userMessage || err.message || 'Return request failed');
    } finally {
      setIsSubmittingReturn(false);
    }
  };

  if (isLoading) {
    return <div className="detail-loading">Loading order details...</div>;
  }

  if (errorMsg || !order) {
    return (
      <div className="order-not-found">
        <h2>Order Not Found</h2>
        <p>{errorMsg || 'Could not find details for this order.'}</p>
        <Link to="/orders" className="btn-back-orders">
          &larr; Back to Orders
        </Link>
      </div>
    );
  }

  const currentStepIndex = STATUS_STEPS.indexOf(order.status.toLowerCase());
  const isTerminal = order.status.toLowerCase() === 'cancelled' || order.status.toLowerCase() === 'returned';

  return (
    <div className="order-detail-page">
      <div className="order-detail-header">
        <div>
          <Link to="/orders" className="back-link">
            &larr; All Orders
          </Link>
          <h1>Order #{order.order_number}</h1>
          <span className="order-placed-at">
            Placed on {new Date(order.created_at).toLocaleString()}
          </span>
        </div>

        <div className="order-header-actions">
          <button
            type="button"
            className="btn-order-chat"
            onClick={() =>
              askAboutOrder({
                order_number: order.order_number,
                status: order.status,
                total_amount_inr: order.total_amount_inr,
              })
            }
          >
            💬 Ask AI Support
          </button>

          {order.is_cancellable && (
            <button
              type="button"
              className="btn-order-cancel"
              onClick={() => setShowCancelModal(true)}
            >
              Cancel Order
            </button>
          )}

          {order.is_returnable && (
            <button
              type="button"
              className="btn-order-return"
              onClick={() => setShowReturnModal(true)}
            >
              Request Return
            </button>
          )}
        </div>
      </div>

      {returnSuccessNotice && (
        <div className="return-success-banner">{returnSuccessNotice}</div>
      )}

      {/* Progress Stepper (if not cancelled/returned) */}
      {!isTerminal ? (
        <div className="status-timeline-card">
          <div className="status-steps">
            {STATUS_STEPS.map((step, idx) => {
              const isDone = currentStepIndex >= idx;
              const isCurrent = currentStepIndex === idx;
              return (
                <div
                  key={step}
                  className={`step-item ${isDone ? 'done' : ''} ${isCurrent ? 'current' : ''}`}
                >
                  <div className="step-circle">{isDone ? '✓' : idx + 1}</div>
                  <span className="step-label">
                    {step.replace(/_/g, ' ').toUpperCase()}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="terminal-status-card">
          <span className="terminal-badge">{order.status.toUpperCase()}</span>
          {order.cancelled_at && (
            <p>
              Cancelled on {new Date(order.cancelled_at).toLocaleDateString()}
              {order.cancellation_reason && ` - Reason: ${order.cancellation_reason}`}
            </p>
          )}
        </div>
      )}

      {/* Linked Refund Notice */}
      {order.refund && (
        <div className={`order-refund-card refund-${order.refund.status}`}>
          <h3>Refund Status: {order.refund.status.toUpperCase()}</h3>
          <p>
            Amount: <strong>₹{Number(order.refund.amount).toLocaleString('en-IN')}</strong> | Reason:{' '}
            {order.refund.reason}
          </p>
          {order.refund.status === 'pending_approval' && (
            <p className="refund-pending-text">
              ⏳ This refund exceeds the automatic approval threshold and has been assigned to our
              human support team for verification.
            </p>
          )}
        </div>
      )}

      <div className="order-info-grid">
        {/* Items Card */}
        <div className="order-box order-items-box">
          <h2>Items in this Order ({order.items.length})</h2>
          <table className="order-items-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {order.items.map((it) => (
                <tr key={it.id}>
                  <td>
                    <Link to={`/products/${it.product_id}`} className="order-item-link">
                      {it.title}
                    </Link>
                  </td>
                  <td>{it.quantity}</td>
                  <td>₹{Number(it.unit_price_inr).toLocaleString('en-IN')}</td>
                  <td>₹{Number(it.subtotal_inr).toLocaleString('en-IN')}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="order-cost-breakdown">
            <div className="cost-row">
              <strong>Order Total:</strong>
              <strong>₹{Number(order.total_amount_inr).toLocaleString('en-IN')}</strong>
            </div>
          </div>
        </div>

        {/* Shipping & Payment Card */}
        <div className="order-box order-details-box">
          <h2>Shipping Address</h2>
          <div className="address-block">
            <strong>{order.shipping_address?.full_name || 'N/A'}</strong>
            <p>{order.shipping_address?.street || ''}</p>
            <p>
              {[
                order.shipping_address?.city,
                order.shipping_address?.state,
                order.shipping_address?.pincode,
              ]
                .filter(Boolean)
                .join(', ')}
            </p>
          </div>

          <div className="summary-divider" />

          <h2>Payment Information</h2>
          <p>
            <strong>Method:</strong>{' '}
            {order.payment_method === 'cod' ? 'Cash on Delivery (COD)' : 'Mock Card Payment'}
          </p>
          <p>
            <strong>Status:</strong>{' '}
            <span className={`payment-status ${order.payment_status}`}>
              {order.payment_status.toUpperCase()}
            </span>
          </p>

          <div className="summary-divider" />

          <h2>Delivery &amp; Return Info</h2>
          <p>
            {order.delivered_at
              ? `Delivered on: ${new Date(order.delivered_at).toLocaleDateString()}`
              : 'Not yet delivered'}
          </p>
          {order.days_since_delivery !== null && (
            <p>
              Delivered <strong>{order.days_since_delivery} day(s)</strong> ago
              {order.is_returnable ? ' (Eligible for 7-day return)' : ' (Return window expired)'}
            </p>
          )}
        </div>
      </div>

      {/* Status History Timeline */}
      <div className="order-box history-box">
        <h2>Order Audit &amp; Status Log</h2>
        <div className="history-timeline">
          {order.status_history.map((h) => (
            <div key={h.id} className="history-item">
              <span className="history-bullet" />
              <div className="history-content">
                <strong>{h.status.toUpperCase()}</strong>
                {h.note && <p className="history-note">{h.note}</p>}
                <span className="history-time">{new Date(h.created_at).toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Return Modal */}
      {showReturnModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <h2>Request Return &amp; Refund</h2>
            <p>Select quantities and state the reason for return:</p>
            <form onSubmit={handleReturnSubmit}>
              <div className="return-items-selection">
                {order.items.map((it) => (
                  <div key={it.product_id} className="return-item-line">
                    <span>{it.title} (Max: {it.quantity})</span>
                    <input
                      type="number"
                      min="0"
                      max={it.quantity}
                      value={returnItems[it.product_id] || 0}
                      onChange={(e) =>
                        setReturnItems({
                          ...returnItems,
                          [it.product_id]: parseInt(e.target.value, 10) || 0,
                        })
                      }
                    />
                  </div>
                ))}
              </div>

              <div className="form-group">
                <label htmlFor="rr">Return Reason</label>
                <textarea
                  id="rr"
                  required
                  rows={3}
                  value={returnReason}
                  onChange={(e) => setReturnReason(e.target.value)}
                  placeholder="e.g., Damaged item received, incorrect size, or defective piece"
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-modal-cancel"
                  onClick={() => setShowReturnModal(false)}
                >
                  Close
                </button>
                <button type="submit" className="btn-modal-submit" disabled={isSubmittingReturn}>
                  {isSubmittingReturn ? 'Submitting...' : 'Confirm Return'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Cancel Modal */}
      {showCancelModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <h2>Cancel Order #{order.order_number}</h2>
            <p>Are you sure you want to cancel this order? Stock will be released.</p>
            <form onSubmit={handleCancelOrder}>
              <div className="form-group">
                <label htmlFor="cr">Reason for cancellation</label>
                <input
                  id="cr"
                  type="text"
                  required
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder="e.g. Changed mind / ordered by mistake"
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-modal-cancel"
                  onClick={() => setShowCancelModal(false)}
                >
                  Back
                </button>
                <button type="submit" className="btn-modal-danger" disabled={isSubmittingCancel}>
                  {isSubmittingCancel ? 'Cancelling...' : 'Confirm Cancellation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
