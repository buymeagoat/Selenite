import React from 'react';
import { render, screen, fireEvent, act, within } from '@testing-library/react';
import { vi } from 'vitest';
import { Settings } from '../pages/Settings';
import { fetchSettings } from '../services/settings';

const mockAuthContext = vi.hoisted(() => ({
  user: {
    id: 1,
    username: 'admin',
    email: 'admin@selenite.local',
    is_admin: true,
    is_disabled: false,
    force_password_reset: false,
    last_login_at: null,
    created_at: new Date().toISOString()
  },
  token: 'token',
  isLoading: false,
  login: vi.fn(),
  logout: vi.fn(),
  refreshUser: vi.fn(),
}));

const fetchSettingsMock = vi.mocked(fetchSettings);

vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockAuthContext,
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>
}));

// Mock async data fetches to prevent unhandled errors
vi.mock('../services/settings', () => ({
  fetchSettings: vi.fn().mockResolvedValue({
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
    show_all_jobs: false,
    time_zone: 'UTC',
    date_format: 'locale',
    time_format: 'locale',
    locale: null,
    server_time_zone: 'UTC',
    transcode_to_wav: true,
    enable_empty_weights: false,
    last_selected_asr_set: null,
    last_selected_diarizer_set: null,
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
  }),
  updateSettings: vi.fn().mockResolvedValue({})
}));
vi.mock('../services/tags', () => ({
  fetchTags: vi.fn().mockResolvedValue({ items: [] }),
  deleteTag: vi.fn().mockResolvedValue({ jobs_affected: 0 }),
  createTag: vi.fn().mockResolvedValue({
    id: 99,
    name: 'Personal',
    color: '#000000',
    scope: 'personal',
    owner_user_id: 1,
    job_count: 0,
    created_at: new Date().toISOString(),
  }),
}));

