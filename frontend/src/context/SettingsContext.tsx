/* eslint-disable react-refresh/only-export-components */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  type ReactNode,
} from 'react';
import { fetchSettings, type UserSettings } from '../services/settings';
import { devInfo, devWarn } from '../lib/debug';

export type SettingsStatus = 'loading' | 'ready' | 'error';

interface SettingsState {
  status: SettingsStatus;
  settings: UserSettings | null;
  error: string | null;
  isRefreshing: boolean;
}

interface SettingsAction {
  type: 'start-loading' | 'start-refreshing' | 'set-success' | 'set-error';
  payload?: UserSettings | string | null;
}

export interface SettingsContextValue {
  status: SettingsStatus;
  settings: UserSettings | null;
  error: string | null;
  isRefreshing: boolean;
  refresh: (options?: { force?: boolean }) => Promise<void>;
}

interface CachedSettings {
  version: number;
  fetchedAt: number;
  data: UserSettings;
}

interface SettingsProviderProps {
  children: ReactNode;
  fetcher?: typeof fetchSettings;
  cacheKey?: string;
  timeoutMs?: number;
}

const SETTINGS_CACHE_KEY = 'selenite_admin_settings_v1';
const FETCH_TIMEOUT_MS = 7000;

export const SettingsContext = createContext<SettingsContextValue | undefined>(undefined);

type DebugEvent =
  | { type: 'init'; hasCache: boolean; source: string }
  | { type: 'fetch-start'; hasCachedData: boolean }
  | { type: 'fetch-success'; fromCache: boolean }
  | { type: 'fetch-error'; message: string };

function recordDebugEvent(event: DebugEvent) {
  try {
    const globalObj = window as Window & {
      __SELENITE_SETTINGS_DEBUG__?: DebugEvent[];
    };
    if (!globalObj.__SELENITE_SETTINGS_DEBUG__) {
      globalObj.__SELENITE_SETTINGS_DEBUG__ = [];
    }
    globalObj.__SELENITE_SETTINGS_DEBUG__.push(event);
  } catch {
    // ignore if window not available
  }
  const tag = '[settings-store]';
  switch (event.type) {
    case 'init':
      devInfo(`${tag} init`, event);
      break;
    case 'fetch-start':
      devInfo(`${tag} fetch start`, event);
      break;
    case 'fetch-success':
      devInfo(`${tag} fetch success`, event);
      break;
    case 'fetch-error':
      devWarn(`${tag} fetch error`, event.message);
      break;
    default:
      break;
  }
}

function loadCachedSettings(cacheKey: string): UserSettings | null {
  try {
    const raw = localStorage.getItem(cacheKey);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as CachedSettings;
    if (parsed.version !== 1 || !parsed.data) {
      return null;
    }
    return parsed.data;
  } catch {
    return null;
  }
}

function persistSettings(cacheKey: string, data: UserSettings) {
  try {
    const payload: CachedSettings = {
      version: 1,
      fetchedAt: Date.now(),
      data,
    };
    localStorage.setItem(cacheKey, JSON.stringify(payload));
  } catch {
    // Ignore storage errors (quota, private mode, etc.)
  }
}

function settingsReducer(state: SettingsState, action: SettingsAction): SettingsState {
  switch (action.type) {
    case 'start-loading':
      return {
        ...state,
        status: state.settings ? 'ready' : 'loading',
        isRefreshing: true,
        error: null,
      };
    case 'start-refreshing':
      return {
        ...state,
        isRefreshing: true,
        error: null,
      };
    case 'set-success':
      return {
        status: 'ready',
        settings: action.payload as UserSettings,
        error: null,
        isRefreshing: false,
      };
    case 'set-error': {
      const message = (action.payload as string) || 'Failed to load settings';
      const hasData = Boolean(state.settings);
      return {
        ...state,
        status: hasData ? 'ready' : 'error',
        error: message,
        isRefreshing: false,
      };
    }
    default:
      return state;
  }
}

export const SettingsProvider: React.FC<SettingsProviderProps> = ({
  children,
  fetcher = fetchSettings,
  cacheKey = SETTINGS_CACHE_KEY,
  timeoutMs = FETCH_TIMEOUT_MS,
}) => {
  const cached = loadCachedSettings(cacheKey);
  recordDebugEvent({ type: 'init', hasCache: Boolean(cached), source: cacheKey });
  const [state, dispatch] = useReducer(settingsReducer, {
    status: cached ? 'ready' : 'loading',
    settings: cached,
    error: null,
    isRefreshing: false,
  });

  const inflightRef = useRef<{
    controller: AbortController;
    promise: Promise<void>;
  } | null>(null);

  const refresh = useCallback(
    async (options?: { force?: boolean }) => {
      if (inflightRef.current && !options?.force) {
        return inflightRef.current.promise;
      }

      const controller = new AbortController();
      const timer = window.setTimeout(() => controller.abort(), timeoutMs);
      recordDebugEvent({ type: 'fetch-start', hasCachedData: Boolean(state.settings) });

      const hasData = Boolean(state.settings);
      dispatch({ type: hasData ? 'start-refreshing' : 'start-loading' });

      const request = (async () => {
        try {
          const data = await fetcher({ signal: controller.signal });
          dispatch({ type: 'set-success', payload: data });
          persistSettings(cacheKey, data);
          recordDebugEvent({ type: 'fetch-success', fromCache: false });
          window.dispatchEvent(
            new CustomEvent('selenite:settings-updated', {
              detail: { source: 'settings-store' },
            })
          );
        } catch (error) {
          let message = controller.signal.aborted
            ? 'Settings request timed out'
            : 'Failed to load settings';
          if (error instanceof Error && error.message) {
            message = error.message;
          }
          dispatch({ type: 'set-error', payload: message });
          recordDebugEvent({ type: 'fetch-error', message });
        } finally {
          window.clearTimeout(timer);
          if (inflightRef.current?.controller === controller) {
            inflightRef.current = null;
          }
        }
      })();

      inflightRef.current = { controller, promise: request };
      return request;
    },
    [cacheKey, fetcher, state.settings, timeoutMs]
  );

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const custom = event as CustomEvent<{ source?: string } | undefined>;
      if (custom.detail?.source === 'settings-store') {
        return;
      }
      refresh({ force: true });
    };
    window.addEventListener('selenite:settings-updated', handler as EventListener);
    return () => {
      window.removeEventListener('selenite:settings-updated', handler as EventListener);
    };
  }, [refresh]);

  const value = useMemo<SettingsContextValue>(
    () => ({
      status: state.status,
      settings: state.settings,
      error: state.error,
      isRefreshing: state.isRefreshing,
      refresh,
    }),
    [state, refresh]
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
};

export function useAdminSettings(): SettingsContextValue {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useAdminSettings must be used within a SettingsProvider');
  }
  return context;
}
