/**
 * Modern API client with enhanced error handling, retries, and type safety
 */

import { config } from "@/config";
import { ApiError, RequestConfig } from './types';
import { apiMigration, DataMigrationAdapter } from './migration';

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match?.[2] ? decodeURIComponent(match[2]) : null;
}

export class ApiClient {
  private baseUrl: string;
  private defaultTimeout: number = 10000;

  constructor(baseUrl: string = config.API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private buildUrl(endpoint: string, params?: Record<string, any>, migrationContext?: { notebookId?: string; resourceId?: string }): string {
    // Use migration adapter to get the correct endpoint
    let url: string;
    if (endpoint.startsWith('http')) {
      url = endpoint;
    } else {
      // Apply API migration logic
      const migratedEndpoint = apiMigration.getEndpoint(
        `GET ${endpoint}`, // Add method prefix for mapping lookup
        migrationContext?.notebookId,
        migrationContext?.resourceId
      );
      // Remove the base URL since migration adapter adds it
      url = migratedEndpoint;
    }

    if (!params) return url;

    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    });

    const queryString = searchParams.toString();
    return queryString ? `${url}?${queryString}` : url;
  }

  private async parseErrorResponse(response: Response): Promise<string> {
    try {
      const contentType = response.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        const err = await response.json();
        
        // Handle DRF error formats
        if (err.detail) {
          if (Array.isArray(err.detail)) {
            return err.detail.map((d: any) => `${d.loc?.join?.('.') || 'field'} – ${d.msg}`).join('; ');
          }
          return err.detail;
        }
        
        // Handle validation errors
        if (err.errors || err.error) {
          const errors = err.errors || err.error;
          if (typeof errors === 'string') return errors;
          if (typeof errors === 'object') {
            return Object.entries(errors)
              .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(', ') : messages}`)
              .join('; ');
          }
        }
        
        // Handle field-specific errors
        if (typeof err === 'object') {
          const fieldErrors = Object.entries(err)
            .filter(([key]) => key !== 'detail')
            .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(', ') : messages}`)
            .join('; ');
          
          if (fieldErrors) return fieldErrors;
        }
        
        return err.message || JSON.stringify(err);
      }
      
      return await response.text() || `HTTP ${response.status}`;
    } catch {
      return `HTTP ${response.status}`;
    }
  }

  async request<T = any>(
    endpoint: string, 
    config: RequestConfig & { migrationContext?: { notebookId?: string; resourceId?: string } } = {}
  ): Promise<T> {
    const { params, timeout = this.defaultTimeout, migrationContext, ...requestInit } = config;
    const url = this.buildUrl(endpoint, params, migrationContext);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const requestConfig: RequestInit = {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...requestInit.headers,
      },
      signal: controller.signal,
      ...requestInit,
    };

    // Handle FormData - remove Content-Type to let browser set it
    if (requestInit.body instanceof FormData) {
      const { 'Content-Type': _, ...headersWithoutContentType } = requestConfig.headers as Record<string, string>;
      requestConfig.headers = headersWithoutContentType;
    }

    try {
      const response = await fetch(url, requestConfig);
      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorMessage = await this.parseErrorResponse(response);
        throw new ApiError(errorMessage, response.status, response);
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return { success: true } as T;
      }

      const contentType = response.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        return await response.json();
      }
      
      return await response.text() as T;
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof ApiError) {
        throw error;
      }
      
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ApiError(`Request timeout after ${timeout}ms`, 408);
      }
      
      console.error('API request failed:', error);
      throw new ApiError(
        error instanceof Error ? error.message : 'Network error',
        0
      );
    }
  }

  async get<T = any>(
    endpoint: string, 
    config: RequestConfig = {}
  ): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', ...config });
  }

  async post<T = any>(
    endpoint: string, 
    data?: any, 
    config: RequestConfig = {}
  ): Promise<T> {
    const requestConfig: RequestConfig = {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
        ...config.headers,
      },
      ...config,
    };

    if (data instanceof FormData) {
      requestConfig.body = data;
    } else if (data !== undefined && data !== null) {
      requestConfig.body = JSON.stringify(data);
    }

    return this.request<T>(endpoint, requestConfig);
  }

  async put<T = any>(
    endpoint: string, 
    data?: any, 
    config: RequestConfig = {}
  ): Promise<T> {
    const requestConfig: RequestConfig = {
      method: 'PUT',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
        ...config.headers,
      },
      ...config,
    };

    if (data instanceof FormData) {
      requestConfig.body = data;
    } else if (data !== undefined && data !== null) {
      requestConfig.body = JSON.stringify(data);
    }

    return this.request<T>(endpoint, requestConfig);
  }

  async patch<T = any>(
    endpoint: string, 
    data?: any, 
    config: RequestConfig = {}
  ): Promise<T> {
    const requestConfig: RequestConfig = {
      method: 'PATCH',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
        ...config.headers,
      },
      ...config,
    };

    if (data instanceof FormData) {
      requestConfig.body = data;
    } else if (data !== undefined && data !== null) {
      requestConfig.body = JSON.stringify(data);
    }

    return this.request<T>(endpoint, requestConfig);
  }

  async delete<T = any>(
    endpoint: string, 
    config: RequestConfig = {}
  ): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
        ...config.headers,
      },
      ...config,
    });
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.get('/health/');
      return true;
    } catch (error) {
      console.warn('Health check failed:', error);
      return false;
    }
  }
}

// Create singleton instance
export const apiClient = new ApiClient();

// Legacy client for gradual migration
export const legacyApiClient = new ApiClient('');