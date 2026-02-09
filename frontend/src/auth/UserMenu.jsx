import { useAuth } from './AuthContext';
import { Link } from 'react-router-dom';

export default function UserMenu() {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <div className="user-menu">
      {user.picture && (
        <img src={user.picture} alt={user.name} className="user-avatar" referrerPolicy="no-referrer" />
      )}
      <Link to="/" className="user-menu-link">Dashboard</Link>
      <Link to="/history" className="user-menu-link">History</Link>
      <Link to="/profile" className="user-name-link">{user.name}</Link>
      <button className="sign-out-btn" onClick={logout}>
        Sign out
      </button>
    </div>
  );
}
