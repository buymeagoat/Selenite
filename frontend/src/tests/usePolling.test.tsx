import { renderHook } from '@testing-library/react';
import { act } from 'react';
import { vi } from 'vitest';
import { usePolling } from '../hooks/usePolling';

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it('calls function immediately on mount', async () => {
    const mockFn = vi.fn().mockResolvedValue(null);
    renderHook(() => usePolling(mockFn, { enabled: true }));
    
    // Flush promises
    await act(async () => {
      await Promise.resolve();
    });
    
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  it('calls function repeatedly at interval', async () => {
    const mockFn = vi.fn().mockResolvedValue(null);
    renderHook(() => usePolling(mockFn, { interval: 1000 }));
    
    await act(async () => {
      await Promise.resolve();
    });
    expect(mockFn).toHaveBeenCalledTimes(1);
    
    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });
    expect(mockFn).toHaveBeenCalledTimes(2);
    
    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });
    expect(mockFn).toHaveBeenCalledTimes(3);
  });

  it('does not call function when enabled is false', async () => {
    const mockFn = vi.fn().mockResolvedValue(null);
    renderHook(() => usePolling(mockFn, { enabled: false }));
    
    await act(async () => {
      vi.advanceTimersByTime(5000);
      await Promise.resolve();
    });
    
    expect(mockFn).not.toHaveBeenCalled();
  });

  it('stops polling when unmounted', async () => {
    const mockFn = vi.fn().mockResolvedValue(null);
    const { unmount } = renderHook(() => usePolling(mockFn));
    
    await act(async () => {
      await Promise.resolve();
    });
    expect(mockFn).toHaveBeenCalledTimes(1);
    
    unmount();
    
    await act(async () => {
      vi.advanceTimersByTime(5000);
      await Promise.resolve();
    });
    
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  it('calls onError when function throws', async () => {
    const error = new Error('Test error');
    const mockFn = vi.fn().mockRejectedValue(error);
    const handleError = vi.fn();
    
    renderHook(() => usePolling(mockFn, { onError: handleError }));
    
    await act(async () => {
      await Promise.resolve();
    });
    
    expect(handleError).toHaveBeenCalledWith(error);
  });

  it('continues polling after error', async () => {
    let callCount = 0;
    const mockFn = vi.fn().mockImplementation(() => {
      callCount++;
      if (callCount === 1) return Promise.reject(new Error('First call fails'));
      return Promise.resolve();
    });
    
    renderHook(() => usePolling(mockFn, { interval: 500, onError: vi.fn() }));
    
    await act(async () => {
      await Promise.resolve();
    });
    expect(mockFn).toHaveBeenCalledTimes(1);
    
    await act(async () => {
      vi.advanceTimersByTime(500);
      await Promise.resolve();
    });
    expect(mockFn).toHaveBeenCalledTimes(2);
  });

  it('updates when function reference changes', async () => {
    const mockFn1 = vi.fn().mockResolvedValue('first');
    const mockFn2 = vi.fn().mockResolvedValue('second');
    
    const { rerender } = renderHook(
      ({ fn }) => usePolling(fn, { interval: 1000 }),
      { initialProps: { fn: mockFn1 } }
    );
    
    await act(async () => {
      await Promise.resolve();
    });
    expect(mockFn1).toHaveBeenCalled();
    
    // Rerender updates the ref but doesn't restart the poll cycle immediately
    rerender({ fn: mockFn2 });
    
    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });
    
    // mockFn2 should be called on the next interval
    expect(mockFn2).toHaveBeenCalled();
  });

  it('updates when enabled changes from false to true', async () => {
    const mockFn = vi.fn().mockResolvedValue(null);
    
    const { rerender } = renderHook(
      ({ enabled }) => usePolling(mockFn, { enabled }),
      { initialProps: { enabled: false } }
    );
    
    await act(async () => {
      vi.advanceTimersByTime(3000);
      await Promise.resolve();
    });
    expect(mockFn).not.toHaveBeenCalled();
    
    await act(async () => {
      rerender({ enabled: true });
      await Promise.resolve();
    });
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  it('stops polling when enabled changes from true to false', async () => {
    const mockFn = vi.fn().mockResolvedValue(null);
    
    const { rerender } = renderHook(
      ({ enabled }) => usePolling(mockFn, { enabled }),
      { initialProps: { enabled: true } }
    );
    
    await act(async () => {
      await Promise.resolve();
    });
    expect(mockFn).toHaveBeenCalledTimes(1);
    
    // Disable polling
    rerender({ enabled: false });
    
    await act(async () => {
      vi.advanceTimersByTime(5000);
      await Promise.resolve();
    });
    
    // Should still only have been called once (no new calls after disabling)
    expect(mockFn).toHaveBeenCalledTimes(1);
  });
});
