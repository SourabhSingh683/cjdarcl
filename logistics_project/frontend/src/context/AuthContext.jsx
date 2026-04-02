/**
 * AuthContext.jsx
 * ===============
 * Global authentication state for CJ Darcl LMS.
 * Provides: user, role, login (username/pw), loginOTP, logout, loading.
 *
 * Wrap your app with <AuthProvider> in main.jsx.
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  authLogin, authOTPRequest, authOTPVerify,
  authMe, authLogout,
} from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);   // { id, username, full_name, role }
  const [loading, setLoading] = useState(true);   // true while verifying token on mount
  const [error, setError]     = useState(null);

  // On mount: try to restore session from stored access token
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) { setLoading(false); return; }
    authMe()
      .then(data => setUser({ ...data, role: data.profile?.role ?? 'unknown' }))
      .catch(() => { localStorage.clear(); setUser(null); })
      .finally(() => setLoading(false));
  }, []);

  /** Username + password login */
  const login = useCallback(async (username, password) => {
    setError(null);
    const data = await authLogin(username, password);
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    setUser(data.user);
    return data.user;
  }, []);

  /** OTP step 1: request OTP for phone number. Returns demo OTP in dev mode. */
  const requestOTP = useCallback(async (phone) => {
    setError(null);
    return authOTPRequest(phone);
  }, []);

  /** OTP step 2: verify OTP, auto-create user, log in */
  const loginOTP = useCallback(async (phone, otp, extras = {}) => {
    setError(null);
    const data = await authOTPVerify(phone, otp, extras);
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    setUser(data.user);
    return data.user;
  }, []);

  /** Logout: clear tokens + reset state */
  const logout = useCallback(() => {
    authLogout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, error, login, requestOTP, loginOTP, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

/** Hook shortcut */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
