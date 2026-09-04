import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { ensureCsrf, getMe, login as apiLogin, logout as apiLogout } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    ensureCsrf()
      .then(() => getMe())
      .then((res) => setUser(res.data))
      .catch(() => setUser(null));
  }, []);

  const login = useCallback(async (username, password) => {
    await ensureCsrf();
    const res = await apiLogin({ username, password });
    setUser(res.data);
    return res.data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      /* still clear local session */
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout, ready: user !== undefined }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
