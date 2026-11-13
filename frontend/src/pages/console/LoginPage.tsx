import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminLogin, ApiError } from '../../api/client';
import { Agent } from '../../api/types';

interface LoginPageProps {
  onLoginSuccess?: (agent: Agent) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;

    setLoading(true);
    setError(null);

    try {
      const agent = await adminLogin(email.trim(), password);
      if (onLoginSuccess) {
        onLoginSuccess(agent);
      }
      navigate('/console');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.userMessage || err.message);
      } else {
        setError('Login failed. Please check your credentials.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <span className="login-badge">Phase 3 Console</span>
          <h2>Support Agent Login</h2>
          <p>Access the unified escalation inbox and case management workspace.</p>
        </div>

        {error && (
          <div className="login-error-alert" role="alert">
            <span>⚠️ {error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="agent-email">Email Address</label>
            <input
              id="agent-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="agent@example.com"
              required
              disabled={loading}
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="agent-password">Password</label>
            <input
              id="agent-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              disabled={loading}
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary login-btn"
            disabled={loading || !email.trim() || !password}
          >
            {loading ? 'Authenticating...' : 'Sign In to Console'}
          </button>
        </form>

        <div className="login-demo-helpers">
          <span className="demo-hint-title">Quick Demo Sign-In:</span>
          <div className="demo-btn-group">
            <button
              type="button"
              className="btn btn-outline-sm"
              onClick={() => handleQuickFill('admin@example.com', 'AdminPass123!')}
            >
              👑 Demo Admin
            </button>
            <button
              type="button"
              className="btn btn-outline-sm"
              onClick={() => handleQuickFill('agent@example.com', 'AgentPass123!')}
            >
              🎧 Demo Agent
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
