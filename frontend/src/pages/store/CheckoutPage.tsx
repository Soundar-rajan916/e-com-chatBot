import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { checkoutOrder } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';

export const CheckoutPage: React.FC = () => {
  const { customer } = useAuth();
  const { cart, refreshCart } = useCart();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState(customer?.name || '');
  const [street, setStreet] = useState('14 Gandhi Road, T. Nagar');
  const [city, setCity] = useState('Chennai');
  const [state, setState] = useState('Tamil Nadu');
  const [pincode, setPincode] = useState('600017');

  const [paymentMethod, setPaymentMethod] = useState<'mock_card' | 'cod'>('mock_card');
  const [mockOutcome, setMockOutcome] = useState<'success' | 'failure'>('success');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!customer) {
    return (
      <div className="checkout-auth-required">
        <h2>Sign in required to Checkout</h2>
        <p>Please log in or create a customer account to finalize your order and delivery address.</p>
        <div className="auth-required-actions">
          <Link to="/login?redirect=/checkout" className="btn-auth-login">
            Sign In &rarr;
          </Link>
          <Link to="/register?redirect=/checkout" className="btn-auth-register">
            Create Account &rarr;
          </Link>
        </div>
      </div>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="empty-cart-page">
        <h2>Your cart is empty</h2>
        <p>Add some products to your cart before proceeding to checkout.</p>
        <Link to="/products" className="btn-start-shopping">
          Browse Products &rarr;
        </Link>
      </div>
    );
  }

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName || !street || !city || !state || !pincode) {
      setErrorMsg('Please complete all shipping address fields.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const idempotencyKey = `chk_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
      const order = await checkoutOrder(
        {
          shipping_address: {
            full_name: fullName,
            street,
            city,
            state,
            pincode,
          },
          payment_method: paymentMethod,
          mock_payment_outcome: paymentMethod === 'mock_card' ? mockOutcome : undefined,
        },
        idempotencyKey
      );

      await refreshCart();
      navigate(`/orders/${order.order_number}`);
    } catch (err: any) {
      setErrorMsg(err.userMessage || err.message || 'Checkout failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="checkout-page">
      <h1>Checkout &amp; Place Order</h1>

      {errorMsg && <div className="checkout-error-banner">{errorMsg}</div>}

      <div className="checkout-layout">
        {/* Left Form */}
        <form onSubmit={handlePlaceOrder} className="checkout-form">
          <div className="checkout-section">
            <h2>1. Shipping Address</h2>
            <div className="form-group">
              <label htmlFor="fn">Full Name</label>
              <input
                id="fn"
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Receiver's name"
              />
            </div>

            <div className="form-group">
              <label htmlFor="st">Street Address</label>
              <input
                id="st"
                type="text"
                required
                value={street}
                onChange={(e) => setStreet(e.target.value)}
                placeholder="Door no, Street name, Area"
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="city">City</label>
                <input
                  id="city"
                  type="text"
                  required
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label htmlFor="state">State</label>
                <input
                  id="state"
                  type="text"
                  required
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label htmlFor="pincode">Pincode</label>
                <input
                  id="pincode"
                  type="text"
                  required
                  pattern="[0-9]{6}"
                  value={pincode}
                  onChange={(e) => setPincode(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="checkout-section">
            <h2>2. Payment Method</h2>

            <div className="payment-options">
              <label className={`payment-option ${paymentMethod === 'mock_card' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="payment"
                  checked={paymentMethod === 'mock_card'}
                  onChange={() => setPaymentMethod('mock_card')}
                />
                <div className="payment-option-text">
                  <strong>Pay now (Demo Card)</strong>
                  <span>Simulated card transaction (no real card details collected)</span>
                </div>
              </label>

              {paymentMethod === 'mock_card' && (
                <div className="mock-payment-controls">
                  <span className="mock-note">Test Outcome:</span>
                  <label className="mock-radio">
                    <input
                      type="radio"
                      name="mockOutcome"
                      checked={mockOutcome === 'success'}
                      onChange={() => setMockOutcome('success')}
                    />
                    Simulate Success
                  </label>
                  <label className="mock-radio">
                    <input
                      type="radio"
                      name="mockOutcome"
                      checked={mockOutcome === 'failure'}
                      onChange={() => setMockOutcome('failure')}
                    />
                    Simulate Card Decline
                  </label>
                </div>
              )}

              <label className={`payment-option ${paymentMethod === 'cod' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="payment"
                  checked={paymentMethod === 'cod'}
                  onChange={() => setPaymentMethod('cod')}
                />
                <div className="payment-option-text">
                  <strong>Cash on Delivery (COD)</strong>
                  <span>Pay upon receiving package at your door</span>
                </div>
              </label>
            </div>
          </div>

          <button
            type="submit"
            className="btn-place-order"
            disabled={isSubmitting || !cart.is_checkout_ready}
          >
            {isSubmitting
              ? 'Processing Order...'
              : `Place Order • ₹${Number(cart.total_inr).toLocaleString('en-IN')}`}
          </button>
        </form>

        {/* Right Order Review */}
        <div className="checkout-summary-box">
          <h2>Order Items ({cart.total_items})</h2>
          <div className="checkout-items-list">
            {cart.items.map((it) => (
              <div key={it.product_id} className="checkout-item-preview">
                <span className="it-qty">{it.quantity}x</span>
                <span className="it-title">{it.title}</span>
                <span className="it-subtotal">₹{Number(it.subtotal_inr).toLocaleString('en-IN')}</span>
              </div>
            ))}
          </div>

          <div className="summary-divider" />
          <div className="summary-row">
            <span>Subtotal</span>
            <span>₹{Number(cart.subtotal_inr).toLocaleString('en-IN')}</span>
          </div>
          <div className="summary-row">
            <span>Shipping</span>
            <span>
              {Number(cart.shipping_fee_inr) === 0
                ? 'FREE'
                : `₹${Number(cart.shipping_fee_inr).toLocaleString('en-IN')}`}
            </span>
          </div>
          <div className="summary-row total-row">
            <strong>Total Payable</strong>
            <strong>₹{Number(cart.total_inr).toLocaleString('en-IN')}</strong>
          </div>
        </div>
      </div>
    </div>
  );
};
