import React, { useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useSupportWidget } from '../hooks/useSupportWidget';
import {
  MenuIcon,
  SearchIcon,
  BagIcon,
  UserIcon,
  CloseIcon,
} from './icons';

export const Navbar: React.FC = () => {
  const { customer, logout } = useAuth();
  const { itemCount } = useCart();
  const { openWidget } = useSupportWidget();
  const navigate = useNavigate();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const currentCategory = searchParams.get('category') || '';
  const isProductsPage = location.pathname === '/products';

  const [searchQuery, setSearchQuery] = useState('');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [selectedLang, setSelectedLang] = useState<'en' | 'ta'>('en');

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
    setMobileMenuOpen(false);
  };

  const toggleLanguage = () => {
    setSelectedLang((prev) => (prev === 'en' ? 'ta' : 'en'));
  };

  return (
    <header className="wink-header" role="banner">
      {/* Primary Slim Bar */}
      <div className="wink-header-primary">
        <div className="wink-header-inner">
          {/* Left: Mobile Menu Toggle & Desktop Quick Nav */}
          <div className="wink-header-left">
            <button
              type="button"
              className="wink-menu-trigger"
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? <CloseIcon size={20} /> : <MenuIcon size={20} />}
            </button>
            <nav className="wink-desktop-nav" aria-label="Main Navigation">
              <NavLink to="/" end className={({ isActive }) => `wink-nav-link ${isActive ? 'active' : ''}`}>
                Home
              </NavLink>
              <NavLink to="/products" className={({ isActive }) => `wink-nav-link ${isActive ? 'active' : ''}`}>
                Products
              </NavLink>
            </nav>
          </div>

          {/* Centre: Refined Editorial Wordmark */}
          <div className="wink-header-center">
            <Link to="/" className="wink-wordmark" aria-label="Regional Bazaar Home">
              <span className="wink-wordmark-title">Regional Bazaar</span>
            </Link>
          </div>

          {/* Right: Actions, Language Toggle, Account, Orders & Cart */}
          <div className="wink-header-right">
            {/* Language Segmented Pill */}
            <button
              type="button"
              className="wink-lang-pill"
              onClick={toggleLanguage}
              title="Toggle English / தமிழ்"
              aria-label="Toggle language between English and Tamil"
            >
              <span className={`wink-lang-segment ${selectedLang === 'en' ? 'active' : ''}`}>EN</span>
              <span className="wink-lang-divider">|</span>
              <span className={`wink-lang-segment ${selectedLang === 'ta' ? 'active' : ''}`}>தமிழ்</span>
            </button>

            {/* Account / Login */}
            {customer ? (
              <div className="wink-user-menu">
                <Link to="/account" className="wink-icon-btn" title={customer.email}>
                  <UserIcon size={16} />
                  <span className="wink-user-name">
                    {(customer.name || customer.email || 'Account').split(' ')[0]}
                  </span>
                </Link>
                <button
                  type="button"
                  className="wink-signout-btn"
                  onClick={() => void handleLogout()}
                >
                  Sign out
                </button>
              </div>
            ) : (
              <div className="wink-auth-actions">
                <Link to="/login" className="wink-text-link">
                  Sign in
                </Link>
                <Link to="/register" className="wink-pill-link">
                  Register
                </Link>
              </div>
            )}

            {/* Orders */}
            <Link to="/orders" className="wink-text-link wink-orders-link" title="Track Orders">
              Orders
            </Link>

            {/* Console Link */}
            <Link to="/console" className="wink-text-link" title="Staff Support Console">
              Console
            </Link>

            {/* Cart with Item Count Badge */}
            <Link to="/cart" className="wink-cart-btn" aria-label="Shopping Cart">
              <BagIcon size={19} />
              <span className="wink-cart-label">Cart</span>
              {itemCount > 0 && <span className="cart-badge">{itemCount}</span>}
            </Link>

            {/* Support Widget Button */}
            <button
              type="button"
              className="wink-support-btn"
              onClick={openWidget}
              title="Open Support Chat"
              aria-label="Open AI Support Chat"
            >
              Support
            </button>
          </div>
        </div>
      </div>

      {/* Secondary Controls Bar: Search & Category Pills */}
      <div className="wink-header-secondary">
        <div className="wink-header-inner-sub">
          {/* Search Pill */}
          <form className="wink-search-form" onSubmit={handleSearch}>
            <div className="wink-search-pill">
              <SearchIcon size={16} className="wink-search-icon" />
              <input
                type="search"
                className="wink-search-input"
                placeholder="Search products, materials, styles..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search products"
              />
              {searchQuery && (
                <button
                  type="button"
                  className="wink-search-clear"
                  onClick={() => setSearchQuery('')}
                  aria-label="Clear search"
                >
                  <CloseIcon size={14} />
                </button>
              )}
            </div>
          </form>

          {/* Quiet Category Pills */}
          <nav className="wink-category-pills" aria-label="Category Filters">
            <Link
              to="/products"
              className={`wink-cat-pill ${isProductsPage && !currentCategory ? 'active' : ''}`}
            >
              All
            </Link>
            <Link
              to="/products?category=formal_shirts"
              className={`wink-cat-pill ${isProductsPage && currentCategory === 'formal_shirts' ? 'active' : ''}`}
            >
              Formal Shirts
            </Link>
            <Link
              to="/products?category=casual_shirts"
              className={`wink-cat-pill ${isProductsPage && currentCategory === 'casual_shirts' ? 'active' : ''}`}
            >
              Casual &amp; Linen
            </Link>
            <Link
              to="/products?category=dhotis_ethnic"
              className={`wink-cat-pill ${isProductsPage && currentCategory === 'dhotis_ethnic' ? 'active' : ''}`}
            >
              Dhotis &amp; Ethnic
            </Link>
            <Link
              to="/products?category=trousers_chinos"
              className={`wink-cat-pill ${isProductsPage && currentCategory === 'trousers_chinos' ? 'active' : ''}`}
            >
              Trousers
            </Link>
            <Link
              to="/products?category=blazers_suits"
              className={`wink-cat-pill ${isProductsPage && currentCategory === 'blazers_suits' ? 'active' : ''}`}
            >
              Blazers &amp; Suits
            </Link>
            <Link
              to="/products?category=footwear"
              className={`wink-cat-pill ${isProductsPage && currentCategory === 'footwear' ? 'active' : ''}`}
            >
              Footwear
            </Link>
            <Link
              to="/products?category=accessories"
              className={`wink-cat-pill ${isProductsPage && currentCategory === 'accessories' ? 'active' : ''}`}
            >
              Accessories
            </Link>
          </nav>
        </div>
      </div>

      {/* Mobile Drawer (Accessible, keyboard-trappable, closed by default) */}
      {mobileMenuOpen && (
        <div className="wink-mobile-drawer" role="dialog" aria-modal="true" aria-label="Mobile Navigation">
          <div className="wink-mobile-drawer-content">
            <nav className="wink-mobile-nav">
              <Link to="/" className="wink-mobile-link" onClick={() => setMobileMenuOpen(false)}>
                Home
              </Link>
              <Link to="/products" className="wink-mobile-link" onClick={() => setMobileMenuOpen(false)}>
                Products
              </Link>
              <Link to="/orders" className="wink-mobile-link" onClick={() => setMobileMenuOpen(false)}>
                Orders
              </Link>
              <Link to="/cart" className="wink-mobile-link" onClick={() => setMobileMenuOpen(false)}>
                Cart ({itemCount})
              </Link>
              {customer ? (
                <>
                  <Link to="/account" className="wink-mobile-link" onClick={() => setMobileMenuOpen(false)}>
                    My Account
                  </Link>
                  <button
                    type="button"
                    className="wink-mobile-link wink-mobile-logout"
                    onClick={() => {
                      setMobileMenuOpen(false);
                      void handleLogout();
                    }}
                  >
                    Sign Out
                  </button>
                </>
              ) : (
                <>
                  <Link to="/login" className="wink-mobile-link" onClick={() => setMobileMenuOpen(false)}>
                    Sign In
                  </Link>
                  <Link to="/register" className="wink-mobile-link" onClick={() => setMobileMenuOpen(false)}>
                    Create Account
                  </Link>
                </>
              )}
              <div className="wink-mobile-divider" />
              <Link to="/console" className="wink-mobile-link" onClick={() => setMobileMenuOpen(false)}>
                Staff Console ↗
              </Link>
            </nav>
          </div>
        </div>
      )}
    </header>
  );
};
