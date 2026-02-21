import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import * as SecureStore from 'expo-secure-store';
import { sardisApi } from '../api/sardisApi';

interface AuthContextType {
  apiKey: string | null;
  baseUrl: string;
  isAuthenticated: boolean;
  isLoading: boolean;
  signIn: (apiKey: string, baseUrl?: string) => Promise<void>;
  signOut: () => Promise<void>;
  updateBaseUrl: (url: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_KEY_STORAGE_KEY = 'sardis_api_key';
const BASE_URL_STORAGE_KEY = 'sardis_base_url';
const DEFAULT_BASE_URL = 'https://api.sardis.sh/api/v2';

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [baseUrl, setBaseUrl] = useState<string>(DEFAULT_BASE_URL);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadStoredCredentials();
  }, []);

  const loadStoredCredentials = async () => {
    try {
      const [storedApiKey, storedBaseUrl] = await Promise.all([
        SecureStore.getItemAsync(API_KEY_STORAGE_KEY),
        SecureStore.getItemAsync(BASE_URL_STORAGE_KEY),
      ]);

      if (storedApiKey) {
        setApiKey(storedApiKey);
        const url = storedBaseUrl || DEFAULT_BASE_URL;
        setBaseUrl(url);
        sardisApi.configure({ apiKey: storedApiKey, baseUrl: url });
      }
    } catch (error) {
      console.error('Failed to load stored credentials:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const signIn = async (newApiKey: string, newBaseUrl?: string) => {
    try {
      const url = newBaseUrl || DEFAULT_BASE_URL;

      // Test the credentials
      sardisApi.configure({ apiKey: newApiKey, baseUrl: url });
      await sardisApi.getQuickStats(); // Simple API call to verify credentials

      // Store if successful
      await Promise.all([
        SecureStore.setItemAsync(API_KEY_STORAGE_KEY, newApiKey),
        SecureStore.setItemAsync(BASE_URL_STORAGE_KEY, url),
      ]);

      setApiKey(newApiKey);
      setBaseUrl(url);
    } catch (error) {
      console.error('Sign in failed:', error);
      throw new Error('Invalid API key or server URL');
    }
  };

  const signOut = async () => {
    try {
      await Promise.all([
        SecureStore.deleteItemAsync(API_KEY_STORAGE_KEY),
        SecureStore.deleteItemAsync(BASE_URL_STORAGE_KEY),
      ]);

      setApiKey(null);
      setBaseUrl(DEFAULT_BASE_URL);
    } catch (error) {
      console.error('Sign out failed:', error);
    }
  };

  const updateBaseUrl = async (newUrl: string) => {
    try {
      if (apiKey) {
        // Test the new URL
        sardisApi.configure({ apiKey, baseUrl: newUrl });
        await sardisApi.getQuickStats();

        await SecureStore.setItemAsync(BASE_URL_STORAGE_KEY, newUrl);
        setBaseUrl(newUrl);
      }
    } catch (error) {
      console.error('Base URL update failed:', error);
      throw new Error('Invalid server URL');
    }
  };

  const value: AuthContextType = {
    apiKey,
    baseUrl,
    isAuthenticated: !!apiKey,
    isLoading,
    signIn,
    signOut,
    updateBaseUrl,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
