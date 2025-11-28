import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { Settings } from '../pages/Settings';

// Mock async data fetches to prevent unhandled errors
vi.mock('../services/settings', () => ({
  fetchSettings: vi.fn().mockResolvedValue({
    default_model: 'medium',
    default_language: 'auto',
    default_diarizer: 'vad',
    diarization_enabled: false,
    allow_job_overrides: false,
    max_concurrent_jobs: 3
  }),
  updateSettings: vi.fn().mockResolvedValue({})
}));
vi.mock('../services/tags', () => ({
  fetchTags: vi.fn().mockResolvedValue({ items: [] }),
  deleteTag: vi.fn().mockResolvedValue({ jobs_affected: 0 })
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
    project: { path: '/tmp/project', total_gb: 300, used_gb: 50, free_gb: 250 }
  },
  network: { hostname: 'selenite-host', interfaces: [{ name: 'eth0', ipv4: ['192.168.1.50'] }] },
  runtime: { python: '3.11.0', node: 'v20.10.0' },
  container: { is_container: false, indicators: [] },
  recommendation: { suggested_asr_model: 'large-v3', suggested_diarization: 'pyannote', basis: ['mock'] }
}));

const refreshSpy = vi.hoisted(() => vi.fn());
const mockCapabilities = vi.hoisted(() => ({
  asr: [{ provider: 'whisper', display_name: 'Whisper', available: true, models: ['tiny'], notes: [] }],
  diarizers: [
    { key: 'whisperx', display_name: 'WhisperX', requires_gpu: true, available: true, notes: [] },
    { key: 'pyannote', display_name: 'Pyannote', requires_gpu: true, available: false, notes: ['GPU required'] },
    { key: 'vad', display_name: 'VAD + clustering', requires_gpu: false, available: true, notes: [] }
  ]
}));

vi.mock('../services/system', () => ({
  fetchSystemInfo: vi.fn().mockResolvedValue(mockSystemInfo),
  refreshSystemInfo: refreshSpy,
  fetchCapabilities: vi.fn().mockResolvedValue(mockCapabilities)
}));

refreshSpy.mockResolvedValue(mockSystemInfo);

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
  await screen.findByText(/account/i);
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
    refreshSpy.mockResolvedValue(mockSystemInfo);
  });

  afterEach(() => {
    refreshSpy.mockReset();
  });

  it('renders all settings sections', async () => {
    await renderSettings();
    expect(screen.getByText(/default transcription options/i)).toBeInTheDocument();
    expect(screen.getByText(/performance/i)).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { name: /storage/i }).length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: /tags/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /system/i })).toBeInTheDocument();
  });

  it('renders change password form', async () => {
    await renderSettings();
    expect(screen.getByLabelText(/current password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
  });

  it('renders default transcription options', async () => {
    await renderSettings();
    expect(screen.getByLabelText(/default model/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/default language/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/timestamps/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/enable diarization/i)).toBeInTheDocument();
  });

  it('renders performance settings', async () => {
    await renderSettings();
    expect(screen.getByLabelText(/max concurrent jobs/i)).toBeInTheDocument();
  });

  it('displays storage information', async () => {
    await renderSettings();
    expect(screen.getByText(/used space/i)).toBeInTheDocument();
    expect(screen.getByText(/location/i)).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { name: /storage/i }).length).toBeGreaterThan(0);
  });

  it('renders tag list section', async () => {
    await renderSettings();
    expect(screen.getByRole('heading', { name: /tags/i })).toBeInTheDocument();
  });

  it('renders system control buttons', async () => {
    await renderSettings();
    expect(screen.getByRole('button', { name: /restart server/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /shutdown server/i })).toBeInTheDocument();
  });

  it('shows system probe information and detect button', async () => {
    await renderSettings();
    expect(screen.getByTestId('system-section')).toBeInTheDocument();
    expect(screen.getByTestId('system-gpu')).toBeInTheDocument();
    expect(screen.getByText(/selenite-host/i)).toBeInTheDocument();
    const detectButton = screen.getByTestId('system-detect');
    await clickButton(detectButton);
    expect(refreshSpy).toHaveBeenCalled();
  });

  it('renders diarization controls', async () => {
    await renderSettings();
    const toggle = screen.getByLabelText(/enable diarization/i) as HTMLInputElement;
    expect(toggle).toBeInTheDocument();
    const select = screen.getByTestId('default-diarizer') as HTMLSelectElement;
    expect(select).toBeDisabled();
  });

  it('submits password change form', async () => {
    await renderSettings();
    const currentPw = screen.getByLabelText(/current password/i);
    const newPw = screen.getByLabelText(/new password/i);
    const confirmPw = screen.getByLabelText(/confirm password/i);
    await changeField(currentPw, 'oldpass');
    await changeField(newPw, 'newpass123');
    await changeField(confirmPw, 'newpass123');
    const saveBtn = screen.getAllByRole('button', { name: /save/i })[0];
    await clickButton(saveBtn);
  });

  it('saves default transcription options', async () => {
    await renderSettings();
    const modelSelect = screen.getByLabelText(/default model/i);
    await changeField(modelSelect, 'large');
    const saveBtn = screen.getAllByRole('button', { name: /save/i })[1];
    await clickButton(saveBtn);
  });

  it('adjusts max concurrent jobs slider', async () => {
    await renderSettings();
    const slider = screen.getByLabelText(/max concurrent jobs/i) as HTMLInputElement;
    await changeField(slider, '3');
    expect(slider.value).toBe('3');
  });
});
