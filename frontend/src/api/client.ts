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
  // FastAPI routes with prefix="/api/products" and route="/" need trailing slash: /api/products/
  // Add trailing slash for collection list endpoints to avoid 307 redirects
  // Check if this is a collection endpoint (ends with /api/products, /api/jobs, /api/webhooks, etc.)
  const isCollectionEndpoint = /^\/api\/(products|jobs|webhooks|uploads)(\/.*)?$/.test(normalizedPath);
  if (isCollectionEndpoint && !normalizedPath.endsWith('/') && !normalizedPath.match(/\/\d+/)) {
    // Add trailing slash for collection endpoints without resource IDs
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
    
    // Debug: log the URL being requested (always log for debugging)
    console.log('[API Client] Fetching URL:', url);
    
    try {
      // Add timeout to prevent blocking (10 seconds)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);
      
      const response = await fetch(url, {
        method: 'GET',
        redirect: 'follow', // Let browser handle redirects
        signal: controller.signal,
        // Don't set Content-Type for GET requests - it triggers unnecessary CORS preflight
      });
      
      clearTimeout(timeoutId);

      console.log('[API Client] Response status:', response.status, 'URL:', url);

      if (!response.ok) {
        // Log more details about the error
        const errorText = await response.text().catch(() => 'Unable to read error response');
        const errorMessage = `HTTP error! status: ${response.status}, url: ${url}`;
        console.error('[API Client]', errorMessage, errorText);
        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log('[API Client] Success:', url);
      return data;
    } catch (error) {
      // Handle abort/timeout
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Request timeout: ${url} took longer than 10 seconds`);
      }
      // Provide more detailed error information
      console.error('[API Client] Error details:', {
        error,
        url,
        errorType: error instanceof Error ? error.constructor.name : typeof error,
        errorMessage: error instanceof Error ? error.message : String(error),
      });
      
      if (error instanceof TypeError) {
        // Network error or CORS error
        if (error.message.includes('Failed to fetch') || error.message.includes('network')) {
          const errorMessage = `Network error: Unable to fetch ${url}. Check CORS configuration and network connectivity.`;
          throw new Error(errorMessage);
        }
        if (error.message.includes('CORS')) {
          const errorMessage = `CORS error: Request to ${url} was blocked. Check backend CORS_ORIGINS configuration.`;
          throw new Error(errorMessage);
        }
      }
      
      // Re-throw with more context
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(`Unknown error fetching ${url}: ${String(error)}`);
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
