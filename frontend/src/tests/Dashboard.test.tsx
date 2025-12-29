import React from 'react';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
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
const createTagMock = vi.fn();
const fetchSettingsMock = vi.fn();
const renameJobMock = vi.fn();
const jsZipFileMock = vi.fn();
const jsZipGenerateMock = vi.fn();
const jsZipMock = vi.hoisted(() => vi.fn());

vi.mock('../services/jobs', () => ({
  fetchJobs: (...args: any[]) => fetchJobsMock(...args),
  createJob: (...args: any[]) => createJobMock(...args),
  restartJob: (...args: any[]) => restartJobMock(...args),
  cancelJob: (...args: any[]) => cancelJobMock(...args),
  deleteJob: (...args: any[]) => deleteJobMock(...args),
  assignTag: (...args: any[]) => assignTagMock(...args),
  removeTag: (...args: any[]) => removeTagMock(...args),
  renameJob: (...args: any[]) => renameJobMock(...args),
}));

vi.mock('../services/tags', () => ({
  fetchTags: (...args: any[]) => fetchTagsMock(...args),
  createTag: (...args: any[]) => createTagMock(...args),
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

vi.mock('jszip', () => ({
  default: jsZipMock,
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
  JobFilters: ({ onCustomRange }: any) => (
    <button type="button" data-testid="open-custom-range" onClick={() => onCustomRange?.()}>
      Open Custom Range
    </button>
  ),
}));

vi.mock('../components/jobs/JobCard', () => ({
  JobCard: ({ job, selectionMode, selected, onSelectToggle, onClick }: any) => (
    <div>
      {selectionMode && (
        <input
          data-testid={`select-${job.id}`}
          type="checkbox"
          checked={selected}
          onChange={(event) => onSelectToggle?.(job.id, event.target.checked)}
        />
      )}
      <button type="button" onClick={() => onClick(job.id)}>
        {job.original_filename}
      </button>
    </div>
  ),
}));

vi.mock('../components/common/Skeleton', () => ({
  SkeletonGrid: () => <div data-testid="skeleton-grid" />,
}));

vi.mock('../components/modals/NewJobModal', () => ({
  NewJobModal: () => null,
}));

vi.mock('../components/modals/JobDetailModal', () => ({
  JobDetailModal: ({ isOpen, job, onUpdateTags }: any) =>
    isOpen ? (
      <button data-testid="update-tags" onClick={() => onUpdateTags(job.id, [1, 2])}>
        Update tags
      </button>
    ) : null,
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
    createTagMock.mockReset();
    renameJobMock.mockReset();
    localStorage.removeItem(settingsCacheKey);
    jsZipFileMock.mockReset();
    jsZipGenerateMock.mockReset();
    jsZipMock.mockReset();
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
      allow_asr_overrides: true,
      allow_diarizer_overrides: true,
      enable_timestamps: true,
      max_concurrent_jobs: 3,
      time_zone: 'UTC',
      server_time_zone: 'UTC',
      transcode_to_wav: true,
      enable_empty_weights: false,
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

  it('selects all visible jobs when toggling select all', async () => {
    const jobA = buildJob({ id: 'job-a', original_filename: 'Alpha' });
    const jobB = buildJob({ id: 'job-b', original_filename: 'Beta' });
    fetchJobsMock.mockResolvedValue(jobsResponse([jobA, jobB]));
    fetchTagsMock.mockResolvedValue({ total: 0, items: [] });
    fetchSettingsMock.mockResolvedValue({
      default_asr_provider: null,
      default_model: 'medium',
      default_language: 'auto',
      default_diarizer_provider: 'pyannote',
      default_diarizer: 'vad',
      diarization_enabled: true,
      allow_asr_overrides: true,
      allow_diarizer_overrides: true,
      enable_timestamps: true,
      max_concurrent_jobs: 3,
      time_zone: 'UTC',
      server_time_zone: 'UTC',
      transcode_to_wav: true,
      enable_empty_weights: false,
      last_selected_asr_set: null,
      last_selected_diarizer_set: null,
    });

    jsZipMock.mockImplementation(() => ({
      file: jsZipFileMock,
      generateAsync: jsZipGenerateMock.mockResolvedValue(new Blob(['zip'])),
    }));

    renderDashboard();

    await waitFor(() => expect(fetchJobsMock).toHaveBeenCalled());

    const selectAll = screen.getByRole('checkbox', { name: /select all/i });
    fireEvent.click(selectAll);

    await waitFor(() => {
      expect((screen.getByTestId('select-job-a') as HTMLInputElement).checked).toBe(true);
      expect((screen.getByTestId('select-job-b') as HTMLInputElement).checked).toBe(true);
    });

    fireEvent.click(selectAll);

    await waitFor(() => {
      expect((screen.getByTestId('select-job-a') as HTMLInputElement).checked).toBe(false);
      expect((screen.getByTestId('select-job-b') as HTMLInputElement).checked).toBe(false);
    });
  });

  it('downloads selected transcripts as a zip when multiple jobs are selected', async () => {
    const jobA = buildJob({ id: 'job-a', original_filename: 'Alpha' });
    const jobB = buildJob({ id: 'job-b', original_filename: 'Beta' });
    fetchJobsMock.mockResolvedValue(jobsResponse([jobA, jobB]));
    fetchTagsMock.mockResolvedValue({ total: 0, items: [] });
    fetchSettingsMock.mockResolvedValue({
      default_asr_provider: null,
      default_model: 'medium',
      default_language: 'auto',
      default_diarizer_provider: 'pyannote',
      default_diarizer: 'vad',
      diarization_enabled: true,
      allow_asr_overrides: true,
      allow_diarizer_overrides: true,
      enable_timestamps: true,
      max_concurrent_jobs: 3,
      time_zone: 'UTC',
      server_time_zone: 'UTC',
      transcode_to_wav: true,
      enable_empty_weights: false,
      last_selected_asr_set: null,
      last_selected_diarizer_set: null,
    });

    jsZipMock.mockImplementation(() => ({
      file: jsZipFileMock,
      generateAsync: jsZipGenerateMock.mockResolvedValue(new Blob(['zip'])),
    }));

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => new Blob(['transcript']),
      headers: {
        get: () => 'attachment; filename="transcript.txt"',
      },
    });
    const originalFetch = globalThis.fetch;
    const originalCreateObjectURL = URL.createObjectURL;
    const originalRevokeObjectURL = URL.revokeObjectURL;
    globalThis.fetch = fetchMock as any;
    URL.createObjectURL = vi.fn(() => 'blob:download');
    URL.revokeObjectURL = vi.fn();

    try {
      renderDashboard();
      await waitFor(() => expect(fetchJobsMock).toHaveBeenCalled());

      fireEvent.click(screen.getByTestId('select-job-a'));
      fireEvent.click(screen.getByTestId('select-job-b'));

    fireEvent.click(screen.getByRole('button', { name: /^download$/i }));

    const dialog = screen.getByRole('dialog', { name: /export transcripts/i });
    fireEvent.click(within(dialog).getByRole('button', { name: /^download$/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(jsZipMock).toHaveBeenCalledTimes(1);
    expect(jsZipFileMock).toHaveBeenCalledTimes(2);
    expect(jsZipGenerateMock).toHaveBeenCalledWith({ type: 'blob' });
    } finally {
      globalThis.fetch = originalFetch;
      URL.createObjectURL = originalCreateObjectURL;
      URL.revokeObjectURL = originalRevokeObjectURL;
    }
  });

  it('renames a selected job from the bulk rename modal', async () => {
    const job = buildJob({ id: 'job-9', original_filename: 'Original.mp3' });
    fetchJobsMock
      .mockResolvedValueOnce(jobsResponse([job]))
      .mockResolvedValueOnce(jobsResponse([{ ...job, original_filename: 'Updated.mp3' }]));
    fetchTagsMock.mockResolvedValue({ total: 0, items: [] });
    fetchSettingsMock.mockResolvedValue({
      default_asr_provider: null,
      default_model: 'medium',
      default_language: 'auto',
      default_diarizer_provider: 'pyannote',
      default_diarizer: 'vad',
      diarization_enabled: true,
      allow_asr_overrides: true,
      allow_diarizer_overrides: true,
      enable_timestamps: true,
      max_concurrent_jobs: 3,
      time_zone: 'UTC',
      server_time_zone: 'UTC',
      transcode_to_wav: true,
      enable_empty_weights: false,
      last_selected_asr_set: null,
      last_selected_diarizer_set: null,
    });
    renameJobMock.mockResolvedValue({ ...job, original_filename: 'Updated.mp3' });

    renderDashboard();
    await waitFor(() => expect(fetchJobsMock).toHaveBeenCalled());

    fireEvent.click(screen.getByTestId('select-job-9'));
    fireEvent.click(screen.getByRole('button', { name: /^rename$/i }));

    const dialog = screen.getByRole('dialog', { name: /rename job/i });
    fireEvent.change(within(dialog).getByLabelText(/new name/i), {
      target: { value: 'Updated' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /^rename$/i }));

    await waitFor(() => expect(renameJobMock).toHaveBeenCalledWith('job-9', 'Updated'));
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
      allow_asr_overrides: false,
      allow_diarizer_overrides: false,
      enable_timestamps: true,
      max_concurrent_jobs: 3,
      time_zone: 'UTC',
      server_time_zone: 'UTC',
      transcode_to_wav: true,
      enable_empty_weights: false,
      last_selected_asr_set: null,
      last_selected_diarizer_set: null,
    });

    renderDashboard();
    await waitFor(() => expect(fetchJobsMock).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText(/no transcriptions yet/i)).toBeInTheDocument());
    expect(toastMock.showError).toHaveBeenCalledWith(expect.stringContaining('Boom'));
  });

  it('creates a custom tag and applies it to selected jobs', async () => {
    const job = buildJob({ id: 'job-1', original_filename: 'Custom tag test' });
    fetchJobsMock
      .mockResolvedValueOnce(jobsResponse([job]))
      .mockResolvedValueOnce(jobsResponse([job]));
    fetchTagsMock
      .mockResolvedValueOnce({ total: 0, items: [] })
      .mockResolvedValueOnce({
        total: 1,
        items: [{ id: 42, name: 'Priority', color: '#000000', job_count: 0, created_at: new Date().toISOString() }],
      });
    createTagMock.mockResolvedValue({ id: 42, name: 'Priority', color: '#000000', job_count: 0, created_at: new Date().toISOString() });
    fetchSettingsMock.mockResolvedValue({
      default_asr_provider: null,
      default_model: 'medium',
      default_language: 'auto',
      default_diarizer_provider: 'pyannote',
      default_diarizer: 'vad',
      diarization_enabled: false,
      allow_asr_overrides: false,
      allow_diarizer_overrides: false,
      enable_timestamps: true,
      max_concurrent_jobs: 3,
      time_zone: 'UTC',
      server_time_zone: 'UTC',
      transcode_to_wav: true,
      enable_empty_weights: false,
      last_selected_asr_set: null,
      last_selected_diarizer_set: null,
    });

    renderDashboard();
    await waitFor(() => expect(fetchJobsMock).toHaveBeenCalled());

    fireEvent.click(screen.getByTestId('select-job-1'));
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'custom' } });

    const dialog = screen.getByRole('dialog', { name: /custom tag/i });
    fireEvent.change(within(dialog).getByLabelText(/tag name/i), { target: { value: 'Priority' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Apply' }));

    await waitFor(() => expect(createTagMock).toHaveBeenCalledWith({ name: 'Priority', color: '#000000' }));
    await waitFor(() =>
      expect(assignTagMock).toHaveBeenCalledWith('job-1', expect.arrayContaining([1, 42]))
    );
    expect(toastMock.showSuccess).toHaveBeenCalledWith(expect.stringContaining('Applied tag'));
  });

  it('updates tags from the modal without dropping existing tags', async () => {
    const job = buildJob({ id: 'job-2', original_filename: 'Modal tag test' });
    fetchJobsMock.mockResolvedValue(jobsResponse([job]));
    fetchTagsMock.mockResolvedValue({ total: 1, items: [{ id: 1, name: 'General', color: '#1D8348', job_count: 1, created_at: new Date().toISOString() }] });
    fetchSettingsMock.mockResolvedValue({
      default_asr_provider: null,
      default_model: 'medium',
      default_language: 'auto',
      default_diarizer_provider: 'pyannote',
      default_diarizer: 'vad',
      diarization_enabled: false,
      allow_asr_overrides: false,
      allow_diarizer_overrides: false,
      enable_timestamps: true,
      max_concurrent_jobs: 3,
      time_zone: 'UTC',
      server_time_zone: 'UTC',
      transcode_to_wav: true,
      enable_empty_weights: false,
      last_selected_asr_set: null,
      last_selected_diarizer_set: null,
    });

    renderDashboard();
    await waitFor(() => expect(fetchJobsMock).toHaveBeenCalled());

    fireEvent.click(screen.getByText(/Modal tag test/i));
    fireEvent.click(screen.getByTestId('update-tags'));

    await waitFor(() => expect(assignTagMock).toHaveBeenCalledWith('job-2', [1, 2]));
  });

  it('defaults custom range meridiem to AM', async () => {
    const job = buildJob({ id: 'job-3', original_filename: 'Range test' });
    fetchJobsMock.mockResolvedValue(jobsResponse([job]));
    fetchTagsMock.mockResolvedValue({ total: 0, items: [] });
    fetchSettingsMock.mockResolvedValue({
      default_asr_provider: null,
      default_model: 'medium',
      default_language: 'auto',
      default_diarizer_provider: 'pyannote',
      default_diarizer: 'vad',
      diarization_enabled: false,
      allow_asr_overrides: false,
      allow_diarizer_overrides: false,
      enable_timestamps: true,
      max_concurrent_jobs: 3,
      time_zone: 'UTC',
      server_time_zone: 'UTC',
      transcode_to_wav: true,
      enable_empty_weights: false,
      last_selected_asr_set: null,
      last_selected_diarizer_set: null,
    });

    renderDashboard();
    await waitFor(() => expect(fetchJobsMock).toHaveBeenCalled());

    fireEvent.click(screen.getByTestId('open-custom-range'));
    const startMeridiem = screen.getByLabelText(/start meridiem/i) as HTMLSelectElement;
    const endMeridiem = screen.getByLabelText(/end meridiem/i) as HTMLSelectElement;
    expect(startMeridiem.value).toBe('AM');
    expect(endMeridiem.value).toBe('AM');
  });
});
