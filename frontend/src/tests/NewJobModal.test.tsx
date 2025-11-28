import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NewJobModal } from '../components/modals/NewJobModal';
import {
  SettingsContext,
  type SettingsContextValue,
} from '../context/SettingsContext';
import { fetchCapabilities } from '../services/system';

vi.mock('../services/system', () => ({
  fetchCapabilities: vi.fn().mockResolvedValue({
    asr: [],
    diarizers: [
      { key: 'whisperx', display_name: 'WhisperX', requires_gpu: true, available: true, notes: [] },
      { key: 'pyannote', display_name: 'Pyannote', requires_gpu: true, available: false, notes: ['GPU required'] },
      { key: 'vad', display_name: 'VAD + clustering', requires_gpu: false, available: true, notes: [] },
    ],
  }),
}));

const mockedFetchCapabilities = fetchCapabilities as any;

const baseContext: SettingsContextValue = {
  status: 'ready',
  settings: {
    default_model: 'medium',
    default_language: 'auto',
    default_diarizer: 'vad',
    diarization_enabled: true,
    allow_job_overrides: true,
    enable_timestamps: true,
    max_concurrent_jobs: 3,
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
      asr: [],
      diarizers: [
        { key: 'whisperx', display_name: 'WhisperX', requires_gpu: true, available: true, notes: [] },
        { key: 'pyannote', display_name: 'Pyannote', requires_gpu: true, available: false, notes: ['GPU required'] },
        { key: 'vad', display_name: 'VAD + clustering', requires_gpu: false, available: true, notes: [] },
      ],
    });
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

  it('shows default model and language selections', () => {
    renderModal();
    expect((screen.getByLabelText(/model/i) as HTMLSelectElement).value).toBe('medium');
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
    renderModal({ defaultDiarizer: 'whisperx' });
    const select = (await screen.findByTestId('diarizer-select')) as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(select.value).toBe('whisperx');
    const options = Array.from(select.options);
    const disabledOption = options.find((opt) => opt.value === 'pyannote');
    expect(disabledOption?.disabled).toBe(true);
  });

  it('disables speaker detection when no diarizers are available', async () => {
    mockedFetchCapabilities.mockResolvedValueOnce({
      asr: [],
      diarizers: [
        { key: 'whisperx', display_name: 'WhisperX', requires_gpu: true, available: false, notes: ['GPU required'] },
        { key: 'vad', display_name: 'VAD + clustering', requires_gpu: false, available: false, notes: ['not installed'] },
      ],
    });
    renderModal();
    const help = await screen.findByText(/No compatible diarization models/i);
    expect(help).toBeInTheDocument();
    const checkbox = screen.getByLabelText(/detect speakers/i) as HTMLInputElement;
    expect(checkbox).toBeDisabled();
  });

  it('respects provided default model and language props', () => {
    renderModal({ defaultModel: 'small', defaultLanguage: 'es' });
    expect((screen.getByLabelText(/model/i) as HTMLSelectElement).value).toBe('small');
    expect((screen.getByLabelText(/language/i) as HTMLSelectElement).value).toBe('es');
  });
});
