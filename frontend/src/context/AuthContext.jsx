import { createContext, useContext, useEffect, useState } from 'react';
import { authApi } from '../lib/api';
import { AUTH_EXPIRED_EVENT, TOKEN_KEY } from '../lib/config';

const AuthContext = createContext(null);
function expiry(token) {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(payload)).exp * 1000;
  } catch { return 0; }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(token));
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [expired, setExpired] = useState(false);

  const logout = () => {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken(null); setUser(null); setLoading(false); setError('');
  };
  useEffect(() => {
    const onExpired = () => { logout(); setExpired(true); };
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, []);

  useEffect(() => {
    if (!token) return;
    const remaining = expiry(token) - Date.now();
    if (!Number.isFinite(remaining) || remaining <= 0) {
      logout(); setExpired(true); return;
    }
    const timer = setTimeout(() => { logout(); setExpired(true); }, Math.min(remaining, 2147483647));
    const controller = new AbortController();
    setLoading(true); setError('');
    authApi.me(controller.signal).then(setUser).catch((failure) => {
      if (failure.name !== 'AbortError' && failure.status !== 401) setError(failure.message);
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => { clearTimeout(timer); controller.abort(); };
  }, [token, retry]);

  const login = async (credentials) => {
    const data = await authApi.login(credentials);
    if (!data?.access_token || !data?.user) throw new Error('La respuesta de acceso no es válida.');
    sessionStorage.setItem(TOKEN_KEY, data.access_token);
    setExpired(false); setError(''); setUser(data.user); setToken(data.access_token);
  };

  return <AuthContext.Provider value={{ user, token, loading, error, expired, login, logout, retry: () => setRetry((value) => value + 1) }}>{children}</AuthContext.Provider>;
}
export const useAuth = () => useContext(AuthContext);
