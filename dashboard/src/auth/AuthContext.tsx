
import React, { createContext, useContext, useState, useCallback } from 'react';

interface AuthContextType {
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

// Use a module-level variable for the token so the API client can access it
// without needing React context (for use outside components).
let _currentToken: string | null = null;

export function getCurrentToken(): string | null {
  return _currentToken;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Initialize from sessionStorage (tab-scoped, cleared on browser close)
  const [token, setToken] = useState<string | null>(() => {
    const stored = sessionStorage.getItem('sardis_session');
    _currentToken = stored;
    return stored;
  });

  const login = useCallback((newToken: string) => {
    _currentToken = newToken;
    sessionStorage.setItem('sardis_session', newToken);
    // Clean up any legacy localStorage keys
    localStorage.removeItem('sardis_token');
    localStorage.removeItem('sardis_api_key');
    setToken(newToken);
  }, []);

  const logout = useCallback(() => {
    _currentToken = null;
    sessionStorage.removeItem('sardis_session');
    localStorage.removeItem('sardis_token');
    localStorage.removeItem('sardis_api_key');
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, isAuthenticated: !!token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
