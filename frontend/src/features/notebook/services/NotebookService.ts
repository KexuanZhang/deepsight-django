import { config } from '@/config';
import type {
  Notebook,
  CreateNotebookRequest,
  UpdateNotebookRequest,
  ApiResponse,
  PaginatedResponse
} from '@/features/notebook/type';

/**
 * Service class for notebook-related API operations
 * Follows single responsibility principle - only handles notebook operations
 */
class NotebookService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = config.API_BASE_URL;
  }

  // Helper to get CSRF token
  private getCsrfToken(): string | null {
    const match = document.cookie.match(new RegExp(`(^| )csrftoken=([^;]+)`));
    return match ? decodeURIComponent(match[2]) : null;
  }

  // Helper to handle API responses
  private async handleResponse<T>(response: Response): Promise<T> {
    if (response.status === 401) {
      throw new Error('Unauthorized');
    }
    
    if (response.status === 404) {
      throw new Error('Not found');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Prime CSRF token
  async primeCsrf(): Promise<void> {
    try {
      await fetch(`${this.baseUrl}/users/csrf/`, {
        method: "GET",
        credentials: "include",
      });
    } catch (error) {
      console.error('Failed to prime CSRF:', error);
    }
  }

  // Get all notebooks
  async getNotebooks(): Promise<Notebook[]> {
    const response = await fetch(`${this.baseUrl}/notebooks/`, {
      credentials: "include",
    });
    
    return this.handleResponse<Notebook[]>(response);
  }

  // Get single notebook
  async getNotebook(notebookId: string): Promise<Notebook> {
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/`, {
      credentials: "include",
    });
    
    return this.handleResponse<Notebook>(response);
  }

  // Create notebook
  async createNotebook(name: string, description: string): Promise<Notebook> {
    const csrfToken = this.getCsrfToken();
    const response = await fetch(`${this.baseUrl}/notebooks/`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
      body: JSON.stringify({
        name: name.trim(),
        description: description.trim(),
      }),
    });
    
    return this.handleResponse<Notebook>(response);
  }

  // Update notebook
  async updateNotebook(notebookId: string, updates: UpdateNotebookRequest): Promise<Notebook> {
    const csrfToken = this.getCsrfToken();
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/`, {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
      body: JSON.stringify(updates),
    });
    
    return this.handleResponse<Notebook>(response);
  }

  // Delete notebook
  async deleteNotebook(notebookId: string): Promise<{ success: boolean }> {
    const csrfToken = this.getCsrfToken();
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/`, {
      method: "DELETE",
      credentials: "include",
      headers: {
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.error || `HTTP ${response.status}`);
    }
    
    return { success: true };
  }


}

// Export singleton instance
export default new NotebookService();