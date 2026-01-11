import { devInfo, devWarn } from './debug';

/**
 * API Client Utilities
 * 
 * Base fetch wrapper with authentication, error handling, and standardized responses.
 */

const envApiBase = import.meta.env.VITE_API_URL?.trim();

const LOOPBACK_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '::1'];

const getRuntimeHostInfo = () => {
  if (typeof window === 'undefined') {
    return {
      protocol: 'http:',
      hostname: 'localhost'
    };
  }

  return {
    protocol: window.location?.protocol || 'http:',
    hostname: window.location?.hostname || 'localhost'
  };
};

const isLoopbackHost = (host?: string | null) => {
  if (!host) {
    return false;
  }
  const normalized = host.toLowerCase();
  return (
    LOOPBACK_HOSTS.includes(normalized) ||
    normalized.startsWith('127.')
  );
};

const parseUrl = (value?: string | null): URL | null => {
  if (!value || value.length === 0) {
    return null;
  }
  try {
    return new URL(value);
  } catch (error) {
    devWarn('[API CONFIG] Invalid VITE_API_URL provided; falling back to runtime host.', {
      provided: value,
      error: error instanceof Error ? error.message : 'unknown'
    });
    return null;
  }
};

const runtimeHostInfo = getRuntimeHostInfo();
const runtimeApiPort = import.meta.env.VITE_API_PORT?.trim() || '8201';
const runtimeApiBase = `${runtimeHostInfo.protocol}//${runtimeHostInfo.hostname}:${runtimeApiPort}`;
const envApiUrl = parseUrl(envApiBase);

let resolvedApiBase = (envApiBase && envApiBase.length > 0)
  ? envApiBase
  : runtimeApiBase;

if (envApiUrl && typeof window !== 'undefined') {
  const envIsLoopback = isLoopbackHost(envApiUrl.hostname);
  const runtimeIsLoopback = isLoopbackHost(runtimeHostInfo.hostname);

  if (envIsLoopback && !runtimeIsLoopback) {
    // If the bundle was built with a loopback API base but the browser is remote, prefer the runtime host.
    devWarn('[API CONFIG] Remote browser detected but VITE_API_URL points to loopback; defaulting to runtime host.', {
      envApiBase,
      runtimeApiBase
    });
    resolvedApiBase = runtimeApiBase;
  }
}

export const API_BASE_URL = resolvedApiBase;

// Log API configuration on load (dev only)
devInfo('[API CONFIG]', {
  envApiBase,
  runtimeApiBase,
  envHost: envApiUrl?.hostname ?? null,
  runtimeHost: runtimeHostInfo.hostname,
  envIsLoopback: envApiUrl ? isLoopbackHost(envApiUrl.hostname) : null,
  runtimeIsLoopback: isLoopbackHost(runtimeHostInfo.hostname),
  API_BASE_URL,
  userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
  timestamp: new Date().toISOString()
});

export class ApiError extends Error {
  status: number;
  data?: any;

  constructor(
    message: string,
    status: number,
    data?: any
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Get authentication token from localStorage
 */
function getAuthToken(): string | null {
  return localStorage.getItem('auth_token');
}

/**
 * Base fetch wrapper with authentication and error handling
 */
function handleUnauthorized() {
  try {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
  } catch {
    // Ignore storage errors
  }

  if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  const startTime = Date.now();
  const requestId = Math.random().toString(36).substring(7);

  devInfo(`[API REQUEST ${requestId}]`, {
    method: options.method || 'GET',
    url,
    endpoint,
    hasToken: !!token,
    hasBody: Boolean(options.body),
    timestamp: new Date().toISOString()
  });

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    const duration = Date.now() - startTime;
    devInfo(`[API RESPONSE ${requestId}]`, {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok,
      duration: `${duration}ms`,
      timestamp: new Date().toISOString()
    });

    // Handle non-OK responses
    if (!response.ok) {
      let errorData: any;
      try {
        errorData = await response.json();
      } catch {
        errorData = { detail: response.statusText };
      }

      const errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}`;
      if (response.status === 401) {
        handleUnauthorized();
      }
      throw new ApiError(errorMessage, response.status, errorData);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    // Parse JSON response
    const data = await response.json();
    return data as T;
  } catch (error) {
    const duration = Date.now() - startTime;
    devWarn(`[API ERROR ${requestId}]`, {
      endpoint,
      url,
      duration: `${duration}ms`,
      error: error instanceof Error ? {
        name: error.name,
        message: error.message,
        stack: error.stack
      } : error,
      errorType: error instanceof ApiError ? 'ApiError' : error instanceof Error ? 'Error' : 'Unknown',
      timestamp: new Date().toISOString()
    });

    if (error instanceof ApiError) {
      throw error;
    }

    // Network or other errors
    if (error instanceof Error) {
      throw new ApiError(error.message, 0);
    }

    throw new ApiError('Unknown error occurred', 0);
  }
}

/**
 * GET request helper
 */
export async function apiGet<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
  let url = endpoint;
  
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value));
      }
    });
    
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  return apiFetch<T>(url, { method: 'GET' });
}

/**
 * POST request helper
 */
export async function apiPost<T>(endpoint: string, data?: any): Promise<T> {
  return apiFetch<T>(endpoint, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });
}

/**
 * PUT request helper
 */
export async function apiPut<T>(endpoint: string, data: any): Promise<T> {
  return apiFetch<T>(endpoint, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/**
 * PATCH request helper
 */
export async function apiPatch<T>(endpoint: string, data: any): Promise<T> {
  return apiFetch<T>(endpoint, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * DELETE request helper
 */
export async function apiDelete<T>(endpoint: string): Promise<T> {
  return apiFetch<T>(endpoint, { method: 'DELETE' });
}

/**
 * Upload file with FormData
 */
export async function apiUpload<T>(endpoint: string, formData: FormData): Promise<T> {
  const token = getAuthToken();
  
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      let errorData: any;
      try {
        errorData = await response.json();
      } catch {
        errorData = { detail: response.statusText };
      }

      const errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}`;
      throw new ApiError(errorMessage, response.status, errorData);
    }

    const data = await response.json();
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof Error) {
      throw new ApiError(error.message, 0);
    }

    throw new ApiError('Unknown error occurred', 0);
  }
}

/**
 * Fetch binary content with authentication.
 */
export async function apiFetchBlob(endpoint: string): Promise<Blob> {
  const token = getAuthToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, { method: 'GET', headers });
  if (!response.ok) {
    let errorData: any;
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: response.statusText };
    }
    const errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}`;
    throw new ApiError(errorMessage, response.status, errorData);
  }
  return response.blob();
}

