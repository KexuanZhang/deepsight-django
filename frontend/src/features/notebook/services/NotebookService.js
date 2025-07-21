import { config } from '../../../config';

/**
 * Service class for notebook-related API operations
 * Follows single responsibility principle - only handles notebook operations
 */
class NotebookService {
  constructor() {
    this.baseUrl = config.API_BASE_URL;
  }

  // Helper to get CSRF token
  getCsrfToken() {
    const match = document.cookie.match(new RegExp(`(^| )csrftoken=([^;]+)`));
    return match ? decodeURIComponent(match[2]) : null;
  }

  // Helper to handle API responses
  async handleResponse(response) {
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
  async primeCsrf() {
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
  async getNotebooks() {
    const response = await fetch(`${this.baseUrl}/notebooks/`, {
      credentials: "include",
    });
    
    return this.handleResponse(response);
  }

  // Get single notebook
  async getNotebook(notebookId) {
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/`, {
      credentials: "include",
    });
    
    return this.handleResponse(response);
  }

  // Create notebook
  async createNotebook(name, description) {
    const response = await fetch(`${this.baseUrl}/notebooks/`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": this.getCsrfToken(),
      },
      body: JSON.stringify({
        name: name.trim(),
        description: description.trim(),
      }),
    });
    
    return this.handleResponse(response);
  }

  // Update notebook
  async updateNotebook(notebookId, updates) {
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/`, {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": this.getCsrfToken(),
      },
      body: JSON.stringify(updates),
    });
    
    return this.handleResponse(response);
  }

  // Delete notebook
  async deleteNotebook(notebookId) {
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/`, {
      method: "DELETE",
      credentials: "include",
      headers: {
        "X-CSRFToken": this.getCsrfToken(),
      },
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.error || `HTTP ${response.status}`);
    }
    
    return { success: true };
  }

  // Get suggested questions
  async getSuggestedQuestions(notebookId) {
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/suggested-questions/`, {
      credentials: 'include',
    });
    
    return this.handleResponse(response);
  }

  // Get chat history
  async getChatHistory(notebookId) {
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/chat-history/`, {
      credentials: 'include',
    });
    
    return this.handleResponse(response);
  }

  // Clear chat history
  async clearChatHistory(notebookId) {
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/chat-history/clear/`, {
      method: "DELETE",
      credentials: 'include',
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": this.getCsrfToken(),
      },
    });
    
    if (!response.ok) {
      throw new Error("Failed to clear chat history");
    }
    
    return { success: true };
  }

  // Send chat message
  async sendChatMessage(notebookId, fileIds, question) {
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/chat/`, {
      method: "POST",
      credentials: 'include',
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": this.getCsrfToken(),
      },
      body: JSON.stringify({
        file_ids: fileIds,
        question: question
      })
    });
    
    return this.handleResponse(response);
  }
}

// Export singleton instance
export default new NotebookService();