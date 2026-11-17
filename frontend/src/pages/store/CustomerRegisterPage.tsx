import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export const CustomerRegisterPage: React.FC = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('9876543210');
  const [password, setPassword] = useState('');
  const [preferredLang, setPreferredLang] = useState('en');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirect = searchParams.get('redirect') || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await register({
        name,
        email,
        phone,
        password,
        preferred_language: preferredLang,
      });
      navigate(redirect);
    } catch (err: any) {
      setErrorMsg(err.userMessage || err.message || 'Registration failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-page-container">
      <div className="auth-card">
        <h2>Create an Account</h2>
        <p className="auth-sub">Join Regional Bazaar for regional products and bilingual support.</p>

        {errorMsg && <div className="auth-error-banner">{errorMsg}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="reg-name">Full Name</label>
            <input
              id="reg-name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Ramesh Kumar"
            />
          </div>

          <div className="form-group">
            <label htmlFor="reg-email">Email Address</label>
            <input
              id="reg-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ramesh@example.com"
            />
          </div>

          <div className="form-group">
            <label htmlFor="reg-phone">Phone Number (10 digits)</label>
            <input
              id="reg-phone"
              type="tel"
              required
              pattern="[0-9]{10}"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="9876543210"
            />
          </div>

          <div className="form-group">
            <label htmlFor="reg-lang">Preferred Language</label>
            <select
              id="reg-lang"
              value={preferredLang}
              onChange={(e) => setPreferredLang(e.target.value)}
            >
              <option value="en">English</option>
              <option value="ta">தமிழ் (Tamil)</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="reg-pass">Password (min 8 characters)</label>
            <input
              id="reg-pass"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          <button type="submit" className="btn-auth-submit" disabled={isSubmitting}>
            {isSubmitting ? 'Creating Account...' : 'Register'}
          </button>
        </form>

        <div className="auth-card-footer">
          <p>
            Already have an account?{' '}
            <Link to={`/login?redirect=${encodeURIComponent(redirect)}`}>Sign in here</Link>
          </p>
        </div>
      </div>
    </div>
  );
};
