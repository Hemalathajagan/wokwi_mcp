import { useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { changePassword } from '../api';

export default function ProfilePage() {
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setMessage(null);
    setError(null);

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }
    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters');
      return;
    }

    setSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      setMessage('Password changed successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to change password');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="profile-page">
      <div className="profile-card">
        <h2>Profile</h2>
        <div className="profile-info">
          {user.picture && (
            <img src={user.picture} alt={user.name} className="profile-avatar" referrerPolicy="no-referrer" />
          )}
          <div className="profile-details">
            <p className="profile-name">{user.name}</p>
            <p className="profile-email">{user.email}</p>
            {user.created_at && (
              <p className="profile-member-since">
                Member since {new Date(user.created_at).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="profile-card">
        <h2>Change Password</h2>
        <form className="password-form" onSubmit={handleChangePassword}>
          <input
            type="password"
            placeholder="Current password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="New password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={6}
          />
          <input
            type="password"
            placeholder="Confirm new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            minLength={6}
          />
          <button type="submit" className="auth-submit-btn" disabled={submitting}>
            {submitting ? 'Changing...' : 'Change Password'}
          </button>
        </form>
        {message && <p className="profile-success">{message}</p>}
        {error && <p className="login-error">{error}</p>}
      </div>
    </div>
  );
}
