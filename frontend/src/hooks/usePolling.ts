import { useEffect, useRef } from 'react';

interface UsePollingOptions {
  enabled?: boolean;
  interval?: number;
  onError?: (error: Error) => void;
}

/**
 * Hook for polling an async function at regular intervals
 * @param fn - The async function to call repeatedly
 * @param options - Configuration options
 */
export const usePolling = <T,>(
  fn: () => Promise<T>,
  options: UsePollingOptions = {}
): void => {
  const { enabled = true, interval = 2000, onError } = options;
  const savedCallback = useRef(fn);
  const savedErrorHandler = useRef(onError);
  const timerRef = useRef<number | null>(null);

  // Update refs when deps change
  useEffect(() => {
    savedCallback.current = fn;
  }, [fn]);

  useEffect(() => {
    savedErrorHandler.current = onError;
  }, [onError]);

  useEffect(() => {
    if (!enabled) {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    const poll = async () => {
      try {
        await savedCallback.current();
      } catch (error) {
        if (savedErrorHandler.current) {
          savedErrorHandler.current(error as Error);
        }
      }
      // Schedule next poll
      timerRef.current = window.setTimeout(poll, interval);
    };

    // Start polling
    poll();

    // Cleanup
    return () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [enabled, interval]);
};
