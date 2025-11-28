/**
 * Settings API Service
 * 
 * Functions for managing user settings and preferences.
 */

import { apiFetch, apiPut } from '../lib/api';

export interface UserSettings {
  default_model: string;
  default_language: string;
  default_diarizer: string;
  diarization_enabled: boolean;
  allow_job_overrides: boolean;
  enable_timestamps: boolean;
  max_concurrent_jobs: number;
}

export interface UpdateSettingsParams {
  default_model: string;
  default_language: string;
  default_diarizer: string;
  diarization_enabled: boolean;
  allow_job_overrides: boolean;
  enable_timestamps: boolean;
  max_concurrent_jobs: number;
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
