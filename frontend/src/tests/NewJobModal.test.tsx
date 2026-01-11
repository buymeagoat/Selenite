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
        has_weights: true,
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
    allow_asr_overrides: true,
    allow_diarizer_overrides: true,
    enable_timestamps: true,
    max_concurrent_jobs: 3,
    show_all_jobs: false,
    time_zone: 'UTC',
    server_time_zone: 'UTC',
    transcode_to_wav: true,
    enable_empty_weights: false,
    last_selected_asr_set: 'test-asr',
    last_selected_diarizer_set: 'diar-weight',
    feedback_store_enabled: true,
    feedback_email_enabled: false,
    feedback_webhook_enabled: false,
    feedback_destination_email: null,
    feedback_webhook_url: null,
    smtp_host: null,
    smtp_port: null,
    smtp_username: null,
    smtp_from_email: null,
    smtp_use_tls: true,
    smtp_password_set: false,
    session_timeout_minutes: 30,
    allow_self_signup: false,
    require_signup_verification: false,
    require_signup_captcha: false,
    signup_captcha_provider: null,
    signup_captcha_site_key: null,
    password_min_length: 12,
    password_require_uppercase: true,
    password_require_lowercase: true,
    password_require_number: true,
    password_require_special: false,
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

const openAdvanced = async () => {
  if (!screen.queryByTestId('advanced-panel')) {
    fireEvent.click(await screen.findByTestId('advanced-toggle'));
  }
  await screen.findByTestId('advanced-panel');
};

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

  it('prefills fields when restart data is provided', async () => {
    const file = new File(['audio'], 'restart.mp3', { type: 'audio/mpeg' });
    renderModal({
      prefill: {
        file,
        jobName: 'Restarted Job',
        provider: 'test-asr',
        model: 'asr-weight',
        language: 'en',
        enableTimestamps: false,
        enableSpeakerDetection: true,
        diarizerProvider: 'pyannote',
        diarizer: 'diar-weight',
        speakerCount: 2,
      },
    });

    await waitFor(() => expect(screen.getByText('restart.mp3')).toBeInTheDocument());
    const nameInput = screen.getByLabelText(/job name/i) as HTMLInputElement;
    await waitFor(() => expect(nameInput.value).toBe('Restarted Job'));

    await openAdvanced();
    expect((screen.getByTestId('provider-select') as HTMLSelectElement).value).toBe('test-asr');
    expect((screen.getByTestId('model-select') as HTMLSelectElement).value).toBe('asr-weight');
    expect((screen.getByTestId('language-select') as HTMLSelectElement).value).toBe('en');
    const timestamps = screen.getByLabelText(/include timestamps/i) as HTMLInputElement;
    expect(timestamps.checked).toBe(false);
    const speakerCount = screen.getByTestId('speaker-count-select') as HTMLSelectElement;
    expect(speakerCount.value).toBe('2');
  });

  it('shows default model and language selections', async () => {
    renderModal();
    await openAdvanced();
    const modelSelect = (await screen.findByLabelText(/model weight/i)) as HTMLSelectElement;
    await waitFor(() => {
      expect(modelSelect.value).toBe('asr-weight');
    });
    expect((screen.getByTestId('language-select') as HTMLSelectElement).value).toBe('auto');
  });

  it('has timestamps checkbox checked by default', async () => {
    renderModal();
    await openAdvanced();
    const checkbox = screen.getByLabelText(/include timestamps/i) as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
  });

  it('initializes defaults after settings load if modal opened early', async () => {
    const registryWithTiny = [
      {
        id: 1,
        type: 'asr',
        name: 'whisper',
        description: 'whisper provider',
        abs_path: '/backend/models/whisper',
        enabled: true,
        disable_reason: null,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        weights: [
          {
            id: 1,
            set_id: 1,
            type: 'asr',
            name: 'base',
            description: 'base weight',
            abs_path: '/backend/models/whisper/base',
            checksum: null,
            has_weights: true,
            enabled: true,
            disable_reason: null,
            created_at: '2025-01-01T00:00:00Z',
            updated_at: '2025-01-01T00:00:00Z',
          },
          {
            id: 2,
            set_id: 1,
            type: 'asr',
            name: 'tiny',
            description: 'tiny weight',
            abs_path: '/backend/models/whisper/tiny',
            checksum: null,
            has_weights: true,
            enabled: true,
            disable_reason: null,
            created_at: '2025-01-01T00:00:00Z',
            updated_at: '2025-01-01T00:00:00Z',
          },
        ],
      },
    ];
    mockedListModelSets.mockResolvedValueOnce(registryWithTiny);

    const loadingContext: SettingsContextValue = {
      ...baseContext,
      status: 'loading',
      settings: null,
    };

    const { rerender } = render(
      <SettingsContext.Provider value={loadingContext}>
        <NewJobModal {...defaultProps} />
      </SettingsContext.Provider>
    );

    await openAdvanced();

    const readyContext: SettingsContextValue = {
      ...baseContext,
      status: 'ready',
      settings: {
        ...baseContext.settings!,
        default_asr_provider: 'whisper',
        default_model: 'tiny',
      },
    };

    rerender(
      <SettingsContext.Provider value={readyContext}>
        <NewJobModal {...defaultProps} />
      </SettingsContext.Provider>
    );

    await openAdvanced();
    const modelSelect = (await screen.findByTestId('model-select')) as HTMLSelectElement;
    await waitFor(() => expect(modelSelect.value).toBe('tiny'));
  });

  it('submits selected model and provider even when they match defaults', async () => {
    const submitSpy = vi.fn().mockResolvedValue(undefined);
    renderModal({ onSubmit: submitSpy });
    await openAdvanced();
    await waitFor(() => expect(screen.getByTestId('provider-select')).toBeEnabled());
    await waitFor(() => expect(screen.getByTestId('model-select')).toBeEnabled());
    await waitFor(() => {
      expect((screen.getByTestId('provider-select') as HTMLSelectElement).value).toBe('test-asr');
      expect((screen.getByTestId('model-select') as HTMLSelectElement).value).toBe('asr-weight');
    });

    const fileInput = (await screen.findByTestId('file-input')) as HTMLInputElement;
    const file = new File(['audio'], 'sample.mp3', { type: 'audio/mpeg' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const submitButton = screen.getByTestId('start-transcription-btn');
    await waitFor(() => expect(submitButton).toBeEnabled());
    fireEvent.click(submitButton);

    await waitFor(() => expect(submitSpy).toHaveBeenCalledTimes(1));
    expect(submitSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        jobName: 'sample',
        provider: 'test-asr',
        model: 'asr-weight',
        language: 'auto',
        enableTimestamps: true,
        enableSpeakerDetection: true,
        diarizer: 'diar-weight',
        speakerCount: null,
      })
    );
  });

  it('allows toggling detect speakers', async () => {
    renderModal();
    await openAdvanced();
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
    await openAdvanced();
    const select = (await screen.findByTestId('diarizer-select')) as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(select.value).toBe('diar-weight');
  });

  it('disables model selection and submit when registry is empty', async () => {
    mockedFetchCapabilities.mockResolvedValueOnce({ asr: [], diarizers: [] });
    mockedListModelSets.mockResolvedValueOnce([]);
    renderModal();
    await openAdvanced();
    const modelSelect = (await screen.findByTestId('model-select')) as HTMLSelectElement;
    expect(modelSelect).toBeDisabled();
    expect(screen.getByTestId('start-transcription-btn')).toBeDisabled();
    expect(await screen.findByText(/no providers registered/i)).toBeInTheDocument();
    expect(await screen.findByText(/no model weights registered/i)).toBeInTheDocument();
  });

  it('shows advanced panel when toggled', async () => {
    renderModal();
    const toggle = screen.getByTestId('advanced-toggle');
    expect(screen.queryByTestId('advanced-panel')).not.toBeInTheDocument();
    fireEvent.click(toggle);
    expect(await screen.findByTestId('advanced-panel')).toBeInTheDocument();
  });

  it('hides override controls when admin disables per-job overrides', async () => {
    renderModal(
      {},
      {
        settings: {
          ...baseContext.settings!,
          allow_asr_overrides: false,
          allow_diarizer_overrides: false,
        },
      }
    );
    await openAdvanced();
    expect(
      screen.getByText(/per-job asr selection is disabled by the administrator/i)
    ).toBeInTheDocument();
    expect(screen.queryByTestId('provider-select')).not.toBeInTheDocument();
    expect(screen.queryByTestId('language-select')).not.toBeInTheDocument();
    expect(screen.queryByTestId('timestamps-checkbox')).not.toBeInTheDocument();
    expect(screen.queryByTestId('extra-flags-input')).not.toBeInTheDocument();
    expect(
      screen.getByText(/per-job diarization overrides are disabled by the administrator/i)
    ).toBeInTheDocument();
    expect(screen.queryByTestId('speakers-checkbox')).not.toBeInTheDocument();
  });
});
