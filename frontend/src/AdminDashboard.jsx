
import { useEffect, useState } from 'react';
import {
  getAdminHostels,
  createHostel,
  updateHostel,
  updateHostelUsername,
  resetHostelPassword,
  deleteHostel,
} from './services/api';

export default function AdminDashboard() {
  const [hostels, setHostels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const [newHostel, setNewHostel] = useState({
    hostel_name: '',
    username: '',
    password: '',
  });

  const [passwords, setPasswords] = useState({});

  const loadHostels = async () => {
    setError('');
    try {
      const data = await getAdminHostels();
      setHostels(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load hostel accounts.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHostels();
  }, []);

  const handleCreate = async (event) => {
    event.preventDefault();
    setError('');
    setMessage('');

    try {
      await createHostel(newHostel);
      setNewHostel({ hostel_name: '', username: '', password: '' });
      setMessage('Hostel account created successfully.');
      await loadHostels();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create hostel account.');
    }
  };

  const handleUpdate = async (hostel) => {
    const name = window.prompt('Enter hostel name:', hostel.hostel_name);
    if (name === null) return;

    if (name.trim().length < 2) {
      setError('Hostel name must contain at least 2 characters.');
      return;
    }

    setError('');
    setMessage('');

    try {
      await updateHostel(hostel.id, {
        hostel_name: name.trim(),
        is_active: hostel.is_active,
      });
      setMessage('Hostel details updated.');
      await loadHostels();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not update hostel.');
    }
  };

  const handleUsernameUpdate = async (hostel) => {
    const username = window.prompt(
      `Enter the new login username for ${hostel.hostel_name}:`,
      hostel.username
    );

    if (username === null) return;

    const cleanedUsername = username.trim();

    if (!/^[A-Za-z0-9_-]{3,50}$/.test(cleanedUsername)) {
      setError(
        'Username must be 3–50 characters and contain only letters, numbers, underscores or hyphens.'
      );
      return;
    }

    setError('');
    setMessage('');

    try {
      await updateHostelUsername(hostel.id, cleanedUsername);
      setMessage('Hostel login username updated. The previous login session has been invalidated.');
      await loadHostels();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not update username.');
    }
  };

  const handleToggle = async (hostel) => {
    setError('');
    setMessage('');

    try {
      await updateHostel(hostel.id, {
        hostel_name: hostel.hostel_name,
        is_active: !hostel.is_active,
      });
      setMessage(
        hostel.is_active
          ? 'Hostel account deactivated.'
          : 'Hostel account activated.'
      );
      await loadHostels();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not change account status.');
    }
  };

  const handlePasswordReset = async (hostelId) => {
    const newPassword = passwords[hostelId] || '';

    if (newPassword.length < 6) {
      setError('New password must contain at least 6 characters.');
      return;
    }

    setError('');
    setMessage('');

    try {
      await resetHostelPassword(hostelId, newPassword);
      setPasswords((previous) => ({ ...previous, [hostelId]: '' }));
      setMessage('Hostel password reset successfully. Existing login sessions have been invalidated.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not reset password.');
    }
  };

  const handleDelete = async (hostel) => {
    const confirmed = window.confirm(
      `Delete the account for "${hostel.hostel_name}" (ID: ${hostel.id})?\n\nThis action cannot be undone. Hostels containing rooms or monitoring data, and the initial hostel, are protected.`
    );

    if (!confirmed) return;

    setError('');
    setMessage('');

    try {
      await deleteHostel(hostel.id);
      setMessage('Hostel account deleted successfully.');
      await loadHostels();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not delete hostel account.');
    }
  };

  return (
    <main className="admin-page">
      <header className="admin-heading">
        <div>
          <p className="auth-eyebrow">AQUAGUARD MANAGEMENT</p>
          <h1>Admin Dashboard</h1>
          <p>Manage hostel accounts and their access to AquaGuard.</p>
        </div>
        <div className="admin-count">
          <strong>{hostels.length}</strong>
          <span>Registered hostels</span>
        </div>
      </header>

      {error && <div className="auth-error admin-notice">{error}</div>}
      {message && <div className="admin-success admin-notice">{message}</div>}

      <section className="admin-panel">
        <h2>Create Hostel Account</h2>
        <p className="admin-muted">
          Create a separate login for each hostel warden.
        </p>

        <form className="admin-create-form" onSubmit={handleCreate}>
          <label>
            Hostel name
            <input
              value={newHostel.hostel_name}
              onChange={(e) =>
                setNewHostel({ ...newHostel, hostel_name: e.target.value })
              }
              placeholder="e.g. Bamashah Hostel"
              required
            />
          </label>

          <label>
            Warden username
            <input
              value={newHostel.username}
              onChange={(e) =>
                setNewHostel({ ...newHostel, username: e.target.value })
              }
              placeholder="e.g. bamashah"
              minLength={3}
              required
            />
          </label>

          <label>
            Initial password
            <input
              type="password"
              value={newHostel.password}
              onChange={(e) =>
                setNewHostel({ ...newHostel, password: e.target.value })
              }
              placeholder="Minimum 6 characters"
              minLength={6}
              required
            />
          </label>

          <button className="button button-primary" type="submit">
            Create account
          </button>
        </form>
      </section>

      <section className="admin-panel">
        <div className="admin-list-heading">
          <div>
            <h2>Hostel Accounts</h2>
            <p className="admin-muted">
              View and manage existing hostel access.
            </p>
          </div>
          <button
            className="button button-light"
            type="button"
            onClick={loadHostels}
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <p>Loading hostel accounts...</p>
        ) : hostels.length === 0 ? (
          <p>No hostel accounts found.</p>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Hostel</th>
                  <th>Username</th>
                  <th>Status</th>
                  <th>Account actions</th>
                </tr>
              </thead>
              <tbody>
                {hostels.map((hostel) => (
                  <tr key={hostel.id}>
                    <td>
                      <strong>{hostel.hostel_name}</strong>
                      <small>ID: {hostel.id}</small>
                    </td>
                    <td>{hostel.username || 'Not configured'}</td>
                    <td>
                      <span
                        className={
                          hostel.is_active
                            ? 'admin-status active'
                            : 'admin-status inactive'
                        }
                      >
                        {hostel.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <div className="admin-actions">
                        <button
                          className="button button-light"
                          type="button"
                          onClick={() => handleUpdate(hostel)}
                        >
                          Edit name
                        </button>

                        <button
                          className="button button-light"
                          type="button"
                          onClick={() => handleUsernameUpdate(hostel)}
                        >
                          Edit Username
                        </button>

                        <button
                          className="button button-light"
                          type="button"
                          onClick={() => handleToggle(hostel)}
                        >
                          {hostel.is_active ? 'Deactivate' : 'Activate'}
                        </button>

                        <div className="admin-reset">
                          <input
                            type="password"
                            placeholder="New password"
                            minLength={6}
                            value={passwords[hostel.id] || ''}
                            onChange={(e) =>
                              setPasswords((previous) => ({
                                ...previous,
                                [hostel.id]: e.target.value,
                              }))
                            }
                          />
                          <button
                            className="button button-primary"
                            type="button"
                            onClick={() => handlePasswordReset(hostel.id)}
                          >
                            Reset
                          </button>
                          <button
                            className="button button-light"
                            type="button"
                            onClick={() => handleDelete(hostel)}
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
