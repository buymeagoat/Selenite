import { apiGet, apiPost } from '../lib/api';

export interface CurrentUserResponse {
  id: number;
  username: string;
  email?: string | null;
  is_admin: boolean;
  is_disabled: boolean;
  force_password_reset: boolean;
  is_email_verified: boolean;
  last_login_at?: string | null;
  created_at: string;
}

export const fetchCurrentUser = async () => apiGet<CurrentUserResponse>('/auth/me');

export const resetSessions = async () => apiPost<void>('/auth/reset-sessions');

export interface PasswordPolicy {
  min_length: number;
  require_uppercase: boolean;
  require_lowercase: boolean;
  require_number: boolean;
  require_special: boolean;
}

export interface SignupConfigResponse {
  allow_self_signup: boolean;
  require_email_verification: boolean;
  require_signup_captcha: boolean;
  signup_captcha_provider?: string | null;
  signup_captcha_site_key?: string | null;
  password_policy: PasswordPolicy;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: CurrentUserResponse;
}

export interface SignupRequest {
  username: string;
  email: string;
  password: string;
  captcha_token?: string | null;
}

export const fetchSignupConfig = async () => apiGet<SignupConfigResponse>('/auth/signup/config');

export const signup = async (payload: SignupRequest) => apiPost<AuthTokenResponse>('/auth/signup', payload);
