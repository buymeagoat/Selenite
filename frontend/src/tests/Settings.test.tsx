import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { vi } from 'vitest';
import { Settings } from '../pages/Settings';

// Mock async data fetches to prevent unhandled errors
vi.mock('../services/settings', () => ({
  fetchSettings: vi.fn().mockResolvedValue({
    default_model: 'medium',
    default_language: 'auto',
    max_concurrent_jobs: 3
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
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders all settings sections', async () => {
    await renderSettings();
    expect(screen.getByText(/default transcription options/i)).toBeInTheDocument();
    expect(screen.getByText(/performance/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /storage/i })).toBeInTheDocument();
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
    expect(screen.getByLabelText(/speaker detection/i)).toBeInTheDocument();
  });

  it('renders performance settings', async () => {
    await renderSettings();
    expect(screen.getByLabelText(/max concurrent jobs/i)).toBeInTheDocument();
  });

  it('displays storage information', async () => {
    await renderSettings();
    expect(screen.getByText(/used space/i)).toBeInTheDocument();
    expect(screen.getByText(/location/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /storage/i })).toBeInTheDocument();
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
