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
  allow_job_overrides: boolean;
  enable_timestamps: boolean;
  max_concurrent_jobs: number;
  time_zone: string | null;
  server_time_zone: string;
   transcode_to_wav: boolean;
  last_selected_asr_set: string | null;
  last_selected_diarizer_set: string | null;
}

export interface UpdateSettingsParams {
  default_asr_provider?: string | null;
  default_model?: string | null;
  default_language?: string;
  default_diarizer_provider?: string | null;
  default_diarizer?: string | null;
  diarization_enabled?: boolean;
  allow_job_overrides?: boolean;
  enable_timestamps?: boolean;
  max_concurrent_jobs?: number;
  time_zone?: string | null;
  server_time_zone?: string | null;
  transcode_to_wav?: boolean;
  last_selected_asr_set?: string | null;
  last_selected_diarizer_set?: string | null;
}

export interface UpdateAsrSettingsParams {
  default_asr_provider?: string | null;
  default_model?: string | null;
  default_language?: string;
  allow_job_overrides?: boolean;
  enable_timestamps?: boolean;
  max_concurrent_jobs?: number;
  time_zone?: string | null;
  last_selected_asr_set?: string | null;
}

export interface UpdateDiarizationSettingsParams {
  default_diarizer_provider?: string | null;
  default_diarizer?: string | null;
  diarization_enabled?: boolean;
  allow_job_overrides?: boolean;
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
