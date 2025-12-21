import React from 'react';
import { render, screen, act, fireEvent, within, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { Admin } from '../pages/Admin';
import { updateSettings } from '../services/settings';

const mockAuthContext = vi.hoisted(() => ({
  user: {
    id: 1,
    username: 'admin',
    email: 'admin@example.com',
    is_admin: true,
    created_at: new Date().toISOString(),
  },
  token: 'token',
  isLoading: false,
  login: vi.fn(),
  logout: vi.fn(),
}));

const toastSpies = vi.hoisted(() => ({
  showToast: vi.fn(),
  showSuccess: vi.fn(),
  showError: vi.fn(),
  showInfo: vi.fn(),
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockAuthContext,
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('../context/ToastContext', () => ({
  useToast: () => toastSpies,
}));

const updateAsrSettings = vi.hoisted(() => vi.fn().mockResolvedValue({}));

vi.mock('../services/settings', () => ({
  fetchSettings: vi.fn().mockResolvedValue({
    default_asr_provider: null,
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
    last_selected_asr_set: 'whisper',
    last_selected_diarizer_set: 'pyannote',
  }),
  updateSettings: vi.fn().mockResolvedValue({}),
  updateAsrSettings,
}));

const mockSystemInfo = vi.hoisted(() => ({
  detected_at: '2025-11-25T00:00:00.000Z',
  os: { system: 'TestOS', release: '1.0', version: '1.0', machine: 'x86_64' },
  cpu: { model: 'Sample CPU', architecture: 'x86_64', cores_physical: 4, cores_logical: 8, max_frequency_mhz: 3500 },
  memory: { total_gb: 16, available_gb: 8 },
  gpu: { has_gpu: true, api: 'cuda', driver: '12.1', devices: [{ name: 'Mock GPU', memory_gb: 12, multi_processor_count: 64 }] },
  storage: {
    database: { path: '/tmp/db', total_gb: 100, used_gb: 10, free_gb: 90 },
    media: { path: '/tmp/media', total_gb: 200, used_gb: 20, free_gb: 180 },
    transcripts: { path: '/tmp/trans', total_gb: 150, used_gb: 30, free_gb: 120 },
    project: { path: '/tmp/project', total_gb: 300, used_gb: 50, free_gb: 250 },
  },
  network: { hostname: 'selenite-host', interfaces: [{ name: 'eth0', ipv4: ['192.168.1.50'] }] },
  runtime: { python: '3.11.0', node: 'v20.10.0' },
  container: { is_container: false, indicators: [] },
  recommendation: { suggested_asr_model: 'large-v3', suggested_diarization: 'pyannote', basis: ['mock'] },
}));

const refreshSpy = vi.hoisted(() => vi.fn());

const mockCapabilities = vi.hoisted(() => ({
  asr: [
    {
      provider: 'test-asr',
      display_name: 'test-asr',
      available: true,
      models: ['asr-weight'],
      notes: ['missing dependencies'],
    },
  ],
  diarizers: [
    {
      key: 'diar-weight',
      provider: 'pyannote',
      display_name: 'diar-weight',
      requires_gpu: false,
      available: true,
      notes: [],
    },
  ],
}));

vi.mock('../services/system', () => ({
  fetchSystemInfo: vi.fn().mockResolvedValue(mockSystemInfo),
  refreshSystemInfo: refreshSpy,
  fetchCapabilities: vi.fn().mockResolvedValue(mockCapabilities),
  restartServer: vi.fn().mockResolvedValue({ message: 'Restart requested' }),
  shutdownServer: vi.fn().mockResolvedValue({ message: 'Shutdown requested' }),
  fullRestartServer: vi.fn().mockResolvedValue({ message: 'Full restart requested' }),
}));

refreshSpy.mockResolvedValue(mockSystemInfo);

const mockRegistry = vi.hoisted(() => ([
  {
    id: 1,
    type: 'asr',
    name: 'test-asr',
    description: '',
    abs_path: '/backend/models/test-asr',
    enabled: true,
    disable_reason: null,
    weights: [
      {
        id: 10,
        set_id: 1,
        type: 'asr',
        name: 'asr-weight',
        description: '',
        abs_path: '/backend/models/test-asr/asr-weight/model.bin',
        checksum: null,
        enabled: true,
        disable_reason: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ],
  },
  {
    id: 2,
    type: 'diarizer',
    name: 'test-diar',
    description: '',
    abs_path: '/backend/models/test-diar',
    enabled: true,
    disable_reason: null,
    weights: [
      {
        id: 20,
        set_id: 2,
        type: 'diarizer',
        name: 'diar-weight',
        description: '',
        abs_path: '/backend/models/test-diar/diar-weight/model.bin',
        checksum: null,
        enabled: true,
        disable_reason: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ],
  },
]));

vi.mock('../services/modelRegistry', () => ({
  listModelSets: vi.fn().mockResolvedValue(mockRegistry),
  createModelSet: vi.fn(),
  updateModelSet: vi.fn(),
  deleteModelSet: vi.fn(),
  createModelWeight: vi.fn(),
  updateModelWeight: vi.fn(),
  deleteModelWeight: vi.fn(),
}));

const renderAdmin = async () => {
  let utils: ReturnType<typeof render>;
  await act(async () => {
    utils = render(<Admin />);
  });
  await screen.findByTestId('admin-advanced-settings');
  return utils!;
};

describe('Admin page', () => {
  beforeEach(() => {
    refreshSpy.mockResolvedValue(mockSystemInfo);
    mockAuthContext.user = {
      ...mockAuthContext.user,
      is_admin: true,
    };
  });

  afterEach(() => {
    refreshSpy.mockReset();
    vi.clearAllMocks();
  });

  it('renders admin sections for admins', async () => {
    await renderAdmin();
    expect(screen.getByTestId('model-registry-section')).toBeInTheDocument();
    expect(screen.getByTestId('admin-advanced-settings')).toBeInTheDocument();
    expect(screen.getByTestId('system-section')).toBeInTheDocument();
    expect(screen.getByText(/admin access granted/i)).toBeInTheDocument();
  });

  it('shows registry data and availability refresh', async () => {
    await renderAdmin();
    expect(screen.getByTestId('set-select')).toBeInTheDocument();
    expect(screen.getByTestId('weight-list')).toBeInTheDocument();
    const refreshButton = screen.getByTestId('rescan-availability');
    await act(async () => {
      fireEvent.click(refreshButton);
    });
    expect(screen.getByTestId('asr-provider-test-asr')).toBeInTheDocument();
    expect(screen.queryByTestId('availability-warnings')).not.toBeInTheDocument();
    const providerCard = screen.getByTestId('asr-provider-test-asr');
    expect(
      within(providerCard).getByText(/pending files/i, {
        selector: 'span',
      })
    ).toBeInTheDocument();
  });

  it('allows adjusting throughput slider and surfaces storage summary', async () => {
    await renderAdmin();
    await screen.findByTestId('admin-storage-summary');
    await waitFor(() => {
      expect(screen.getByTestId('default-diarizer')).toHaveAttribute('data-ready', 'true');
    });
    const slider = screen.getByTestId('max-concurrent-jobs') as HTMLInputElement;
    fireEvent.change(slider, { target: { value: '4' } });
    await waitFor(() => {
      expect(screen.getByTestId('max-concurrent-label')).toHaveTextContent('Max Concurrent Jobs: 4');
    });
    expect(screen.getByTestId('admin-storage-summary')).toBeInTheDocument();
    const saveButton = screen.getByTestId('admin-save-all');
    await act(async () => {
      fireEvent.click(saveButton);
    });
    expect(updateSettings).toHaveBeenCalled();
    const latestCall = vi.mocked(updateSettings).mock.calls.at(-1)?.[0];
    expect(latestCall?.max_concurrent_jobs ?? Number(slider.value)).toBe(4);
  });

  it('allows system detect refresh', async () => {
    await renderAdmin();
    const detectButton = screen.getByTestId('system-detect');
    await act(async () => {
      fireEvent.click(detectButton);
    });
    expect(refreshSpy).toHaveBeenCalled();
  });

  it('shows locked notice for non-admin users', async () => {
    mockAuthContext.user = {
      ...mockAuthContext.user,
      is_admin: false,
    };
    await act(async () => {
      render(<Admin />);
    });
    expect(screen.getByTestId('admin-access-guard')).toBeInTheDocument();
    expect(screen.getByTestId('admin-locked')).toBeInTheDocument();
  });
});
