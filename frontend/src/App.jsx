
import { useState } from 'react';
import Dashboard from './Dashboard';
import {
  login,
  logout,
  getAuthToken,
} from './services/api';
import AdminDashboard from './AdminDashboard';
import './App.css';

const USER_KEY = 'aquaguard_user';

function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      const user = await login(username.trim(), password);
      sessionStorage.setItem(USER_KEY, JSON.stringify(user));
      onLogin(user);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Unable to log in. Please check your credentials.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand-mark">A</div>
        <p className="auth-eyebrow">SMART HOSTEL WATER MONITORING</p>
        <h1>Welcome to AquaGuard</h1>
        <p className="auth-description">
          Sign in to access your hostel water monitoring dashboard.
        </p>

        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            Username / Hostel ID
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              autoComplete="username"
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              autoComplete="current-password"
              required
            />
          </label>

          {error && <div className="auth-error">{error}</div>}

          <button
            type="submit"
            className="button button-primary auth-submit"
            disabled={loading}
          >
            {loading ? 'Signing in...' : 'Sign in securely'}
          </button>
        </form>

        <div className="auth-footer">
          <span className="live-dot" />
          Secure AquaGuard monitoring portal
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(() => {
    if (!getAuthToken()) return null;

    try {
      return JSON.parse(sessionStorage.getItem(USER_KEY));
    } catch {
      return null;
    }
  });

  const handleLogout = () => {
    logout();
    sessionStorage.removeItem(USER_KEY);
    setUser(null);
  };

  if (!user) {
    return <LoginPage onLogin={setUser} />;
  }

  return (
    <>
      <div className="account-bar">
        <div>
          <strong>{user.role === 'admin' ? 'Administrator' : user.hostel_name}</strong>
          <span>{user.username}</span>
        </div>
        <button
          type="button"
          className="button button-light"
          onClick={handleLogout}
        >
          Sign out
        </button>
      </div>

      {user.role === 'admin' ? (
        <AdminDashboard onLogout={handleLogout} />
      ) : (
        <Dashboard />
      )}
    </>
  );
}
