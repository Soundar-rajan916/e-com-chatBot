import React from 'react';
import { Link } from 'react-router-dom';

export const Footer: React.FC = () => {
  return (
    <footer className="store-footer">
      <div className="store-footer-container">
        <div className="footer-col">
          <h4>🛍️ Regional Bazaar</h4>
          <p>
            Your trusted destination for regional staples, silk sarees, cookware, and spices across
            Tamil Nadu.
          </p>
          <p className="footer-lang-pill">Supported: English &amp; தமிழ் (Tamil)</p>
        </div>

        <div className="footer-col">
          <h4>Quick Links</h4>
          <ul>
            <li>
              <Link to="/products">Browse All Products</Link>
            </li>
            <li>
              <Link to="/cart">Shopping Cart</Link>
            </li>
            <li>
              <Link to="/orders">Order Tracking</Link>
            </li>
            <li>
              <Link to="/dev/chat">Widget Test Harness</Link>
            </li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Support &amp; Trust</h4>
          <ul>
            <li>7-Day Easy Return Policy</li>
            <li>100% Authentic Regional Products</li>
            <li>Real-time Bilingual AI Support</li>
            <li>Human Escalation Guarantee</li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Staff Access</h4>
          <p>Support executive and administrator portal for dispute handling and refunds.</p>
          <Link to="/console" className="footer-console-btn">
            Open Staff Console
          </Link>
        </div>
      </div>
      <div className="footer-bottom">
        <p>&copy; {new Date().getFullYear()} Regional Bazaar. Powered by Multilingual Support AI.</p>
      </div>
    </footer>
  );
};
