/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { fetchCurrentUser, type CurrentUserResponse } from '../services/auth';
import { devError } from '../lib/debug';

type User = CurrentUserResponse;

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string, bootstrapUser?: User) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const persistUser = useCallback((nextUser: User | null) => {
    if (nextUser) {
      localStorage.setItem('auth_user', JSON.stringify(nextUser));
    } else {
      localStorage.removeItem('auth_user');
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    // Clear from localStorage
    localStorage.removeItem('auth_token');
    persistUser(null);
  }, [persistUser]);

  const refreshUserProfile = useCallback(async () => {
    if (!localStorage.getItem('auth_token')) {
      return;
    }
    try {
      const latest = await fetchCurrentUser();
      setUser(latest);
      persistUser(latest);
    } catch (error) {
      devError('Failed to refresh user profile', error);
      logout();
    }
  }, [logout, persistUser]);

  const login = useCallback((newToken: string, bootstrapUser?: User) => {
    setToken(newToken);
    localStorage.setItem('auth_token', newToken);
    if (bootstrapUser) {
      setUser(bootstrapUser);
      persistUser(bootstrapUser);
      return;
    }
    void refreshUserProfile();
  }, [persistUser, refreshUserProfile]);

  // Restore from localStorage on mount
  useEffect(() => {
    let isMounted = true;
    const bootstrapAuth = async () => {
      const storedToken = localStorage.getItem('auth_token');
      const storedUser = localStorage.getItem('auth_user');

      if (storedToken) {
        setToken(storedToken);
      }

      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
        } catch {
          persistUser(null);
        }
      }

      if (storedToken) {
        try {
          await refreshUserProfile();
        } finally {
          if (isMounted) {
            setIsLoading(false);
          }
        }
      } else {
        setIsLoading(false);
      }
    };

    void bootstrapAuth();
    return () => {
      isMounted = false;
    };
  }, [persistUser, refreshUserProfile]);

  useEffect(() => {
    if (!token || typeof window === 'undefined') {
      return;
    }
    const intervalId = window.setInterval(() => {
      void refreshUserProfile();
    }, 60_000);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [token, refreshUserProfile]);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout, refreshUser: refreshUserProfile }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
