import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ApiError } from '../lib/api';
import { devError, devInfo } from '../lib/debug';
import { useAuth } from '../context/AuthContext';
import { signup, fetchSignupConfig, type SignupConfigResponse } from '../services/auth';
import { TurnstileWidget } from '../components/auth/TurnstileWidget';

export const Signup: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [config, setConfig] = useState<SignupConfigResponse | null>(null);
  const [isLoadingConfig, setIsLoadingConfig] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [captchaToken, setCaptchaToken] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [detail, setDetail] = useState<any>(null);

  useEffect(() => {
    let cancelled = false;
    const loadConfig = async () => {
      setIsLoadingConfig(true);
      try {
        const data = await fetchSignupConfig();
        if (!cancelled) {
          setConfig(data);
        }
      } catch (err) {
        devError('[SIGNUP CONFIG]', err);
        if (!cancelled) {
          setError('Unable to load signup configuration.');
        }
      } finally {
        if (!cancelled) {
          setIsLoadingConfig(false);
        }
      }
    };
    loadConfig();
    return () => {
      cancelled = true;
    };
  }, []);

  const passwordPolicy = useMemo(() => config?.password_policy, [config]);
  const captchaBlocked = useMemo(() => {
    if (!config) return false;
    if (!config.require_signup_captcha) return false;
    return config.signup_captcha_provider === 'turnstile' && !config.signup_captcha_site_key;
  }, [config]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setDetail(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (!config?.allow_self_signup) {
      setError('Self-service signup is disabled.');
      return;
    }
    if (config.require_signup_captcha && !captchaToken) {
      setError('Complete the CAPTCHA to continue.');
      return;
    }

    setIsSubmitting(true);
    devInfo('[SIGNUP ATTEMPT]', { email, username, timestamp: new Date().toISOString() });
    try {
      const result = await signup({
        username,
        email,
        password,
        captcha_token: captchaToken || undefined,
      });
      login(result.access_token, result.user);
      navigate('/');
    } catch (err) {
      devError('[SIGNUP FAILED]', err);
      if (err instanceof ApiError) {
        setError(err.message);
        setDetail({ status: err.status, data: err.data });
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Signup failed. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const passwordHints = useMemo(() => {
    if (!passwordPolicy) return [] as string[];
    const hints: string[] = [`At least ${passwordPolicy.min_length} characters`];
    if (passwordPolicy.require_uppercase) hints.push('At least one uppercase letter');
    if (passwordPolicy.require_lowercase) hints.push('At least one lowercase letter');
    if (passwordPolicy.require_number) hints.push('At least one number');
    if (passwordPolicy.require_special) hints.push('At least one special character');
    return hints;
  }, [passwordPolicy]);

  const canSubmit = Boolean(
    username.trim() &&
    email.trim() &&
    password &&
    confirmPassword &&
    !isSubmitting &&
    config?.allow_self_signup &&
    !captchaBlocked
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-sage-light px-4 py-8">
      <form onSubmit={handleSubmit} className="bg-white shadow rounded p-6 w-full max-w-md space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-pine-deep">Create your account</h1>
            <p className="text-sm text-pine-mid">Sign up to start using Selenite.</p>
          </div>
          <Link to="/login" className="text-sm text-forest-green underline">Back to login</Link>
        </div>

        {isLoadingConfig && (
          <div className="text-sm text-pine-mid">Loading signup settings...</div>
        )}

        {!isLoadingConfig && config && !config.allow_self_signup && (
          <div className="bg-amber-50 border border-amber-200 text-amber-800 px-3 py-2 rounded text-sm">
            Signups are disabled by the administrator.
          </div>
        )}

        {captchaBlocked && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
            Signup CAPTCHA is required but not configured. Contact an administrator.
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
            <div className="font-semibold">{error}</div>
            {detail && (
              <details className="mt-2 text-xs">
                <summary className="cursor-pointer underline">Details</summary>
                <pre className="mt-1 p-2 bg-red-100 rounded overflow-x-auto">{JSON.stringify(detail, null, 2)}</pre>
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
            placeholder="username"
            autoComplete="username"
            disabled={!config?.allow_self_signup || isSubmitting}
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium text-pine-mid" htmlFor="email">Email</label>
          <input
            id="email"
            className="border rounded px-3 py-2 w-full"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            autoComplete="email"
            disabled={!config?.allow_self_signup || isSubmitting}
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
            placeholder="Choose a password"
            autoComplete="new-password"
            disabled={!config?.allow_self_signup || isSubmitting}
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium text-pine-mid" htmlFor="confirm-password">Confirm Password</label>
          <input
            id="confirm-password"
            type="password"
            className="border rounded px-3 py-2 w-full"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Re-enter password"
            autoComplete="new-password"
            disabled={!config?.allow_self_signup || isSubmitting}
          />
        </div>

        {passwordHints.length > 0 && (
          <div className="bg-sage-light border border-sage-mid rounded px-3 py-2 text-xs text-pine-deep">
            <div className="font-semibold mb-1">Password requirements</div>
            <ul className="list-disc list-inside space-y-0.5">
              {passwordHints.map((hint) => (
                <li key={hint}>{hint}</li>
              ))}
            </ul>
          </div>
        )}

        {config?.require_signup_captcha && config.signup_captcha_provider === 'turnstile' && config.signup_captcha_site_key && (
          <div className="space-y-2">
            <TurnstileWidget
              siteKey={config.signup_captcha_site_key}
              onToken={(token) => setCaptchaToken(token)}
              onError={(message) => setError(message)}
            />
          </div>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="w-full bg-forest-green text-white py-2 rounded disabled:opacity-50"
        >
          {isSubmitting ? 'Creating account...' : 'Sign up'}
        </button>

        {config?.require_email_verification && (
          <p className="text-xs text-pine-mid text-center">
            Email verification will be required before full access.
          </p>
        )}
      </form>
    </div>
  );
};
