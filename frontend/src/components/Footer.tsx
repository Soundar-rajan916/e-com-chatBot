import React from 'react';
import { Link } from 'react-router-dom';

export const Footer: React.FC = () => {
  return (
    <footer className="store-footer">
      <div className="store-footer-container">
        {/* Brand Column */}
        <div className="footer-col footer-col-brand">
          <div className="footer-brand">
            <div className="footer-brand-badge">
              <svg className="footer-leaf-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
                <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
              </svg>
            </div>
            <div className="footer-brand-text">
              <span className="footer-brand-name">🛍️ Regional Bazaar</span>
              <span className="footer-brand-sub">LIVE BETTER · REGIONAL</span>
            </div>
          </div>
          <p className="footer-brand-desc">
            Your destination for refined men's style: bespoke linen shirts, pure silk wedding dhotis, tailored trousers, blazers, and handcrafted leather footwear.
          </p>
          <div className="footer-social-links">
            <span className="social-icon" title="Facebook">🌐</span>
            <span className="social-icon" title="Instagram">📸</span>
            <span className="social-icon" title="Twitter / X">🐦</span>
            <span className="social-icon" title="YouTube">📺</span>
          </div>
        </div>

        {/* Shop Column */}
        <div className="footer-col">
          <h4 className="footer-heading">Men's Collection</h4>
          <ul className="footer-links">
            <li>
              <Link to="/products">All Categories</Link>
            </li>
            <li>
              <Link to="/products?category=mens_wear">Formal &amp; Linen Shirts</Link>
            </li>
            <li>
              <Link to="/products?category=sarees_ethnic">Silk Dhotis &amp; Kurtas</Link>
            </li>
            <li>
              <Link to="/products?category=mens_wear">Trousers &amp; Chinos</Link>
            </li>
            <li>
              <Link to="/products?category=footwear">Leather Shoes &amp; Loafers</Link>
            </li>
          </ul>
        </div>

        {/* Customer Service Column */}
        <div className="footer-col">
          <h4 className="footer-heading">Customer Service</h4>
          <ul className="footer-links">
            <li>
              <Link to="/orders">Track Order</Link>
            </li>
            <li>
              <Link to="/orders">Returns &amp; Refunds</Link>
            </li>
            <li>
              <Link to="/dev/chat">Widget Test Harness</Link>
            </li>
            <li>
              <span className="footer-text-link">Shipping Policy (₹999 Free)</span>
            </li>
            <li>
              <span className="footer-text-link">Bilingual AI Helpdesk</span>
            </li>
          </ul>
        </div>

        {/* Company Column */}
        <div className="footer-col">
          <h4 className="footer-heading">Company</h4>
          <ul className="footer-links">
            <li>
              <span className="footer-text-link">About Us</span>
            </li>
            <li>
              <span className="footer-text-link">Weavers &amp; Artisans</span>
            </li>
            <li>
              <span className="footer-text-link">Sustainability</span>
            </li>
            <li>
              <Link to="/console" className="footer-console-link">
                🛡️ Open Staff Console
              </Link>
            </li>
          </ul>
        </div>

        {/* Download & Trust Column */}
        <div className="footer-col">
          <h4 className="footer-heading">Experience Viva</h4>
          <p className="footer-app-desc">
            Enjoy seamless shopping, order tracking, and instant AI customer care in English and தமிழ்.
          </p>
          <div className="footer-app-badges">
            <div className="app-badge">
              <span className="app-badge-icon">🍏</span>
              <div>
                <span className="app-badge-sub">Download on</span>
                <span className="app-badge-name">App Store</span>
              </div>
            </div>
            <div className="app-badge">
              <span className="app-badge-icon">▶</span>
              <div>
                <span className="app-badge-sub">GET IT ON</span>
                <span className="app-badge-name">Google Play</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Bottom Legal Bar */}
      <div className="footer-bottom">
        <div className="footer-bottom-container">
          <p className="footer-copyright">
            &copy; {new Date().getFullYear()} Regional Bazaar. Powered by Multilingual Support AI. All rights reserved.
          </p>
          <div className="footer-legal-links">
            <span className="legal-link">Privacy Policy</span>
            <span className="legal-dot">·</span>
            <span className="legal-link">Terms of Service</span>
            <span className="legal-dot">·</span>
            <span className="legal-link">Cookie Policy</span>
          </div>
          <div className="footer-region-pill">
            <span>🇮🇳</span>
            <span>India (Tamil Nadu)</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
