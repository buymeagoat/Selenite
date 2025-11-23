import React from 'react';
import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { ToastProvider, useToast } from '../context/ToastContext';

describe('ToastContext', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it('renders and auto-dismisses toast notifications', async () => {
    const Trigger: React.FC = () => {
      const { showSuccess } = useToast();
      return (
        <button onClick={() => showSuccess('Saved!')}>Trigger</button>
      );
    };

    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText(/trigger/i));
    expect(screen.getByText(/saved!/i)).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    vi.useRealTimers();
    await waitFor(() => expect(screen.queryByText(/saved!/i)).not.toBeInTheDocument());
  });

  it('provides safe no-op handlers when used without a provider', () => {
    const { result } = renderHook(() => useToast());
    expect(() => result.current.showError('oops')).not.toThrow();
    expect(() => result.current.showSuccess('done')).not.toThrow();
  });
});
