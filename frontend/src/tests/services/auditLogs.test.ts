import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../lib/api', () => ({
  apiGet: vi.fn(),
  apiFetchBlob: vi.fn(),
}));

import { apiGet, apiFetchBlob } from '../../lib/api';
import { fetchAuditLogs, downloadAuditLogs } from '../../services/auditLogs';

describe('audit log services', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetchAuditLogs builds query params', async () => {
    (apiGet as any).mockResolvedValue({ total: 0, items: [] });
    await fetchAuditLogs({ action: 'auth.login', limit: 10, offset: 20 });
    expect(apiGet).toHaveBeenCalledWith('/audit-logs?action=auth.login&limit=10&offset=20');
  });

  it('downloadAuditLogs uses authenticated blob fetch', async () => {
    const blob = new Blob(['csv']);
    (apiFetchBlob as any).mockResolvedValue(blob);
    await downloadAuditLogs({ target_type: 'user' });
    expect(apiFetchBlob).toHaveBeenCalledWith('/audit-logs/export?target_type=user');
  });
});
