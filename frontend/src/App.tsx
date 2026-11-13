import React from 'react';
import { BrowserRouter, Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { HealthBanner } from './components/HealthBanner';
import { useHealth } from './hooks/useHealth';
import { ChatPage } from './pages/ChatPage';
import { ConsolePlaceholder } from './pages/ConsolePlaceholder';

export const App: React.FC = () => {
  const { isHealthy, errorMessage } = useHealth();

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
            Console (Phase 3)
          </NavLink>
        </nav>
      </header>

      <main>
        <Routes>
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/console" element={<ConsolePlaceholder />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
};

export default App;
