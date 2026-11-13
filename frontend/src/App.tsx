import React, { useEffect, useState } from 'react';
import { BrowserRouter, Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { adminLogout, getAdminMe } from './api/client';
import { Agent } from './api/types';
import { HealthBanner } from './components/HealthBanner';
import { useHealth } from './hooks/useHealth';
import { ChatPage } from './pages/ChatPage';
import { CaseDetailPage } from './pages/console/CaseDetailPage';
import { InboxPage } from './pages/console/InboxPage';
import { LoginPage } from './pages/console/LoginPage';

export const App: React.FC = () => {
  const { isHealthy, errorMessage } = useHealth();
  const [currentAgent, setCurrentAgent] = useState<Agent | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    // Check if agent session is active
    void getAdminMe()
      .then((agent) => {
        setCurrentAgent(agent);
      })
      .catch(() => {
        setCurrentAgent(null);
      })
      .finally(() => {
        setAuthChecked(true);
      });
  }, []);

  const handleLogout = async () => {
    try {
      await adminLogout();
    } finally {
      setCurrentAgent(null);
    }
  };

  return (
    <BrowserRouter>
      <HealthBanner isHealthy={isHealthy} message={errorMessage} />
      <header className="app-header">
        <NavLink to="/chat" className="app-branding">
          <span>🛍️ Regional Support</span>
        </NavLink>
        <nav className="app-nav" aria-label="Main Navigation">
          <NavLink
            to="/chat"
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            Chat
          </NavLink>
          <NavLink
            to="/console"
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            Console
          </NavLink>
          {currentAgent && (
            <div className="nav-agent-pill">
              <span className="nav-agent-name">🎧 {currentAgent.name}</span>
              <button type="button" className="nav-logout-btn" onClick={() => void handleLogout()}>
                Sign Out
              </button>
            </div>
          )}
        </nav>
      </header>

      <main>
        {authChecked ? (
          <Routes>
            <Route path="/chat" element={<ChatPage />} />
            <Route
              path="/console/login"
              element={
                currentAgent ? (
                  <Navigate to="/console" replace />
                ) : (
                  <LoginPage onLoginSuccess={(agent) => setCurrentAgent(agent)} />
                )
              }
            />
            <Route
              path="/console"
              element={
                currentAgent ? (
                  <InboxPage currentAgent={currentAgent} onLogout={() => void handleLogout()} />
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
            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>
        ) : (
          <div className="app-loading-spinner">Loading session...</div>
        )}
      </main>
    </BrowserRouter>
  );
};

export default App;
