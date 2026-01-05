import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SettingsProvider, useAdminSettings } from '../context/SettingsContext';
import type { UserSettings } from '../services/settings';

const mockSettings: UserSettings = {
  default_asr_provider: 'whisper',
  default_model: 'medium',
  default_language: 'auto',
  default_diarizer_provider: 'pyannote',
  default_diarizer: 'vad',
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
  last_selected_asr_set: 'whisper',
  last_selected_diarizer_set: 'pyannote',
};

const TestConsumer: React.FC = () => {
  const { status, settings, error, refresh } = useAdminSettings();
  return (
    <div>
      <div data-testid="status">{status}</div>
      <div data-testid="model">{settings?.default_model ?? 'none'}</div>
      <div data-testid="error">{error ?? ''}</div>
      <button data-testid="refresh" onClick={() => refresh()}>
        refresh
      </button>
    </div>
  );
};

describe('SettingsProvider', () => {
  const cacheKey = 'test_settings_cache';

  beforeEach(() => {
    localStorage.removeItem(cacheKey);
  });

  it('loads settings via fetcher and exposes them to consumers', async () => {
    const fetcher = vi.fn().mockResolvedValue(mockSettings);
    render(
      <SettingsProvider fetcher={fetcher} cacheKey={cacheKey}>
        <TestConsumer />
      </SettingsProvider>
    );

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('ready'));
    expect(screen.getByTestId('model').textContent).toBe('medium');
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('surfaces errors when fetch fails and no cache exists', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('boom'));
    render(
      <SettingsProvider fetcher={fetcher} cacheKey={cacheKey}>
        <TestConsumer />
      </SettingsProvider>
    );

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('error'));
    expect(screen.getByTestId('error').textContent).toContain('boom');
  });

  it('hydrates from cache synchronously before refresh completes', async () => {
    const cached = {
      version: 1,
      fetchedAt: Date.now(),
      data: mockSettings,
    };
    localStorage.setItem(cacheKey, JSON.stringify(cached));
    const fetcher = vi.fn().mockResolvedValue({
      ...mockSettings,
      default_model: 'large',
    });

    render(
      <SettingsProvider fetcher={fetcher} cacheKey={cacheKey}>
        <TestConsumer />
      </SettingsProvider>
    );

    // Cached value should be visible immediately
    expect(screen.getByTestId('model').textContent).toBe('medium');

    await waitFor(() => expect(screen.getByTestId('model').textContent).toBe('large'));
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('surfaces timeout errors when fetch aborts', async () => {
    const fetcher = vi.fn(
      ({ signal }: { signal?: AbortSignal } = {}) =>
        new Promise<UserSettings>((_resolve, reject) => {
          signal?.addEventListener('abort', () =>
            reject(new DOMException('Aborted', 'AbortError'))
          );
        })
    );
    render(
      <SettingsProvider fetcher={fetcher} cacheKey={cacheKey} timeoutMs={10}>
        <TestConsumer />
      </SettingsProvider>
    );

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('error'));
    expect(screen.getByTestId('error').textContent).toContain('timed out');
  });
});
