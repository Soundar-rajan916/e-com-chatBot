import React from 'react';
import { Link } from 'react-router-dom';
import { BagIcon } from './icons';

export const Footer: React.FC = () => {
  return (
    <footer className="wink-footer" role="contentinfo">
      <div className="wink-footer-container">
        {/* Main Footer Grid */}
        <div className="wink-footer-grid">
          {/* Brand Column */}
          <div className="wink-footer-brand">
            <span className="wink-footer-logo" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <BagIcon size={18} /> Regional Bazaar Store
            </span>
            <p className="wink-footer-tagline">
              Bespoke formal shirts, pure silk wedding dhotis, tailored trousers, blazers, and handcrafted leather footwear from Tamil Nadu.
            </p>
            <div className="wink-footer-region">
              <span className="wink-region-dot" />
              <span>India (Tamil Nadu)</span>
            </div>
          </div>

          {/* Departments */}
          <div className="wink-footer-col">
            <h4 className="wink-footer-heading">Departments</h4>
            <ul className="wink-footer-links">
              <li>
                <Link to="/products">All Men's Wear</Link>
              </li>
              <li>
                <Link to="/products?category=formal_shirts">Formal Shirts</Link>
              </li>
              <li>
                <Link to="/products?category=casual_shirts">Casual &amp; Linen</Link>
              </li>
              <li>
                <Link to="/products?category=dhotis_ethnic">Silk Dhotis &amp; Ethnic</Link>
              </li>
              <li>
                <Link to="/products?category=trousers_chinos">Trousers &amp; Chinos</Link>
              </li>
              <li>
                <Link to="/products?category=blazers_suits">Blazers &amp; Suits</Link>
              </li>
              <li>
                <Link to="/products?category=footwear">Footwear &amp; Loafers</Link>
              </li>
              <li>
                <Link to="/products?category=accessories">Leather Accessories</Link>
              </li>
            </ul>
          </div>

          {/* Help & Policies */}
          <div className="wink-footer-col">
            <h4 className="wink-footer-heading">Support &amp; Service</h4>
            <ul className="wink-footer-links">
              <li>
                <Link to="/orders">Track Order</Link>
              </li>
              <li>
                <Link to="/orders">Returns &amp; Refunds</Link>
              </li>
              <li>
                <Link to="/dev/chat">Bilingual AI Helpdesk</Link>
              </li>
              <li>
                <span className="wink-footer-text">7-Day Return Policy</span>
              </li>
              <li>
                <span className="wink-footer-text">Free Shipping on ₹999+</span>
              </li>
            </ul>
          </div>

          {/* Organization & Access */}
          <div className="wink-footer-col">
            <h4 className="wink-footer-heading">Staff &amp; Operations</h4>
            <ul className="wink-footer-links">
              <li>
                <Link to="/console" className="wink-footer-console-link">
                  Staff Support Console ↗
                </Link>
              </li>
              <li>
                <span className="wink-footer-text">Crafted with Precision</span>
              </li>
              <li>
                <span className="wink-footer-text">Multilingual Tamil &amp; English</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Hairline Bottom Bar */}
        <div className="wink-footer-bottom">
          <p className="wink-copyright">
            &copy; {new Date().getFullYear()} Regional Bazaar. All rights reserved.
          </p>
          <div className="wink-legal-links">
            <span className="wink-legal-item">Privacy Policy</span>
            <span className="wink-legal-sep">·</span>
            <span className="wink-legal-item">Terms of Service</span>
            <span className="wink-legal-sep">·</span>
            <span className="wink-legal-item">Returns &amp; Exchange Policy</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
