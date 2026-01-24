import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../lib/api', () => ({
  apiGet: vi.fn(),
  apiFetchBlob: vi.fn(),
  apiPost: vi.fn(),
}));

import { apiFetchBlob } from '../../lib/api';
import { downloadSystemLog } from '../../services/system';

describe('system log services', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('downloadSystemLog fetches log blob', async () => {
    const blob = new Blob(['log']);
    (apiFetchBlob as any).mockResolvedValue(blob);
    await downloadSystemLog('selenite.log');
    expect(apiFetchBlob).toHaveBeenCalledWith('/system/logs/selenite.log');
  });
});
