import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { Dashboard } from '../pages/Dashboard';
import { ApiError } from '../lib/api';
import { SettingsProvider } from '../context/SettingsContext';

const fetchJobsMock = vi.fn();
const createJobMock = vi.fn();
const restartJobMock = vi.fn();
const cancelJobMock = vi.fn();
const deleteJobMock = vi.fn();
const assignTagMock = vi.fn();
const removeTagMock = vi.fn();
const fetchTagsMock = vi.fn();
const fetchSettingsMock = vi.fn();

vi.mock('../services/jobs', () => ({
  fetchJobs: (...args: any[]) => fetchJobsMock(...args),
  createJob: (...args: any[]) => createJobMock(...args),
  restartJob: (...args: any[]) => restartJobMock(...args),
  cancelJob: (...args: any[]) => cancelJobMock(...args),
  deleteJob: (...args: any[]) => deleteJobMock(...args),
  assignTag: (...args: any[]) => assignTagMock(...args),
  removeTag: (...args: any[]) => removeTagMock(...args),
}));

vi.mock('../services/tags', () => ({
  fetchTags: (...args: any[]) => fetchTagsMock(...args),
}));

vi.mock('../services/settings', () => ({
  fetchSettings: (...args: any[]) => fetchSettingsMock(...args),
}));

const toastMock = {
  showError: vi.fn(),
  showSuccess: vi.fn(),
  showToast: vi.fn(),
  showInfo: vi.fn(),
};

vi.mock('../context/ToastContext', () => ({
  useToast: () => toastMock,
}));

vi.mock('../hooks/usePolling', () => ({
  usePolling: vi.fn(),
}));

const buildJob = (overrides: Partial<any> = {}) => ({
  id: overrides.id ?? `job-${Math.random().toString(36).slice(2, 9)}`,
  original_filename: overrides.original_filename ?? 'audio.wav',
  file_size: 1024,
  mime_type: 'audio/wav',
  duration: 60,
  status: overrides.status ?? 'completed',
  progress_percent: 100,
  progress_stage: 'done',
  estimated_time_left: null,
  estimated_total_seconds: 120,
  model_used: 'medium',
  language_detected: 'English',
  speaker_count: 1,
  has_timestamps: true,
  has_speaker_labels: false,
  tags: overrides.tags ?? [
    { id: 1, name: 'General', color: '#1D8348' },
  ],
  created_at: overrides.created_at ?? new Date().toISOString(),
  updated_at: overrides.updated_at ?? new Date().toISOString(),
  started_at: null,
  completed_at: new Date().toISOString(),
  stalled_at: null,
});

const jobsResponse = (items: any[]) => ({
  total: items.length,
  limit: 50,
  offset: 0,
  items,
});

vi.mock('../components/common/SearchBar', () => ({
  SearchBar: ({ value, onChange }: any) => (
    <input
      data-testid="search-input"
      value={value}
      placeholder="Search jobs"
      onChange={(event: React.ChangeEvent<HTMLInputElement>) => onChange(event.target.value)}
    />
  ),
}));

vi.mock('../components/jobs/JobFilters', () => ({
  JobFilters: () => <div data-testid="job-filters" />,
}));

vi.mock('../components/jobs/JobCard', () => ({
  JobCard: ({ job }: any) => <div>{job.original_filename}</div>,
}));

vi.mock('../components/common/Skeleton', () => ({
  SkeletonGrid: () => <div data-testid="skeleton-grid" />,
}));

vi.mock('../components/modals/NewJobModal', () => ({
  NewJobModal: () => null,
}));

vi.mock('../components/modals/JobDetailModal', () => ({
  JobDetailModal: () => null,
}));

const settingsCacheKey = 'dashboard_test_settings';

const renderDashboard = () =>
  render(
    <SettingsProvider
      fetcher={(options) => fetchSettingsMock(options)}
      cacheKey={settingsCacheKey}
    >
      <Dashboard />
    </SettingsProvider>
  );

describe('Dashboard', () => {
  beforeEach(() => {
    fetchJobsMock.mockReset();
    fetchTagsMock.mockReset();
    fetchSettingsMock.mockReset();
    createJobMock.mockReset();
    restartJobMock.mockReset();
    cancelJobMock.mockReset();
    deleteJobMock.mockReset();
    assignTagMock.mockReset();
    removeTagMock.mockReset();
    toastMock.showError.mockReset();
    toastMock.showSuccess.mockReset();
    localStorage.removeItem(settingsCacheKey);
  });

  it('loads jobs and filters with the search bar', async () => {
    const jobA = buildJob({ id: 'a', original_filename: 'Quarterly Review' });
    const jobB = buildJob({ id: 'b', original_filename: 'All Hands Recording' });
    fetchJobsMock.mockResolvedValue(jobsResponse([jobA, jobB]));
    fetchTagsMock.mockResolvedValue({ total: 1, items: [{ id: 1, name: 'General', color: '#1D8348', job_count: 2, created_at: new Date().toISOString() }] });
    fetchSettingsMock.mockResolvedValue({
      default_asr_provider: null,
      default_model: 'medium',
      default_language: 'auto',
      default_diarizer_provider: 'pyannote',
      default_diarizer: 'vad',
      diarization_enabled: true,
      allow_job_overrides: true,
      enable_timestamps: true,
      max_concurrent_jobs: 3,
      time_zone: 'UTC',
      server_time_zone: 'UTC',
      transcode_to_wav: true,
      last_selected_asr_set: null,
      last_selected_diarizer_set: null,
    });

    renderDashboard();

    await waitFor(() => expect(fetchJobsMock).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText(/Quarterly Review/i)).toBeInTheDocument());
    expect(screen.getByText(/All Hands Recording/i)).toBeInTheDocument();

    const searchInput = screen.getByTestId('search-input');
    fireEvent.change(searchInput, { target: { value: 'quarter' } });

    expect(screen.getByText(/Quarterly Review/i)).toBeInTheDocument();
    expect(screen.queryByText(/All Hands Recording/i)).not.toBeInTheDocument();
  });

  it('shows empty-state and surfaces toast errors when fetching jobs fails', async () => {
    fetchJobsMock.mockRejectedValueOnce(new ApiError('Boom', 500));
    fetchTagsMock.mockResolvedValue({ total: 0, items: [] });
    fetchSettingsMock.mockResolvedValue({
      default_asr_provider: null,
      default_model: 'medium',
      default_language: 'auto',
      default_diarizer_provider: 'pyannote',
      default_diarizer: 'vad',
      diarization_enabled: false,
      allow_job_overrides: false,
      enable_timestamps: true,
      max_concurrent_jobs: 3,
      time_zone: 'UTC',
      server_time_zone: 'UTC',
      transcode_to_wav: true,
      last_selected_asr_set: null,
      last_selected_diarizer_set: null,
    });

    renderDashboard();
    await waitFor(() => expect(fetchJobsMock).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText(/no transcriptions yet/i)).toBeInTheDocument());
    expect(toastMock.showError).toHaveBeenCalledWith(expect.stringContaining('Boom'));
  });
});
