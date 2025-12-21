import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { NewJobModal } from '../components/modals/NewJobModal';
import {
  SettingsContext,
  type SettingsContextValue,
} from '../context/SettingsContext';
import { fetchCapabilities } from '../services/system';
import { listModelSets } from '../services/modelRegistry';

vi.mock('../services/system', () => ({
  fetchCapabilities: vi.fn().mockResolvedValue({
    asr: [
      { provider: 'test-asr', display_name: 'test-asr', available: true, models: ['asr-weight'], notes: [] },
    ],
    diarizers: [
      { key: 'diar-weight', display_name: 'diar-weight', requires_gpu: false, available: true, notes: [] },
    ],
  }),
}));

vi.mock('../services/modelRegistry', () => ({
  listModelSets: vi.fn(),
}));

const mockedFetchCapabilities = fetchCapabilities as unknown as Mock;
const mockedListModelSets = listModelSets as unknown as Mock;

const mockRegistrySets = [
  {
    id: 1,
    type: 'asr',
    name: 'test-asr',
    description: 'test asr provider',
    abs_path: '/backend/models/test-asr',
    enabled: true,
    disable_reason: null,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    weights: [
      {
        id: 1,
        set_id: 1,
        type: 'asr',
        name: 'asr-weight',
        description: 'default weight',
        abs_path: '/backend/models/test-asr/asr-weight',
        checksum: null,
        enabled: true,
        disable_reason: null,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
    ],
  },
  {
    id: 2,
    type: 'diarizer',
    name: 'pyannote',
    description: 'test diarizer provider',
    abs_path: '/backend/models/pyannote',
    enabled: true,
    disable_reason: null,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    weights: [
      {
        id: 2,
        set_id: 2,
        type: 'diarizer',
        name: 'diar-weight',
        description: 'diarizer weight',
        abs_path: '/backend/models/pyannote/diar-weight',
        checksum: null,
        enabled: true,
        disable_reason: null,
        has_weights: true,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
    ],
  },
];

const baseContext: SettingsContextValue = {
  status: 'ready',
  settings: {
    default_asr_provider: 'test-asr',
    default_model: 'asr-weight',
    default_language: 'auto',
    default_diarizer_provider: 'pyannote',
    default_diarizer: 'diar-weight',
    diarization_enabled: true,
    allow_job_overrides: true,
    enable_timestamps: true,
    max_concurrent_jobs: 3,
    time_zone: 'UTC',
    server_time_zone: 'UTC',
    transcode_to_wav: true,
    enable_empty_weights: false,
    last_selected_asr_set: 'test-asr',
    last_selected_diarizer_set: 'diar-weight',
  },
  error: null,
  isRefreshing: false,
  refresh: vi.fn(),
};

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  onSubmit: vi.fn(),
};

describe('NewJobModal', () => {
  beforeEach(() => {
    defaultProps.onClose.mockClear();
    defaultProps.onSubmit.mockClear();
    mockedFetchCapabilities.mockClear();
    mockedFetchCapabilities.mockResolvedValue({
      asr: [
        { provider: 'test-asr', display_name: 'test-asr', available: true, models: ['asr-weight'], notes: [] },
      ],
      diarizers: [
        { key: 'diar-weight', display_name: 'diar-weight', requires_gpu: false, available: true, notes: [] },
      ],
    });
    mockedListModelSets.mockResolvedValue(mockRegistrySets);
  });

const renderModal = (
  overrideProps: Partial<React.ComponentProps<typeof NewJobModal>> = {},
  ctxOverrides: Partial<SettingsContextValue> = {}
) =>
  render(
    <SettingsContext.Provider value={{ ...baseContext, ...ctxOverrides }}>
      <NewJobModal {...defaultProps} {...overrideProps} />
    </SettingsContext.Provider>
  );

  it('does not render when isOpen is false', () => {
    renderModal({ isOpen: false });
    expect(screen.queryByText(/start transcription/i)).not.toBeInTheDocument();
  });

  it('renders modal when open', () => {
    renderModal();
    expect(screen.getByText(/new transcription job/i)).toBeInTheDocument();
    expect(screen.getByText(/drag & drop file here/i)).toBeInTheDocument();
  });

  it('closes modal via cancel button', () => {
    renderModal();
    fireEvent.click(screen.getByText(/cancel/i));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it('closes modal via close icon', () => {
    renderModal();
    fireEvent.click(screen.getByLabelText(/close/i));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it('disables submit button when no file is selected', () => {
    renderModal();
    expect(screen.getByText(/start transcription/i)).toBeDisabled();
  });

  it('shows default model and language selections', async () => {
    renderModal();
    const modelSelect = (await screen.findByLabelText(/model weight/i)) as HTMLSelectElement;
    await waitFor(() => {
      expect(modelSelect.value).toBe('asr-weight');
    });
    expect((screen.getByLabelText(/language/i) as HTMLSelectElement).value).toBe('auto');
  });

  it('has timestamps checkbox checked by default', () => {
    renderModal();
    const checkbox = screen.getByLabelText(/include timestamps/i) as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
  });

  it('allows toggling detect speakers', async () => {
    renderModal();
    const checkbox = (await screen.findByLabelText(/detect speakers/i)) as HTMLInputElement;
    expect(checkbox).not.toBeDisabled();
    expect(checkbox.checked).toBe(true);
    fireEvent.click(checkbox);
    expect(checkbox.checked).toBe(false);
  });

  it('shows diarizer dropdown with options and respects defaults', async () => {
    renderModal(
      {},
      {
        settings: {
          ...baseContext.settings!,
          default_diarizer: 'diar-weight',
        },
      }
    );
    const select = (await screen.findByTestId('diarizer-select')) as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(select.value).toBe('diar-weight');
  });

  it('disables model selection and submit when registry is empty', async () => {
    mockedFetchCapabilities.mockResolvedValueOnce({ asr: [], diarizers: [] });
    mockedListModelSets.mockResolvedValueOnce([]);
    renderModal();
    const modelSelect = (await screen.findByTestId('model-select')) as HTMLSelectElement;
    expect(modelSelect).toBeDisabled();
    expect(screen.getByTestId('start-transcription-btn')).toBeDisabled();
    expect(await screen.findByText(/no providers registered/i)).toBeInTheDocument();
    expect(await screen.findByText(/no model weights registered/i)).toBeInTheDocument();
  });
});
