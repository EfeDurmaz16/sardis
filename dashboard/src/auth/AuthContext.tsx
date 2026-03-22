
import React, { createContext, useContext, useState, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || ''

interface AuthContextType {
  token: string | null;
  isAuthenticated: boolean;
  needsOnboarding: boolean;
  login: (token: string) => void;
  logout: () => void;
  completeOnboarding: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

// Use a module-level variable for the token so the API client can access it
// without needing React context (for use outside components).
let _currentToken: string | null = null;

export function getCurrentToken(): string | null {
  return _currentToken;
}

async function checkNeedsOnboarding(_token: string): Promise<boolean> {
  // Onboarding is opt-in, not blocking. Users can always access the dashboard.
  // The onboarding checklist component shows progress without forcing a redirect.
  if (localStorage.getItem('sardis_onboarding_complete') === 'true') {
    return false;
  }
  // Don't block dashboard access — agents are created during onboarding, not before.
  return false;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Initialize from sessionStorage (tab-scoped, cleared on browser close)
  const [token, setToken] = useState<string | null>(() => {
    const stored = sessionStorage.getItem('sardis_session');
    _currentToken = stored;
    return stored;
  });

  const [needsOnboarding, setNeedsOnboarding] = useState(false);

  const login = useCallback(async (newToken: string) => {
    _currentToken = newToken;
    sessionStorage.setItem('sardis_session', newToken);
    // Clean up any legacy localStorage keys
    localStorage.removeItem('sardis_token');
    localStorage.removeItem('sardis_api_key');
    setToken(newToken);

    const shouldOnboard = await checkNeedsOnboarding(newToken);
    setNeedsOnboarding(shouldOnboard);
  }, []);

  const logout = useCallback(() => {
    _currentToken = null;
    sessionStorage.removeItem('sardis_session');
    localStorage.removeItem('sardis_token');
    localStorage.removeItem('sardis_api_key');
    setToken(null);
    setNeedsOnboarding(false);
  }, []);

  const completeOnboarding = useCallback(() => {
    localStorage.setItem('sardis_onboarding_complete', 'true');
    setNeedsOnboarding(false);
  }, []);

  return (
    <AuthContext.Provider value={{ token, isAuthenticated: !!token, needsOnboarding, login, logout, completeOnboarding }}>
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
