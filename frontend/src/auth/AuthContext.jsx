import { createContext, useContext, useState, useEffect } from 'react';
import { googleLogin as apiGoogleLogin, signup as apiSignup, emailLogin as apiEmailLogin, getCurrentUser } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // On mount, check if we have tokens and load user
    const accessToken = localStorage.getItem('access_token');
    if (accessToken) {
      getCurrentUser()
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const storeTokensAndLoadUser = async (data) => {
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    const me = await getCurrentUser();
    setUser(me);
  };

  const login = async (googleToken) => {
    const data = await apiGoogleLogin(googleToken);
    await storeTokensAndLoadUser(data);
  };

  const signupWithEmail = async (email, name, password) => {
    await apiSignup(email, name, password);
    // Don't auto-login — user will be redirected to sign-in tab
  };

  const loginWithEmail = async (email, password) => {
    const data = await apiEmailLogin(email, password);
    await storeTokensAndLoadUser(data);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signupWithEmail, loginWithEmail, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
