import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../lib/api', () => ({
  apiGet: vi.fn(),
  apiPut: vi.fn(),
}));

import { apiGet, apiPut } from '../../lib/api';
import { fetchSettings, updateSettings } from '../../services/settings';

describe('settings service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetchSettings retrieves data from /settings', async () => {
    (apiGet as any).mockResolvedValue({});
    await fetchSettings();
    expect(apiGet).toHaveBeenCalledWith('/settings');
  });

  it('updateSettings sends payload via PUT', async () => {
    (apiPut as any).mockResolvedValue({});
    const payload = {
      default_model: 'large',
      default_language: 'en',
      default_diarizer: 'vad',
      diarization_enabled: true,
      allow_job_overrides: true,
      max_concurrent_jobs: 3,
    };
    await updateSettings(payload);
    expect(apiPut).toHaveBeenCalledWith('/settings', payload);
  });
});
