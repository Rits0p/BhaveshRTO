import { createContext, useContext, useEffect, useState } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [admin, setAdmin] = useState(null);
  const [initialized, setInitialized] = useState(false);

  const login = (adminData) => {
    setAdmin(adminData);
  };

  const logout = () => {
    setAdmin(null);
  };

  // Session cookies are HttpOnly, so on load we just ask the backend who we
  // are. A 401 here simply means "no valid session" — nothing to restore.
  useEffect(() => {
    const restoreSession = async () => {
      try {
        const meResponse = await api.get('/auth/me');
        setAdmin(meResponse.data.admin);
      } catch {
        setAdmin(null);
      } finally {
        setInitialized(true);
      }
    };

    restoreSession();
  }, []);

  const isAuthenticated = !!admin;

  return (
    <AuthContext.Provider value={{ admin, isAuthenticated, initialized, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
