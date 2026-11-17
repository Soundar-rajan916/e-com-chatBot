import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getCustomerOrders } from '../../api/client';
import { OrderDetail } from '../../api/types';
import { useAuth } from '../../context/AuthContext';
import { useSupportWidget } from '../../hooks/useSupportWidget';

export const OrdersPage: React.FC = () => {
  const { customer } = useAuth();
  const [orders, setOrders] = useState<OrderDetail[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { askAboutOrder } = useSupportWidget();

  useEffect(() => {
    if (!customer) {
      setIsLoading(false);
      return;
    }
    async function loadOrders() {
      try {
        const ords = await getCustomerOrders();
        setOrders(Array.isArray(ords) ? ords : []);
      } catch (err) {
        console.error('Failed to load orders', err);
        setOrders([]);
      } finally {
        setIsLoading(false);
      }
    }
    void loadOrders();
  }, [customer]);

  if (!customer) {
    return (
      <div className="orders-auth-required">
        <h2>Please sign in to view your orders</h2>
        <Link to="/login?redirect=/orders" className="btn-auth-login">
          Sign In &rarr;
        </Link>
      </div>
    );
  }

  if (isLoading) {
    return <div className="orders-loading">Loading your order history...</div>;
  }

  return (
    <div className="orders-page">
      <h1>My Order History</h1>
      <p className="orders-sub">Track order packages, initiate returns, and view delivery updates.</p>

      {orders.length === 0 ? (
        <div className="empty-orders-card">
          <div className="empty-icon">📦</div>
          <h2>No orders placed yet</h2>
          <p>You haven't made any purchases with us yet.</p>
          <Link to="/products" className="btn-start-shopping">
            Start Shopping &rarr;
          </Link>
        </div>
      ) : (
        <div className="orders-list">
          {orders.map((o) => (
            <div key={o.id} className="order-card">
              <div className="order-card-header">
                <div>
                  <span className="order-number-title">Order #{o.order_number}</span>
                  <span className="order-date-text">
                    Placed on {new Date(o.created_at).toLocaleDateString()}
                  </span>
                </div>

                <div className="order-header-right">
                  <span className={`status-pill ${o.status.toLowerCase()}`}>{o.status}</span>
                  <span className="order-total-amount">
                    ₹{Number(o.total_amount_inr).toLocaleString('en-IN')}
                  </span>
                </div>
              </div>

              <div className="order-card-body">
                <div className="order-items-snippet">
                  {(o.items || []).map((it) => (
                    <div key={it.id} className="order-snippet-row">
                      <span className="it-bullet">•</span>
                      <span className="it-name">{it.title}</span>
                      <span className="it-qty">x{it.quantity}</span>
                      <span className="it-price">
                        ₹{Number(it.subtotal_inr).toLocaleString('en-IN')}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="order-actions-bar">
                  <Link to={`/orders/${o.order_number}`} className="btn-order-details">
                    View Details &amp; Tracking &rarr;
                  </Link>
                  <button
                    type="button"
                    className="btn-order-ask-ai"
                    onClick={() =>
                      askAboutOrder({
                        order_number: o.order_number,
                        status: o.status,
                        total_amount_inr: o.total_amount_inr,
                      })
                    }
                  >
                    💬 Ask AI about this order
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
