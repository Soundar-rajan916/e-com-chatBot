import React, { useEffect, useState } from 'react';
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { adminLogout, getAdminMe, getBaseUrl } from './api/client';
import { Agent } from './api/types';
import { DevToolsPanel } from './components/DevToolsPanel';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Footer } from './components/Footer';
import { HealthBanner } from './components/HealthBanner';
import { Navbar } from './components/Navbar';
import { AuthProvider } from './context/AuthContext';
import { CartProvider } from './context/CartContext';
import { useHealth } from './hooks/useHealth';
import { CaseDetailPage } from './pages/console/CaseDetailPage';
import { InboxPage } from './pages/console/InboxPage';
import { LoginPage as StaffLoginPage } from './pages/console/LoginPage';
import { CartPage } from './pages/store/CartPage';
import { CheckoutPage } from './pages/store/CheckoutPage';
import { CustomerLoginPage } from './pages/store/CustomerLoginPage';
import { CustomerRegisterPage } from './pages/store/CustomerRegisterPage';
import { DevChatPage } from './pages/store/DevChatPage';
import { HomePage } from './pages/store/HomePage';
import { OrderDetailPage } from './pages/store/OrderDetailPage';
import { OrdersPage } from './pages/store/OrdersPage';
import { ProductDetailPage } from './pages/store/ProductDetailPage';
import { ProductListPage } from './pages/store/ProductListPage';

const MainLayout: React.FC = () => {
  const location = useLocation();
  const isConsoleRoute = location.pathname.startsWith('/console');

  // Staff agent state for /console
  const [currentAgent, setCurrentAgent] = useState<Agent | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    if (isConsoleRoute) {
      void getAdminMe()
        .then((agent) => setCurrentAgent(agent))
        .catch(() => setCurrentAgent(null))
        .finally(() => setAuthChecked(true));
    } else {
      setAuthChecked(true);
    }
  }, [isConsoleRoute]);

  const handleStaffLogout = async () => {
    try {
      await adminLogout();
    } finally {
      setCurrentAgent(null);
    }
  };

  return (
    <div className="app-root-container">
      {/* If in Console routes, display the staff operational header */}
      {isConsoleRoute ? (
        <header className="app-header">
          <NavLink to="/console" className="app-branding">
            <span>🛡️ Regional Support Console</span>
          </NavLink>
          <nav className="app-nav" aria-label="Console Navigation">
            <NavLink
              to="/console"
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              Console
            </NavLink>
            <NavLink to="/" className="nav-link">
              Storefront ↗
            </NavLink>
            {currentAgent && (
              <div className="nav-agent-pill">
                <span className="nav-agent-name">🎧 {currentAgent.name} ({currentAgent.role})</span>
                <button
                  type="button"
                  className="nav-logout-btn"
                  onClick={() => void handleStaffLogout()}
                >
                  Sign Out
                </button>
              </div>
            )}
          </nav>
        </header>
      ) : (
        <Navbar />
      )}

      <main className={isConsoleRoute ? 'console-main-content' : 'store-main-content'}>
        {authChecked && (
          <Routes>
            {/* Storefront Routes */}
            <Route path="/" element={<HomePage />} />
            <Route path="/products" element={<ProductListPage />} />
            <Route path="/products/:id" element={<ProductDetailPage />} />
            <Route path="/cart" element={<CartPage />} />
            <Route path="/checkout" element={<CheckoutPage />} />
            <Route path="/orders" element={<OrdersPage />} />
            <Route path="/orders/:orderNumber" element={<OrderDetailPage />} />
            <Route path="/login" element={<CustomerLoginPage />} />
            <Route path="/register" element={<CustomerRegisterPage />} />
            <Route path="/dev/chat" element={<DevChatPage />} />
            <Route path="/chat" element={<Navigate to="/dev/chat" replace />} />

            {/* Staff Console Routes */}
            <Route
              path="/console/login"
              element={
                currentAgent ? (
                  <Navigate to="/console" replace />
                ) : (
                  <StaffLoginPage onLoginSuccess={(agent) => setCurrentAgent(agent)} />
                )
              }
            />
            <Route
              path="/console"
              element={
                currentAgent ? (
                  <InboxPage
                    currentAgent={currentAgent}
                    onLogout={() => void handleStaffLogout()}
                  />
                ) : (
                  <Navigate to="/console/login" replace />
                )
              }
            />
            <Route
              path="/console/cases/:id"
              element={
                currentAgent ? (
                  <CaseDetailPage currentAgent={currentAgent} />
                ) : (
                  <Navigate to="/console/login" replace />
                )
              }
            />

            {/* Catch-all redirect to storefront */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        )}
      </main>

      {!isConsoleRoute && <Footer />}
      {!isConsoleRoute && <DevToolsPanel />}
    </div>
  );
};

export const App: React.FC = () => {
  const { isHealthy, errorMessage } = useHealth();

  useEffect(() => {
    // Initialize SupportWidget if present on window
    const initWidget = () => {
      if (typeof window !== 'undefined' && window.SupportWidget) {
        window.SupportWidget.init({
          storeName: 'Regional Bazaar',
          defaultOpen: false,
          apiUrl: getBaseUrl(),
        });
      }
    };

    if (typeof window !== 'undefined' && window.SupportWidget) {
      initWidget();
    } else {
      const interval = setInterval(() => {
        if (typeof window !== 'undefined' && window.SupportWidget) {
          clearInterval(interval);
          initWidget();
        }
      }, 200);
      return () => clearInterval(interval);
    }
  }, []);

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <CartProvider>
            <HealthBanner isHealthy={isHealthy} message={errorMessage} />
            <MainLayout />
          </CartProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
};

export default App;
