import { config } from "@/config";

interface RequestOptions extends RequestInit {
  headers?: Record<string, string>;
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  const value = match?.[2];
  return value ? decodeURIComponent(value) : null;
}

class HttpClient {
  public baseUrl: string;

  constructor() {
    this.baseUrl = config.API_BASE_URL;
  }

  async request<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const url = endpoint.startsWith('http')
      ? endpoint
      : `${this.baseUrl}${endpoint}`;

    const config: RequestInit = {
      credentials: 'include',
      headers: options.body instanceof FormData
        ? { ...options.headers }
        : { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        let msg = `HTTP ${response.status}`;
        try {
          const err = await response.json();
          if (err.detail) {
            if (Array.isArray(err.detail)) {
              msg = err.detail.map((d: any) => `${d.loc.join('.')} – ${d.msg}`).join('; ');
            } else {
              msg = err.detail;
            }
          } else if (err.file && Array.isArray(err.file)) {
            msg = err.file[0];
          } else if (err.details) {
            if (err.details.file && Array.isArray(err.details.file)) {
              msg = err.details.file[0];
            } else if (typeof err.details === 'string') {
              msg = err.details;
            } else {
              msg = JSON.stringify(err.details);
            }
          } else if (err.error) {
            msg = err.error;
          } else if (err.message) {
            msg = err.message;
          }
        } catch {}
        throw new Error(msg);
      }
      
      if (response.status === 204) {
        return { success: true } as T;
      }
      
      return await response.json();
    } catch (e) {
      console.error('HTTP request failed:', e);
      throw e;
    }
  }

  async get<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    return this.request(endpoint, {
      method: 'GET',
      ...options
    });
  }

  async post<T = any>(endpoint: string, data: any = null, options: RequestOptions = {}): Promise<T> {
    const config = {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
        ...options.headers
      },
      ...options
    };

    if (data instanceof FormData) {
      config.body = data;
    } else if (data !== null) {
      config.body = JSON.stringify(data);
      config.headers = {
        'Content-Type': 'application/json',
        ...config.headers
      };
    }

    return this.request(endpoint, config);
  }

  async put<T = any>(endpoint: string, data: any = null, options: RequestOptions = {}): Promise<T> {
    const config = {
      method: 'PUT',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
        ...options.headers
      },
      ...options
    };

    if (data instanceof FormData) {
      config.body = data;
    } else if (data !== null) {
      config.body = JSON.stringify(data);
      config.headers = {
        'Content-Type': 'application/json',
        ...config.headers
      };
    }

    return this.request(endpoint, config);
  }

  async delete<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    return this.request(endpoint, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
        ...options.headers
      },
      ...options
    });
  }

  async patch<T = any>(endpoint: string, data: any = null, options: RequestOptions = {}): Promise<T> {
    const config = {
      method: 'PATCH',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
        ...options.headers
      },
      ...options
    };

    if (data instanceof FormData) {
      config.body = data;
    } else if (data !== null) {
      config.body = JSON.stringify(data);
      config.headers = {
        'Content-Type': 'application/json',
        ...config.headers
      };
    }

    return this.request(endpoint, config);
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health/`, { credentials: 'include' });
      return response.ok;
    } catch (error) {
      console.warn('Health check failed:', error);
      return false;
    }
  }
}

const httpClient = new HttpClient();
export default httpClient;
export { getCookie };