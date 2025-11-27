// Central HTTP client configuration (fetch/axios) used across hooks.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

/**
 * Builds a URL with query parameters
 * Uses relative paths in development (to go through Vite proxy)
 * Uses absolute URLs in production when VITE_API_BASE_URL is set
 */
function buildUrl(path: string, params?: Record<string, unknown>): string {
  // If no API_BASE_URL is set, use relative paths (goes through Vite proxy)
  if (!API_BASE_URL) {
    let url = path;
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
      const queryString = searchParams.toString();
      if (queryString) {
        url += (url.includes('?') ? '&' : '?') + queryString;
      }
    }
    return url;
  }
  
  // Use absolute URL when API_BASE_URL is explicitly set
  const url = new URL(path, API_BASE_URL);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    });
  }
  return url.toString();
}

/**
 * Central HTTP client for API requests
 */
export const apiClient = {
  get: async <T>(path: string, params?: Record<string, unknown>): Promise<T> => {
    const url = buildUrl(path, params);
    const response = await fetch(url, {
      method: 'GET',
      // Don't set Content-Type for GET requests - it triggers unnecessary CORS preflight
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  post: async <T>(path: string, body?: unknown): Promise<T> => {
    const url = buildUrl(path);
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  put: async <T>(path: string, body?: unknown): Promise<T> => {
    const url = buildUrl(path);
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  delete: async <T>(path: string): Promise<T> => {
    const url = buildUrl(path);
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // DELETE might return 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  },

  /**
   * Upload file (multipart/form-data)
   */
  upload: async <T>(path: string, file: File): Promise<T> => {
    const url = buildUrl(path);
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },
};
