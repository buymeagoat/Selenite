import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../lib/api', () => ({
  apiGet: vi.fn(),
}));

import { apiGet } from '../../lib/api';
import { fetchTranscript } from '../../services/transcripts';

describe('transcript service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetchTranscript calls /transcripts/:jobId', async () => {
    (apiGet as any).mockResolvedValue({});
    await fetchTranscript('job-123');
    expect(apiGet).toHaveBeenCalledWith('/transcripts/job-123');
  });
});
