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
        // Filter out undefined, null, and empty strings
        if (value !== undefined && value !== null && value !== '') {
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
  // Ensure API_BASE_URL doesn't have trailing slash
  const baseUrl = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  
  // Build query string manually to avoid URL constructor issues
  const queryParts: string[] = [];
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      // Filter out undefined, null, and empty strings
      if (value !== undefined && value !== null && value !== '') {
        queryParts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
      }
    });
  }
  
  const queryString = queryParts.length > 0 ? `?${queryParts.join('&')}` : '';
  return `${baseUrl}${normalizedPath}${queryString}`;
}

/**
 * Central HTTP client for API requests
 */
export const apiClient = {
  get: async <T>(path: string, params?: Record<string, unknown>): Promise<T> => {
    const url = buildUrl(path, params);
    
    // Debug: log the URL being requested (remove in production if needed)
    if (import.meta.env.DEV) {
      console.log('Fetching URL:', url);
    }
    
    const response = await fetch(url, {
      method: 'GET',
      redirect: 'follow', // Explicitly follow redirects
      // Don't set Content-Type for GET requests - it triggers unnecessary CORS preflight
    });

    if (!response.ok) {
      // Log more details about the error
      const errorText = await response.text().catch(() => 'Unable to read error response');
      throw new Error(`HTTP error! status: ${response.status}, url: ${url}, response: ${errorText}`);
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
