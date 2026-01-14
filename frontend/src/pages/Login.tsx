import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { apiPost, ApiError } from '../lib/api';
import { devInfo, devError } from '../lib/debug';
import type { AuthTokenResponse, SignupConfigResponse } from '../services/auth';
import { fetchSignupConfig } from '../services/auth';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [errorDetails, setErrorDetails] = useState<any>(null);
  const [httpsRequiredUrl, setHttpsRequiredUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [signupConfig, setSignupConfig] = useState<SignupConfigResponse | null>(null);
  const [isSignupLoading, setIsSignupLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setErrorDetails(null);
    setHttpsRequiredUrl(null);
    setIsLoading(true);

    devInfo('[LOGIN ATTEMPT]', {
      email,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent
    });

    try {
      const data = await apiPost<AuthTokenResponse>('/auth/login', {
        email,
        password
      });

      devInfo('[LOGIN SUCCESS]', { email, hasToken: !!data.access_token });
      login(data.access_token, data.user);
      navigate('/');
    } catch (err) {
      devError('[LOGIN FAILED]', err);
      if (err instanceof ApiError) {
        if (err.status === 426 && typeof err.data?.detail === 'string') {
          const upgradeUrl = typeof err.data?.upgrade_url === 'string'
            ? err.data.upgrade_url
            : `https://${window.location.host}`;
          setHttpsRequiredUrl(upgradeUrl);
          setError('HTTPS is required to sign in.');
        } else {
          setError(err.message);
        }
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

  React.useEffect(() => {
    let cancelled = false;
    const loadConfig = async () => {
      setIsSignupLoading(true);
      try {
        const config = await fetchSignupConfig();
        if (!cancelled) {
          setSignupConfig(config);
        }
      } catch (err) {
        devError('[SIGNUP CONFIG FAILED]', err);
      } finally {
        if (!cancelled) {
          setIsSignupLoading(false);
        }
      }
    };
    loadConfig();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-sage-light">
      <form onSubmit={handleSubmit} className="bg-white shadow rounded p-6 w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-semibold text-pine-deep">Selenite Login</h1>
        {httpsRequiredUrl && (
          <div className="bg-amber-50 border border-amber-200 text-amber-800 px-3 py-2 rounded text-sm">
            <div className="font-semibold">HTTPS required</div>
            <div>
              Open the secure URL to continue:{' '}
              <a className="underline" href={httpsRequiredUrl}>
                {httpsRequiredUrl}
              </a>
            </div>
          </div>
        )}
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
          <label className="text-sm font-medium text-pine-mid" htmlFor="email">Email</label>
          <input
            id="email"
            className="border rounded px-3 py-2 w-full"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
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
          disabled={!email || !password || isLoading}
          className="w-full bg-forest-green text-white py-2 rounded disabled:opacity-50"
        >
          {isLoading ? 'Logging in...' : 'Login'}
        </button>
        {signupConfig?.allow_self_signup && (
          <button
            type="button"
            onClick={() => navigate('/signup')}
            className="w-full text-sm text-pine-mid underline"
            disabled={isSignupLoading}
          >
            Create an account
          </button>
        )}
      </form>
    </div>
  );
};
