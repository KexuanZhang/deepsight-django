import { config } from '@/config';
import type {
  ChatRequest,
  ChatResponse,
  NotebookChatMessage
} from '@/features/notebook/type';

/**
 * Service class for chat-related API operations
 * Handles all chat functionality for notebooks
 */
class ChatService {
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

  // Get suggested questions for a notebook
  async getSuggestedQuestions(notebookId: string): Promise<string[]> {
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/suggested-questions/`, {
      credentials: 'include',
    });
    
    return this.handleResponse<string[]>(response);
  }

  // Get chat history for a notebook
  async getChatHistory(notebookId: string): Promise<NotebookChatMessage[]> {
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/chat-history/`, {
      credentials: 'include',
    });
    
    return this.handleResponse<NotebookChatMessage[]>(response);
  }

  // Clear chat history for a notebook
  async clearChatHistory(notebookId: string): Promise<{ success: boolean }> {
    const csrfToken = this.getCsrfToken();
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/chat-history/clear/`, {
      method: "DELETE",
      credentials: 'include',
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
    });
    
    if (!response.ok) {
      throw new Error("Failed to clear chat history");
    }
    
    return { success: true };
  }

  // Send a chat message
  async sendChatMessage(notebookId: string, fileIds: string[], question: string): Promise<ChatResponse> {
    const csrfToken = this.getCsrfToken();
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/chat/`, {
      method: "POST",
      credentials: 'include',
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
      body: JSON.stringify({
        file_ids: fileIds,
        question: question
      })
    });
    
    return this.handleResponse<ChatResponse>(response);
  }

  // Get chat message by ID
  async getChatMessage(notebookId: string, messageId: string): Promise<NotebookChatMessage> {
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/chat/${messageId}/`, {
      credentials: 'include',
    });
    
    return this.handleResponse<NotebookChatMessage>(response);
  }

  // Delete a specific chat message
  async deleteChatMessage(notebookId: string, messageId: string): Promise<{ success: boolean }> {
    const csrfToken = this.getCsrfToken();
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/chat/${messageId}/`, {
      method: "DELETE",
      credentials: 'include',
      headers: {
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
    });
    
    if (!response.ok) {
      throw new Error("Failed to delete chat message");
    }
    
    return { success: true };
  }

  // Export chat history
  async exportChatHistory(notebookId: string, format: 'json' | 'txt' | 'csv' = 'json'): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/chat-history/export/?format=${format}`, {
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error("Failed to export chat history");
    }
    
    return response.blob();
  }

  // Get chat statistics
  async getChatStats(notebookId: string): Promise<{
    total_messages: number;
    user_messages: number;
    assistant_messages: number;
    average_response_time: number;
    last_activity: string;
  }> {
    const response = await fetch(`${this.baseUrl}/notebooks/${notebookId}/chat-stats/`, {
      credentials: 'include',
    });
    
    return this.handleResponse(response);
  }
}

// Export singleton instance
export default new ChatService(); 