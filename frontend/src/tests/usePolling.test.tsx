import { renderHook, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { usePolling } from '../hooks/usePolling';

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it('calls function immediately on mount', async () => {
    const mockFn = vi.fn().mockResolvedValue(null);
    renderHook(() => usePolling(mockFn, { enabled: true }));
    await waitFor(() => expect(mockFn).toHaveBeenCalledTimes(1));
  });

  it('calls function repeatedly at interval', async () => {
    const mockFn = vi.fn().mockResolvedValue(null);
    renderHook(() => usePolling(mockFn, { interval: 1000 }));
    
    await waitFor(() => expect(mockFn).toHaveBeenCalledTimes(1));
    
    vi.advanceTimersByTime(1000);
    await waitFor(() => expect(mockFn).toHaveBeenCalledTimes(2));
    
    vi.advanceTimersByTime(1000);
    await waitFor(() => expect(mockFn).toHaveBeenCalledTimes(3));
  });

  it('does not call function when enabled is false', async () => {
    const mockFn = vi.fn().mockResolvedValue(null);
    renderHook(() => usePolling(mockFn, { enabled: false }));
    
    vi.advanceTimersByTime(5000);
    expect(mockFn).not.toHaveBeenCalled();
  });

  it('stops polling when unmounted', async () => {
    const mockFn = vi.fn().mockResolvedValue(null);
    const { unmount } = renderHook(() => usePolling(mockFn));
    
    await waitFor(() => expect(mockFn).toHaveBeenCalledTimes(1));
    
    unmount();
    
    vi.advanceTimersByTime(5000);
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  it('calls onError when function throws', async () => {
    const error = new Error('Test error');
    const mockFn = vi.fn().mockRejectedValue(error);
    const handleError = vi.fn();
    
    renderHook(() => usePolling(mockFn, { onError: handleError }));
    
    await waitFor(() => expect(handleError).toHaveBeenCalledWith(error));
  });

  it('continues polling after error', async () => {
    let callCount = 0;
    const mockFn = vi.fn().mockImplementation(() => {
      callCount++;
      if (callCount === 1) return Promise.reject(new Error('First call fails'));
      return Promise.resolve();
    });
    
    renderHook(() => usePolling(mockFn, { interval: 500, onError: vi.fn() }));
    
    await waitFor(() => expect(mockFn).toHaveBeenCalledTimes(1));
    
    vi.advanceTimersByTime(500);
    await waitFor(() => expect(mockFn).toHaveBeenCalledTimes(2));
  });

  it('updates when function reference changes', async () => {
    const mockFn1 = vi.fn().mockResolvedValue('first');
    const mockFn2 = vi.fn().mockResolvedValue('second');
    
    const { rerender } = renderHook(
      ({ fn }) => usePolling(fn, { interval: 1000 }),
      { initialProps: { fn: mockFn1 } }
    );
    
    await waitFor(() => expect(mockFn1).toHaveBeenCalled());
    
    rerender({ fn: mockFn2 });
    vi.advanceTimersByTime(1000);
    
    await waitFor(() => expect(mockFn2).toHaveBeenCalled());
  });

  it('updates when enabled changes from false to true', async () => {
    const mockFn = vi.fn().mockResolvedValue(null);
    
    const { rerender } = renderHook(
      ({ enabled }) => usePolling(mockFn, { enabled }),
      { initialProps: { enabled: false } }
    );
    
    vi.advanceTimersByTime(3000);
    expect(mockFn).not.toHaveBeenCalled();
    
    rerender({ enabled: true });
    await waitFor(() => expect(mockFn).toHaveBeenCalledTimes(1));
  });

  it('stops polling when enabled changes from true to false', async () => {
    const mockFn = vi.fn().mockResolvedValue(null);
    
    const { rerender } = renderHook(
      ({ enabled }) => usePolling(mockFn, { enabled }),
      { initialProps: { enabled: true } }
    );
    
    await waitFor(() => expect(mockFn).toHaveBeenCalledTimes(1));
    
    rerender({ enabled: false });
    vi.advanceTimersByTime(5000);
    
    expect(mockFn).toHaveBeenCalledTimes(1);
  });
});
