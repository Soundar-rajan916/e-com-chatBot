import React, { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useSupportWidget } from '../hooks/useSupportWidget';

export const Navbar: React.FC = () => {
  const { customer, logout } = useAuth();
  const { itemCount } = useCart();
  const { openWidget } = useSupportWidget();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/products?q=${encodeURIComponent(searchQuery.trim())}`);
    } else {
      navigate('/products');
    }
  };

  return (
    <header className="store-header">
      {/* Top Announcement Bar */}
      <div className="store-top-bar">
        <div className="store-top-bar-container">
          <span className="top-bar-item">✨ Free Shipping on Orders Over ₹999</span>
          <span className="top-bar-separator">|</span>
          <span className="top-bar-item">🔄 7-Day Easy Returns &amp; Exchanges</span>
          <span className="top-bar-separator">|</span>
          <span className="top-bar-item">👔 100% Premium Men's Collection</span>
          <span className="top-bar-separator">|</span>
          <span className="top-bar-item">🌐 Multilingual AI Fit &amp; Style Support (English &amp; தமிழ்)</span>
        </div>
      </div>

      {/* Main Header */}
      <div className="store-header-main">
        <div className="store-header-container">
          {/* Brand Logo */}
          <Link to="/" className="store-brand" aria-label="Regional Bazaar Home">
            <div className="brand-logo-badge">
              <svg className="brand-leaf-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
                <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
              </svg>
            </div>
            <div className="brand-text">
              <span className="brand-name">Regional Bazaar</span>
              <span className="brand-sub">MEN · LIVE BETTER</span>
            </div>
          </Link>

          {/* Search Bar */}
          <form className="store-search-form" onSubmit={handleSearch}>
            <div className="store-search-wrapper">
              <input
                type="text"
                className="store-search-input"
                placeholder="Search formal shirts, linen shirts, silk dhotis, blazers, leather shoes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search products"
              />
              <button type="submit" className="store-search-btn" aria-label="Submit search">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </button>
            </div>
          </form>

          {/* Header Action Hub */}
          <div className="store-header-actions">
            {customer ? (
              <div className="customer-menu">
                <Link to="/orders" className="header-action-item" title={customer.email}>
                  <span className="action-icon">👤</span>
                  <span className="action-label">{(customer.name || customer.email || 'Account').split(' ')[0]}</span>
                </Link>
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
                <Link to="/login" className="header-action-item">
                  <span className="action-icon">👤</span>
                  <span className="action-label">Sign in</span>
                </Link>
                <Link to="/register" className="btn-auth-register">
                  Register
                </Link>
              </div>
            )}

            <Link to="/orders" className="header-action-item" title="Track Orders">
              <span className="action-icon">📦</span>
              <span className="action-label">Orders</span>
            </Link>

            <Link to="/cart" className="store-cart-btn" aria-label="Shopping Cart">
              <span className="cart-icon-wrapper">
                🛒
                {itemCount > 0 && <span className="cart-badge">{itemCount}</span>}
              </span>
              <span className="cart-text">Cart</span>
            </Link>

            <button
              type="button"
              className="chat-trigger-btn"
              onClick={openWidget}
              title="Open AI Support Chat"
            >
              💬 Support
            </button>
          </div>
        </div>
      </div>

      {/* Sub Navigation Bar */}
      <div className="store-subnav">
        <div className="store-subnav-container">
          <Link to="/products" className="subnav-category-btn">
            <span className="category-hamburger">☰</span>
            <span>All Categories</span>
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
            <NavLink
              to="/products?category=formal_shirts"
              className={({ isActive }) => `store-nav-link ${isActive ? 'active' : ''}`}
            >
              Formal Shirts
            </NavLink>
            <NavLink
              to="/products?category=casual_shirts"
              className={({ isActive }) => `store-nav-link ${isActive ? 'active' : ''}`}
            >
              Casual &amp; Linen
            </NavLink>
            <NavLink
              to="/products?category=dhotis_ethnic"
              className={({ isActive }) => `store-nav-link ${isActive ? 'active' : ''}`}
            >
              Dhotis &amp; Ethnic
            </NavLink>
            <NavLink
              to="/products?category=trousers_chinos"
              className={({ isActive }) => `store-nav-link ${isActive ? 'active' : ''}`}
            >
              Trousers &amp; Chinos
            </NavLink>
            <NavLink
              to="/products?category=blazers_suits"
              className={({ isActive }) => `store-nav-link ${isActive ? 'active' : ''}`}
            >
              Blazers &amp; Suits
            </NavLink>
            <NavLink
              to="/products?category=footwear"
              className={({ isActive }) => `store-nav-link ${isActive ? 'active' : ''}`}
            >
              Footwear
            </NavLink>
            <NavLink
              to="/products?category=accessories"
              className={({ isActive }) => `store-nav-link ${isActive ? 'active' : ''}`}
            >
              Accessories
            </NavLink>
            {customer && (
              <NavLink
                to="/orders"
                className={({ isActive }) => `store-nav-link ${isActive ? 'active' : ''}`}
              >
                My Orders
              </NavLink>
            )}
            <Link to="/console" className="staff-console-link" title="Staff Escalation Console">
              Console
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
};
