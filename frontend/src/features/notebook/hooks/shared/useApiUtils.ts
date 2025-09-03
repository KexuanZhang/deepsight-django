import { useCallback } from 'react';
import { config } from "@/config";

/**
 * Shared API utilities hook
 * Provides common functionality used across multiple hooks:
 * - CSRF token management
 * - API response handling
 * - Error handling
 * - Authentication checks
 */
export const useApiUtils = () => {
  /**
   * Get CSRF token from cookies
   * @param name - Cookie name (defaults to 'csrftoken')
   * @returns CSRF token string or null if not found
   */
  const getCsrfToken = useCallback((name: string = 'csrftoken'): string | null => {
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match && match[2] ? decodeURIComponent(match[2]) : null;
  }, []);

  /**
   * Prime CSRF token by making a request to the CSRF endpoint
   * This ensures the token is available for subsequent requests
   */
  const primeCsrfToken = useCallback(async (): Promise<void> => {
    try {
      await fetch(`${config.API_BASE_URL}/users/csrf/`, {
        method: "GET",
        credentials: "include",
      });
    } catch (error) {
      console.error('Failed to prime CSRF token:', error);
    }
  }, []);

  /**
   * Handle API response with proper error handling
   * @param response - Fetch Response object
   * @returns Parsed JSON data or throws error
   */
  const handleApiResponse = useCallback(async <T>(response: Response): Promise<T> => {
    if (response.status === 401) {
      throw new Error('Unauthorized - Please log in again');
    }
    
    if (response.status === 404) {
      throw new Error('Resource not found');
    }

    if (response.status === 403) {
      throw new Error('Access denied');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }, []);

  /**
   * Make authenticated API request with CSRF token
   * @param url - API endpoint URL
   * @param options - Fetch options
   * @returns Promise with parsed response data
   */
  const authenticatedRequest = useCallback(async <T>(
    url: string, 
    options: RequestInit = {}
  ): Promise<T> => {
    const csrfToken = getCsrfToken();
    
    // Ensure URL is absolute by prepending base URL if needed
    const fullUrl = url.startsWith('http') ? url : `${config.API_BASE_URL}${url}`;
    
    const requestOptions: RequestInit = {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRFToken': csrfToken }),
        ...options.headers,
      },
      ...options,
    };

    const response = await fetch(fullUrl, requestOptions);
    return handleApiResponse<T>(response);
  }, [getCsrfToken, handleApiResponse]);

  /**
   * Make GET request with authentication
   * @param url - API endpoint URL
   * @returns Promise with parsed response data
   */
  const get = useCallback(async <T>(url: string): Promise<T> => {
    return authenticatedRequest<T>(url, { method: 'GET' });
  }, [authenticatedRequest]);

  /**
   * Make POST request with authentication
   * @param url - API endpoint URL
   * @param data - Request body data
   * @returns Promise with parsed response data
   */
  const post = useCallback(async <T>(url: string, data: any): Promise<T> => {
    return authenticatedRequest<T>(url, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }, [authenticatedRequest]);

  /**
   * Make PUT request with authentication
   * @param url - API endpoint URL
   * @param data - Request body data
   * @returns Promise with parsed response data
   */
  const put = useCallback(async <T>(url: string, data: any): Promise<T> => {
    return authenticatedRequest<T>(url, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }, [authenticatedRequest]);

  /**
   * Make PATCH request with authentication
   * @param url - API endpoint URL
   * @param data - Request body data
   * @returns Promise with parsed response data
   */
  const patch = useCallback(async <T>(url: string, data: any): Promise<T> => {
    return authenticatedRequest<T>(url, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }, [authenticatedRequest]);

  /**
   * Make DELETE request with authentication
   * @param url - API endpoint URL
   * @returns Promise with success status
   */
  const del = useCallback(async (url: string): Promise<{ success: boolean }> => {
    const csrfToken = getCsrfToken();
    
    // Ensure URL is absolute by prepending base URL if needed
    const fullUrl = url.startsWith('http') ? url : `${config.API_BASE_URL}${url}`;
    
    const response = await fetch(fullUrl, {
      method: 'DELETE',
      credentials: 'include',
      headers: {
        ...(csrfToken && { 'X-CSRFToken': csrfToken }),
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.error || `HTTP ${response.status}`);
    }

    return { success: true };
  }, [getCsrfToken]);

  return {
    getCsrfToken,
    primeCsrfToken,
    handleApiResponse,
    authenticatedRequest,
    get,
    post,
    put,
    patch,
    del,
  };
}; 