vi.mock('../services/modelRegistry', () => ({
  listModelSets: vi.fn().mockResolvedValue([
    {
      id: 1,
      type: 'asr',
      name: 'whisper',
      description: '',
      abs_path: '/backend/models/whisper',
      enabled: true,
      disable_reason: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      weights: [
        {
          id: 10,
          set_id: 1,
          type: 'asr',
          name: 'base',
          description: '',
          abs_path: '/backend/models/whisper/base/model.bin',
          checksum: null,
          enabled: true,
          disable_reason: null,
          has_weights: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
    },
    {
      id: 2,
      type: 'diarizer',
      name: 'pyannote',
      description: '',
      abs_path: '/backend/models/pyannote',
      enabled: true,
      disable_reason: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      weights: [
        {
          id: 20,
          set_id: 2,
          type: 'diarizer',
          name: 'diarization-3.1',
          description: '',
          abs_path: '/backend/models/pyannote/diarization-3.1/model.bin',
          checksum: null,
          enabled: true,
          disable_reason: null,
          has_weights: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
    },
  ]),
}));

// Mock child components
vi.mock('../components/tags/TagList', () => ({
  TagList: ({ tags, onEdit, onDelete }: any) => (
    <div data-testid="tag-list">
      {tags.map((t: any) => (
        <div key={t.id}>
          {t.name}
          <button onClick={() => onEdit(t.id)}>Edit</button>
          <button onClick={() => onDelete(t.id)}>Delete</button>
        </div>
      ))}
    </div>
  )
}));

const renderSettings = async () => {
  let utils: ReturnType<typeof render>;
  await act(async () => {
    utils = render(<Settings />);
  });
  await screen.findByRole('heading', { name: /account/i });
  return utils!;
};

const changeField = async (element: HTMLElement, value: string) => {
  await act(async () => {
    fireEvent.change(element, { target: { value } });
  });
};

const clickButton = async (button: HTMLElement) => {
  await act(async () => {
    fireEvent.click(button);
  });
};

describe('Settings', () => {
  beforeEach(() => {
    mockAuthContext.user = {
      ...mockAuthContext.user,
      is_admin: true,
    };
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
      show_all_jobs: false,
      time_zone: 'UTC',
      date_format: 'locale',
      time_format: 'locale',
      locale: null,
      server_time_zone: 'UTC',
      transcode_to_wav: true,
      enable_empty_weights: false,
      last_selected_asr_set: null,
      last_selected_diarizer_set: null,
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
    });
  });

  it('renders all settings sections', async () => {
    await renderSettings();
    expect(screen.getByText(/default transcription options/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /tags/i })).toBeInTheDocument();
    expect(screen.getByTestId('settings-admin-redirect')).toBeInTheDocument();
  });

  it('renders change password form', async () => {
    await renderSettings();
    expect(screen.getByLabelText(/current password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
  });

  it('renders default transcription options for all users', async () => {
    await renderSettings();
    const defaultSection = screen.getByText(/default transcription options/i).closest('section');
    expect(defaultSection).not.toBeNull();
    expect(within(defaultSection as HTMLElement).getByLabelText(/ASR Model Set/i)).toBeInTheDocument();
    expect(within(defaultSection as HTMLElement).getByLabelText(/ASR Model Weight/i)).toBeInTheDocument();
    expect(within(defaultSection as HTMLElement).getByLabelText(/Diarizer Model Set/i)).toBeInTheDocument();
    expect(within(defaultSection as HTMLElement).getByLabelText(/Diarizer Weight/i)).toBeInTheDocument();
    expect(within(defaultSection as HTMLElement).getByLabelText(/default language/i)).toBeInTheDocument();
  });

  it(
    'shows admin defaults for non-admin users when overrides are disabled',
    async () => {
    mockAuthContext.user = {
      ...mockAuthContext.user,
      is_admin: false,
    };
    fetchSettingsMock.mockResolvedValue({
      default_asr_provider: 'whisper',
      default_model: 'tiny',
      default_language: 'auto',
      default_diarizer_provider: 'pyannote',
      default_diarizer: 'diarization-3.1',
      diarization_enabled: true,
      allow_asr_overrides: false,
      allow_diarizer_overrides: false,
      enable_timestamps: true,
      max_concurrent_jobs: 3,
      show_all_jobs: false,
      time_zone: 'UTC',
      date_format: 'locale',
      time_format: 'locale',
      locale: null,
      server_time_zone: 'UTC',
      transcode_to_wav: true,
      enable_empty_weights: false,
      last_selected_asr_set: null,
      last_selected_diarizer_set: null,
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
    });

    render(<Settings />);
    expect(await screen.findByText(/^ASR defaults$/i, {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByText(/whisper \/ tiny/i)).toBeInTheDocument();
    expect(
      await screen.findByText(/^Diarization defaults$/i, {}, { timeout: 3000 })
    ).toBeInTheDocument();
    expect(screen.getByText(/pyannote \/ diarization-3.1/i)).toBeInTheDocument();
  },
  10000
  );

  it('renders tag list section', async () => {
    await renderSettings();
    expect(screen.getByRole('heading', { name: /tags/i })).toBeInTheDocument();
  });

  it('submits password change form', async () => {
    await renderSettings();
    const currentPw = screen.getByLabelText(/current password/i);
    const newPw = screen.getByLabelText(/new password/i);
    const confirmPw = screen.getByLabelText(/confirm password/i);
    await changeField(currentPw, 'oldpass');
    await changeField(newPw, 'newpass123');
    await changeField(confirmPw, 'newpass123');
    const saveBtn = screen.getByTestId('password-save');
    await clickButton(saveBtn);
  });

  it('saves default transcription options', async () => {
    await renderSettings();
    const modelSelect = screen.getByLabelText(/ASR Model Weight/i);
    await changeField(modelSelect, 'base');
    const saveBtn = screen.getByTestId('default-save');
    await clickButton(saveBtn);
  });
});
