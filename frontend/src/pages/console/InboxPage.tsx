import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Agent } from '../../api/types';
import {
  CreditCardIcon,
  HeadphonesIcon,
  PackageIcon,
  ShieldIcon,
} from '../../components/icons';
import { AdminCasesView } from './AdminCasesView';
import { AdminOrdersView } from './AdminOrdersView';
import { AdminRefundsView } from './AdminRefundsView';

interface InboxPageProps {
  currentAgent: Agent | null;
  onLogout: () => void;
}

export const InboxPage: React.FC<InboxPageProps> = ({ currentAgent, onLogout }) => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Active Main Tab: 'orders' | 'refunds' | 'cases'
  const tabParam = searchParams.get('tab');
  const initialTab: 'orders' | 'refunds' | 'cases' =
    tabParam === 'refunds' ? 'refunds' : tabParam === 'cases' ? 'cases' : 'orders';
  const [activeTab, setActiveTab] = useState<'orders' | 'refunds' | 'cases'>(initialTab);

  // Sync tab with URL
  const handleTabChange = (tab: 'orders' | 'refunds' | 'cases') => {
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
            Fulfill store orders, manage customer returns, and inspect AI bot traces.
          </p>
        </div>
        <div className="inbox-agent-badge">
          <span className="agent-avatar" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
            <ShieldIcon size={16} />
          </span>
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
          <span className="tab-icon" style={{ display: 'inline-flex', alignItems: 'center' }}>
            <PackageIcon size={16} />
          </span>
          <span>All Orders</span>
        </button>
        <button
          type="button"
          className={`admin-nav-tab ${activeTab === 'refunds' ? 'active' : ''}`}
          onClick={() => handleTabChange('refunds')}
        >
          <span className="tab-icon" style={{ display: 'inline-flex', alignItems: 'center' }}>
            <CreditCardIcon size={16} />
          </span>
          <span>Refunds</span>
        </button>
        <button
          type="button"
          className={`admin-nav-tab ${activeTab === 'cases' ? 'active' : ''}`}
          onClick={() => handleTabChange('cases')}
        >
          <span className="tab-icon" style={{ display: 'inline-flex', alignItems: 'center' }}>
            <HeadphonesIcon size={16} />
          </span>
          <span>Support Cases & Traces</span>
        </button>
      </div>

      {/* Tab 1: Orders Management */}
      {activeTab === 'orders' && <AdminOrdersView />}

      {/* Tab 2: Simplified Refunds */}
      {activeTab === 'refunds' && <AdminRefundsView />}

      {/* Tab 3: Support Cases & Traces */}
      {activeTab === 'cases' && <AdminCasesView currentAgent={currentAgent} />}
    </div>
  );
};
