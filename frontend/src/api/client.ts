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
  let normalizedPath = path.startsWith('/') ? path : `/${path}`;
  // FastAPI routes with prefix and "/" route definition need trailing slash
  // e.g., prefix="/api/products" + route="/" = /api/products/
  // Add trailing slash for collection endpoints to avoid 307 redirects
  // Only add if path doesn't already end with / and doesn't have a resource ID (like /api/products/123)
  if (!normalizedPath.endsWith('/') && 
      !normalizedPath.match(/\/\d+(\/|$)/) && // Don't add for resource IDs
      !normalizedPath.includes('?')) {
    normalizedPath = `${normalizedPath}/`;
  }
  
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
    
    // Try with redirect: 'follow' first - if it fails due to CORS on redirect,
    // the browser will block it and we'll get an error we can handle
    try {
      const response = await fetch(url, {
        method: 'GET',
        redirect: 'follow', // Let browser handle redirects
        // Don't set Content-Type for GET requests - it triggers unnecessary CORS preflight
      });

      if (!response.ok) {
        // Log more details about the error
        const errorText = await response.text().catch(() => 'Unable to read error response');
        throw new Error(`HTTP error! status: ${response.status}, url: ${url}, response: ${errorText}`);
      }

      return response.json();
    } catch (error) {
      // If fetch fails due to CORS on redirect, try without redirect following
      // This might work if the initial URL is correct
      if (error instanceof TypeError && error.message.includes('CORS')) {
        console.warn('CORS error on redirect, retrying with manual redirect handling');
        // Unfortunately, we can't manually handle redirects due to CORS restrictions
        // The backend needs to not redirect, or the redirect response needs CORS headers
        throw new Error(`CORS error: The server is redirecting but the redirect response lacks CORS headers. Please ensure the URL is correct and doesn't cause a redirect. URL: ${url}`);
      }
      throw error;
    }
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
