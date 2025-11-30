import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { apiPost, ApiError } from '../lib/api';
import { devInfo, devError } from '../lib/debug';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [errorDetails, setErrorDetails] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setErrorDetails(null);
    setIsLoading(true);

    devInfo('[LOGIN ATTEMPT]', {
      username,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent
    });

    try {
      const data = await apiPost<{ access_token: string; token_type: string; email?: string }>('/auth/login', {
        username,
        password
      });

      devInfo('[LOGIN SUCCESS]', { username, hasToken: !!data.access_token });
      login(data.access_token, { username, email: data.email || `${username}@example.com` });
      navigate('/');
    } catch (err) {
      devError('[LOGIN FAILED]', err);
      if (err instanceof ApiError) {
        setError(err.message);
        setErrorDetails({
          status: err.status,
          data: err.data,
          timestamp: new Date().toISOString()
        });
      } else if (err instanceof Error) {
        setError(err.message);
        setErrorDetails({
          name: err.name,
          message: err.message,
          timestamp: new Date().toISOString()
        });
      } else {
        setError('Login failed');
        setErrorDetails({ error: String(err), timestamp: new Date().toISOString() });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-sage-light">
      <form onSubmit={handleSubmit} className="bg-white shadow rounded p-6 w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-semibold text-pine-deep">Selenite Login</h1>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
            <div className="font-semibold">{error}</div>
            {errorDetails && (
              <details className="mt-2 text-xs">
                <summary className="cursor-pointer underline">Technical Details</summary>
                <pre className="mt-1 p-2 bg-red-100 rounded overflow-x-auto">
                  {JSON.stringify(errorDetails, null, 2)}
                </pre>
              </details>
            )}
          </div>
        )}
        <div className="space-y-1">
          <label className="text-sm font-medium text-pine-mid" htmlFor="username">Username</label>
          <input
            id="username"
            className="border rounded px-3 py-2 w-full"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter username"
            autoComplete="username"
            disabled={isLoading}
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium text-pine-mid" htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            className="border rounded px-3 py-2 w-full"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
            autoComplete="current-password"
            disabled={isLoading}
          />
        </div>
        <button
          type="submit"
          disabled={!username || !password || isLoading}
          className="w-full bg-forest-green text-white py-2 rounded disabled:opacity-50"
        >
          {isLoading ? 'Logging in...' : 'Login'}
        </button>
      </form>
    </div>
  );
};
