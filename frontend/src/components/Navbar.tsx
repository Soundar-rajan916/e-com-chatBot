import React from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useSupportWidget } from '../hooks/useSupportWidget';

export const Navbar: React.FC = () => {
  const { customer, logout } = useAuth();
  const { itemCount } = useCart();
  const { openWidget } = useSupportWidget();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <header className="store-header">
      <div className="store-header-container">
        <Link to="/" className="store-brand">
          <span className="brand-icon">🛍️</span>
          <div className="brand-text">
            <span className="brand-name">Regional Bazaar</span>
            <span className="brand-sub">Tamil Nadu Regional Store</span>
          </div>
        </Link>

        <nav className="store-nav" aria-label="Store Navigation">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `store-nav-link ${isActive ? 'active' : ''}`}
          >
            Home
          </NavLink>
          <NavLink
            to="/products"
            className={({ isActive }) => `store-nav-link ${isActive ? 'active' : ''}`}
          >
            Products
          </NavLink>
          {customer && (
            <NavLink
              to="/orders"
              className={({ isActive }) => `store-nav-link ${isActive ? 'active' : ''}`}
            >
              My Orders
            </NavLink>
          )}
        </nav>

        <div className="store-header-actions">
          <button
            type="button"
            className="chat-trigger-btn"
            onClick={openWidget}
            title="Open AI Support Chat"
          >
            💬 Support Chat
          </button>

          <Link to="/cart" className="store-cart-btn" aria-label="Cart">
            🛒 Cart
            {itemCount > 0 && <span className="cart-badge">{itemCount}</span>}
          </Link>

          {customer ? (
            <div className="customer-menu">
              <span className="customer-greeting" title={customer.email}>
                👤 {customer.name}
              </span>
              <button
                type="button"
                className="btn-auth-logout"
                onClick={() => void handleLogout()}
              >
                Sign out
              </button>
            </div>
          ) : (
            <div className="auth-links">
              <Link to="/login" className="btn-auth-login">
                Sign in
              </Link>
              <Link to="/register" className="btn-auth-register">
                Register
              </Link>
            </div>
          )}

          <Link to="/console" className="staff-console-link" title="Staff Escalation Console">
            Console
          </Link>
        </div>
      </div>
    </header>
  );
};
