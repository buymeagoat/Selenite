/**
 * Settings API Service
 * 
 * Functions for managing user settings and preferences.
 */

import { apiGet, apiPut } from '../lib/api';

export interface UserSettings {
  default_model: string;
  default_language: string;
  max_concurrent_jobs: number;
}

export interface UpdateSettingsParams {
  default_model: string;
  default_language: string;
  max_concurrent_jobs: number;
}

/**
 * Fetch current user settings
 */
export async function fetchSettings(): Promise<UserSettings> {
  return apiGet<UserSettings>('/settings');
}

/**
 * Update user settings
 */
export async function updateSettings(params: UpdateSettingsParams): Promise<UserSettings> {
  return apiPut<UserSettings>('/settings', params);
}
