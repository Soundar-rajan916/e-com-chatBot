import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Agent } from '../../api/types';
import { AdminOrdersView } from './AdminOrdersView';
import { AdminRefundsView } from './AdminRefundsView';

interface InboxPageProps {
  currentAgent: Agent | null;
  onLogout: () => void;
}

export const InboxPage: React.FC<InboxPageProps> = ({ currentAgent, onLogout }) => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Active Main Tab: strictly 'orders' | 'refunds'
  const tabParam = searchParams.get('tab');
  const initialTab: 'orders' | 'refunds' = tabParam === 'refunds' ? 'refunds' : 'orders';
  const [activeTab, setActiveTab] = useState<'orders' | 'refunds'>(initialTab);

  // Sync tab with URL
  const handleTabChange = (tab: 'orders' | 'refunds') => {
    setActiveTab(tab);
    setSearchParams(tab === 'orders' ? {} : { tab });
  };

  return (
    <div className="inbox-container">
      {/* Top Header */}
      <div className="inbox-header">
        <div>
          <h2>Regional Bazaar Store Management</h2>
          <p className="inbox-subtitle">
            Fulfill store orders and manage customer returns.
          </p>
        </div>
        <div className="inbox-agent-badge">
          <span className="agent-avatar">🛡️</span>
          <div className="agent-meta">
            <strong>{currentAgent?.name || 'Admin'}</strong>
            <span className="agent-role">({currentAgent?.role || 'admin'})</span>
          </div>
          <button type="button" className="btn btn-outline-sm logout-btn" onClick={onLogout}>
            Sign Out
          </button>
        </div>
      </div>

      {/* Primary Top Tab Switcher */}
      <div className="admin-nav-tabs">
        <button
          type="button"
          className={`admin-nav-tab ${activeTab === 'orders' ? 'active' : ''}`}
          onClick={() => handleTabChange('orders')}
        >
          <span className="tab-icon">📦</span>
          <span>All Orders</span>
        </button>
        <button
          type="button"
          className={`admin-nav-tab ${activeTab === 'refunds' ? 'active' : ''}`}
          onClick={() => handleTabChange('refunds')}
        >
          <span className="tab-icon">💳</span>
          <span>Refunds</span>
        </button>
      </div>

      {/* Tab 1: Orders Management */}
      {activeTab === 'orders' && <AdminOrdersView />}

      {/* Tab 2: Simplified Refunds */}
      {activeTab === 'refunds' && <AdminRefundsView />}
    </div>
  );
};
