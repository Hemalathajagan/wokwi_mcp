import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from './AuthContext';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';

export default function LoginPage() {
  const { login, signupWithEmail, loginWithEmail } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [tab, setTab] = useState('signin'); // 'signin' | 'signup'
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      setError(null);
      await login(credentialResponse.credential);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Login failed');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      if (tab === 'signup') {
        await signupWithEmail(email, name, password);
        setTab('signin');
        setPassword('');
        setSuccess('Account created successfully. Please sign in.');
        return;
      } else {
        await loginWithEmail(email, password);
      }
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Authentication failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Wokwi Circuit Analyzer</h1>
        <p className="login-subtitle">AI-powered Arduino circuit fault detection</p>
        <div className="login-divider" />

        <div className="auth-tabs">
          <button
            className={tab === 'signin' ? 'active' : ''}
            onClick={() => { setTab('signin'); setError(null); setSuccess(null); }}
          >
            Sign In
          </button>
          <button
            className={tab === 'signup' ? 'active' : ''}
            onClick={() => { setTab('signup'); setError(null); setSuccess(null); }}
          >
            Sign Up
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {tab === 'signup' && (
            <input
              type="text"
              placeholder="Full name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          )}
          <input
            type="email"
            placeholder="Email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
          <button type="submit" className="auth-submit-btn" disabled={submitting}>
            {submitting ? 'Please wait...' : tab === 'signup' ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        {success && <p className="login-success">{success}</p>}
        {error && <p className="login-error">{error}</p>}

        <div className="auth-or">
          <span>or</span>
        </div>

        <div className="google-btn-wrapper">
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => setError('Google sign-in failed')}
            size="large"
            theme="outline"
            text="signin_with"
            shape="rectangular"
          />
        </div>
      </div>
    </div>
  );
}
