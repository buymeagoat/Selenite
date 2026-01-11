/**
 * Settings API Service
 * 
 * Functions for managing user settings and preferences.
 */

import { apiFetch, apiPut } from '../lib/api';

export interface UserSettings {
  default_asr_provider: string | null;
  default_model: string;
  default_language: string;
  default_diarizer_provider: string | null;
  default_diarizer: string;
  diarization_enabled: boolean;
  allow_asr_overrides: boolean;
  allow_diarizer_overrides: boolean;
  enable_timestamps: boolean;
  max_concurrent_jobs: number;
  show_all_jobs: boolean;
  time_zone: string | null;
  server_time_zone: string;
  transcode_to_wav: boolean;
  enable_empty_weights: boolean;
  last_selected_asr_set: string | null;
  last_selected_diarizer_set: string | null;
  feedback_store_enabled: boolean;
  feedback_email_enabled: boolean;
  feedback_webhook_enabled: boolean;
  feedback_destination_email: string | null;
  feedback_webhook_url: string | null;
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_username: string | null;
  smtp_from_email: string | null;
  smtp_use_tls: boolean;
  smtp_password_set: boolean;
  session_timeout_minutes: number;
  allow_self_signup: boolean;
  require_signup_verification: boolean;
  require_signup_captcha: boolean;
  signup_captcha_provider: string | null;
  signup_captcha_site_key: string | null;
  password_min_length: number;
  password_require_uppercase: boolean;
  password_require_lowercase: boolean;
  password_require_number: boolean;
  password_require_special: boolean;
}

export interface UpdateSettingsParams {
  default_asr_provider?: string | null;
  default_model?: string | null;
  default_language?: string;
  default_diarizer_provider?: string | null;
  default_diarizer?: string | null;
  diarization_enabled?: boolean;
  allow_asr_overrides?: boolean;
  allow_diarizer_overrides?: boolean;
  enable_timestamps?: boolean;
  max_concurrent_jobs?: number;
  show_all_jobs?: boolean;
  time_zone?: string | null;
  server_time_zone?: string | null;
  transcode_to_wav?: boolean;
  enable_empty_weights?: boolean;
  last_selected_asr_set?: string | null;
  last_selected_diarizer_set?: string | null;
  feedback_store_enabled?: boolean;
  feedback_email_enabled?: boolean;
  feedback_webhook_enabled?: boolean;
  feedback_destination_email?: string | null;
  feedback_webhook_url?: string | null;
  smtp_host?: string | null;
  smtp_port?: number | null;
  smtp_username?: string | null;
  smtp_password?: string | null;
  smtp_from_email?: string | null;
  smtp_use_tls?: boolean;
  session_timeout_minutes?: number;
  allow_self_signup?: boolean;
  require_signup_verification?: boolean;
  require_signup_captcha?: boolean;
  signup_captcha_provider?: string | null;
  signup_captcha_site_key?: string | null;
  password_min_length?: number;
  password_require_uppercase?: boolean;
  password_require_lowercase?: boolean;
  password_require_number?: boolean;
  password_require_special?: boolean;
}

export interface UpdateAsrSettingsParams {
  default_asr_provider?: string | null;
  default_model?: string | null;
  default_language?: string;
  allow_asr_overrides?: boolean;
  enable_timestamps?: boolean;
  max_concurrent_jobs?: number;
  show_all_jobs?: boolean;
  time_zone?: string | null;
  last_selected_asr_set?: string | null;
}

export interface UpdateDiarizationSettingsParams {
  default_diarizer_provider?: string | null;
  default_diarizer?: string | null;
  diarization_enabled?: boolean;
  allow_diarizer_overrides?: boolean;
  show_all_jobs?: boolean;
  time_zone?: string | null;
  last_selected_diarizer_set?: string | null;
}

/**
 * Fetch current user settings
 */
export async function fetchSettings(options?: { signal?: AbortSignal }): Promise<UserSettings> {
  return apiFetch<UserSettings>('/settings', {
    method: 'GET',
    signal: options?.signal,
  });
}

/**
 * Update user settings
 */
export async function updateSettings(params: UpdateSettingsParams): Promise<UserSettings> {
  return apiPut<UserSettings>('/settings', params);
}

export async function updateAsrSettings(params: UpdateAsrSettingsParams): Promise<UserSettings> {
  return apiPut<UserSettings>('/settings/asr', params);
}

export async function updateDiarizationSettings(params: UpdateDiarizationSettingsParams): Promise<UserSettings> {
  return apiPut<UserSettings>('/settings/diarization', params);
}
