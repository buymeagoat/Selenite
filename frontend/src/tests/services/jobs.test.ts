import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../lib/api', () => ({
  apiGet: vi.fn(),
  apiUpload: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
}));

import { apiGet, apiUpload, apiPost, apiDelete } from '../../lib/api';
import {
  fetchJobs,
  fetchJob,
  createJob,
  restartJob,
  cancelJob,
  deleteJob,
  assignTag,
  removeTag,
} from '../../services/jobs';

describe('job services', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetchJobs forwards filters', async () => {
    (apiGet as any).mockResolvedValue({ items: [] });
    await fetchJobs({ status: 'queued', limit: 5 });
    expect(apiGet).toHaveBeenCalledWith('/jobs', { status: 'queued', limit: 5 });
  });

  it('fetchJob hits the job endpoint', async () => {
    (apiGet as any).mockResolvedValue({ id: 'abc' });
    await fetchJob('abc');
    expect(apiGet).toHaveBeenCalledWith('/jobs/abc');
  });

  it('createJob builds a multipart payload', async () => {
    (apiUpload as any).mockResolvedValue({ id: 'abc' });
    const file = new File(['content'], 'audio.wav', { type: 'audio/wav' });

    await createJob({
      file,
      model: 'large',
      language: 'en',
      enable_timestamps: true,
      enable_speaker_detection: false,
      diarizer: 'vad',
    });

    expect(apiUpload).toHaveBeenCalledWith('/jobs', expect.any(FormData));
    const formData = (apiUpload as any).mock.calls[0][1] as FormData;
    const entries = Array.from(formData.entries());
    expect(entries).toContainEqual(['model', 'large']);
    expect(entries).toContainEqual(['language', 'en']);
    expect(entries).toContainEqual(['enable_timestamps', 'true']);
    expect(entries).toContainEqual(['enable_speaker_detection', 'false']);
    expect(entries).toContainEqual(['diarizer', 'vad']);
    const fileEntry = entries.find(([key]) => key === 'file');
    expect(fileEntry?.[1]).toBeInstanceOf(File);
  });

  it('restartJob posts to restart endpoint', async () => {
    (apiPost as any).mockResolvedValue({});
    await restartJob('job-1');
    expect(apiPost).toHaveBeenCalledWith('/jobs/job-1/restart');
  });

  it('cancelJob posts to cancel endpoint', async () => {
    (apiPost as any).mockResolvedValue({});
    await cancelJob('job-2');
    expect(apiPost).toHaveBeenCalledWith('/jobs/job-2/cancel');
  });

  it('deleteJob calls apiDelete', async () => {
    (apiDelete as any).mockResolvedValue({});
    await deleteJob('job-3');
    expect(apiDelete).toHaveBeenCalledWith('/jobs/job-3');
  });

  it('assignTag posts tag payload', async () => {
    (apiPost as any).mockResolvedValue([]);
    await assignTag('job-4', 3);
    expect(apiPost).toHaveBeenCalledWith('/jobs/job-4/tags', { tag_ids: [3] });
  });

  it('removeTag deletes tag resource', async () => {
    (apiDelete as any).mockResolvedValue([]);
    await removeTag('job-5', 7);
    expect(apiDelete).toHaveBeenCalledWith('/jobs/job-5/tags/7');
  });
});
