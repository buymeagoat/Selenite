/**
 * API Client Utilities
 * 
 * Base fetch wrapper with authentication, error handling, and standardized responses.
 */

const envApiBase = import.meta.env.VITE_API_URL?.trim();

let defaultApiBase = 'http://localhost:8100';
if (typeof window !== 'undefined') {
  const protocol = window.location?.protocol || 'http:';
  const hostname = window.location?.hostname || 'localhost';
  defaultApiBase = `${protocol}//${hostname}:8100`;
}

export const API_BASE_URL =
  envApiBase && envApiBase.length > 0 ? envApiBase : defaultApiBase;

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

  try {
    const response = await fetch(url, {
      ...options,
      headers,
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
