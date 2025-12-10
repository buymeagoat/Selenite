import React from 'react';
import { render, screen, fireEvent, act, within } from '@testing-library/react';
import { vi } from 'vitest';
import { Settings } from '../pages/Settings';

const mockAuthContext = vi.hoisted(() => ({
  user: {
    id: 1,
    username: 'admin',
    email: 'admin@example.com',
    is_admin: true,
    created_at: new Date().toISOString()
  },
  token: 'token',
  isLoading: false,
  login: vi.fn(),
  logout: vi.fn()
}));

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
    default_diarizer: 'vad',
    diarization_enabled: false,
    allow_job_overrides: false,
    enable_timestamps: true,
    max_concurrent_jobs: 3,
    time_zone: 'UTC',
    server_time_zone: 'UTC',
    transcode_to_wav: true,
  }),
  updateSettings: vi.fn().mockResolvedValue({})
}));
vi.mock('../services/tags', () => ({
  fetchTags: vi.fn().mockResolvedValue({ items: [] }),
  deleteTag: vi.fn().mockResolvedValue({ jobs_affected: 0 })
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
    expect(within(defaultSection as HTMLElement).getByLabelText(/default model/i)).toBeInTheDocument();
    expect(within(defaultSection as HTMLElement).getByLabelText(/default language/i)).toBeInTheDocument();
    expect(within(defaultSection as HTMLElement).queryByLabelText(/default diarizer/i)).not.toBeInTheDocument();
  });

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
    const modelSelect = screen.getByLabelText(/default model/i);
    await changeField(modelSelect, 'large');
    const saveBtn = screen.getByTestId('default-save');
    await clickButton(saveBtn);
  });
});
