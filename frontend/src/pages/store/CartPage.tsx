import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCart } from '../../context/CartContext';
import { getProductImageUrl, handleProductImageError } from '../../utils/productImages';

export const CartPage: React.FC = () => {
  const { cart, isLoading, updateQuantity, removeItem, emptyCart } = useCart();
  const navigate = useNavigate();

  if (isLoading && !cart) {
    return <div className="cart-loading">Loading your cart...</div>;
  }

  if (!cart || !Array.isArray(cart.items) || cart.items.length === 0) {
    return (
      <div className="empty-cart-page">
        <div className="empty-cart-icon">🛒</div>
        <h2>Your shopping cart is empty</h2>
        <p>Explore our curated regional products and find authentic handcrafts and staples.</p>
        <Link to="/products" className="btn-start-shopping">
          Browse Products &rarr;
        </Link>
      </div>
    );
  }

  return (
    <div className="cart-page">
      <div className="cart-header">
        <h1>Your Shopping Cart</h1>
        <button
          type="button"
          className="btn-clear-cart"
          onClick={() => void emptyCart()}
          title="Remove all items from your cart"
        >
          Clear Cart
        </button>
      </div>

      <div className="cart-layout">
        {/* Cart items list */}
        <div className="cart-items-container">
          {cart.items.map((item) => {
            const imgUrl = getProductImageUrl({
              id: item.product_id,
              sku: item.sku,
              title: item.title,
            });
            return (
              <div key={item.product_id} className="cart-item-row">
                <div className="cart-item-img-box">
                  <img
                    src={imgUrl}
                    alt={item.title}
                    className="cart-item-img"
                    onError={(e) => handleProductImageError(e, item.product_id)}
                  />
                </div>

                <div className="cart-item-info">
                  <Link to={`/products/${item.product_id}`} className="cart-item-title">
                    <h3>{item.title}</h3>
                  </Link>
                  {item.title_ta && <p className="cart-item-ta">{item.title_ta}</p>}
                  <span className="cart-item-sku">SKU: {item.sku}</span>

                  <div className="cart-item-price-unit">
                    ₹{Number(item.price_inr).toLocaleString('en-IN')} each
                  </div>

                  {(!item.in_stock || item.quantity > item.stock_available) && (
                    <div className="cart-stock-error">
                      {item.stock_available <= 0
                        ? '⚠️ This product is currently out of stock.'
                        : `⚠️ Stock limited: only ${item.stock_available} available.`}
                    </div>
                  )}
                </div>

                <div className="cart-item-actions">
                  <div className="cart-qty-controls">
                    <button
                      type="button"
                      className="qty-btn"
                      onClick={() => void updateQuantity(item.product_id, item.quantity - 1)}
                      disabled={item.quantity <= 1}
                    >
                      -
                    </button>
                    <span className="qty-count">{item.quantity}</span>
                    <button
                      type="button"
                      className="qty-btn"
                      onClick={() => void updateQuantity(item.product_id, item.quantity + 1)}
                      disabled={item.quantity >= item.stock_available || item.quantity >= 10}
                    >
                      +
                    </button>
                  </div>

                  <div className="cart-item-subtotal">
                    ₹{Number(item.subtotal_inr).toLocaleString('en-IN')}
                  </div>

                  <button
                    type="button"
                    className="cart-item-remove-btn"
                    onClick={() => void removeItem(item.product_id)}
                    title="Remove item"
                  >
                    🗑️ Remove
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Cart summary box */}
        <div className="cart-summary-box">
          <h2>Order Summary</h2>
          <div className="summary-row">
            <span>Subtotal ({cart.total_items} items)</span>
            <span>₹{Number(cart.subtotal_inr).toLocaleString('en-IN')}</span>
          </div>
          <div className="summary-row">
            <span>Standard Shipping</span>
            <span>
              {Number(cart.shipping_fee_inr) === 0
                ? 'FREE'
                : `₹${Number(cart.shipping_fee_inr).toLocaleString('en-IN')}`}
            </span>
          </div>
          <div className="summary-divider" />
          <div className="summary-row total-row">
            <strong>Estimated Total</strong>
            <strong>₹{Number(cart.total_inr).toLocaleString('en-IN')}</strong>
          </div>

          {!cart.is_checkout_ready && (
            <div className="cart-checkout-blocked-notice">
              ⚠️ Some items in your cart exceed available inventory. Please adjust quantities.
            </div>
          )}

          <button
            type="button"
            className="btn-proceed-checkout"
            onClick={() => navigate('/checkout')}
            disabled={!cart.is_checkout_ready}
          >
            Proceed to Checkout &rarr;
          </button>

          <div className="cart-security-badges">
            <span>🔒 Safe &amp; Secure Checkout</span>
            <span>🛡️ 7-Day Return Guarantee</span>
          </div>
        </div>
      </div>
    </div>
  );
};
