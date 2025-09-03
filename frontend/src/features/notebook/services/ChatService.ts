import httpClient from "@/shared/utils/httpClient";
import type {
  ChatResponse,
  NotebookChatMessage
} from "@/features/notebook/type";

/**
 * Service class for chat-related API operations
 * Handles all chat functionality for notebooks
 */
class ChatService {

  // Get suggested questions for a notebook
  async getSuggestedQuestions(notebookId: string): Promise<string[]> {
    return httpClient.get<string[]>(`/notebooks/${notebookId}/suggested-questions/`);
  }

  // Get suggested questions with fetch (for consistency with existing ChatPanel implementation)
  async getSuggestedQuestionsWithFetch(notebookId: string): Promise<any> {
    const response = await fetch(`${httpClient.baseUrl}/notebooks/${notebookId}/suggested-questions/`, {
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error("Failed to fetch suggestions");
    }
    
    return response.json();
  }

  // Get chat history for a notebook
  async getChatHistory(notebookId: string): Promise<NotebookChatMessage[]> {
    return httpClient.get<NotebookChatMessage[]>(`/notebooks/${notebookId}/chat-history/`);
  }

  // Get chat history with fetch (for consistency with existing ChatPanel implementation)
  async getChatHistoryWithFetch(notebookId: string): Promise<any> {
    const response = await fetch(`${httpClient.baseUrl}/notebooks/${notebookId}/chat-history/`, {
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error("Failed to fetch chat history");
    }
    
    return response.json();
  }

  // Clear chat history for a notebook
  async clearChatHistory(notebookId: string): Promise<{ success: boolean }> {
    return httpClient.delete<{ success: boolean }>(`/notebooks/${notebookId}/chat-history/clear/`);
  }

  // Clear chat history with fetch (for consistency with existing ChatPanel implementation)
  async clearChatHistoryWithFetch(notebookId: string): Promise<void> {
    const response = await fetch(`${httpClient.baseUrl}/notebooks/${notebookId}/chat-history/clear/`, {
      method: "DELETE",
      credentials: 'include',
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": this.getCookie("csrftoken") || "",
      },
    });

    if (!response.ok) {
      throw new Error("Failed to clear chat");
    }
  }

  // Send a chat message
  async sendChatMessage(notebookId: string, fileIds: string[], question: string): Promise<ChatResponse> {
    return httpClient.post<ChatResponse>(`/notebooks/${notebookId}/chat/`, {
      file_ids: fileIds,
      question: question
    });
  }

  // Send a chat message with streaming response
  async sendChatMessageStream(notebookId: string, fileIds: string[], question: string): Promise<Response> {
    const response = await fetch(`${httpClient.baseUrl}/notebooks/${notebookId}/chat/`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": this.getCookie("csrftoken") || "",
      },
      body: JSON.stringify({
        file_ids: fileIds,
        question: question,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    return response;
  }

  // Helper method to get cookie value
  private getCookie(name: string): string | null {
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match && match[2] ? decodeURIComponent(match[2]) : null;
  }

  // Get chat message by ID
  async getChatMessage(notebookId: string, messageId: string): Promise<NotebookChatMessage> {
    return httpClient.get<NotebookChatMessage>(`/notebooks/${notebookId}/chat/${messageId}/`);
  }

  // Delete a specific chat message
  async deleteChatMessage(notebookId: string, messageId: string): Promise<{ success: boolean }> {
    return httpClient.delete<{ success: boolean }>(`/notebooks/${notebookId}/chat/${messageId}/`);
  }

  // Export chat history
  async exportChatHistory(notebookId: string, format: 'json' | 'txt' | 'csv' = 'json'): Promise<Blob> {
    const response = await fetch(`${httpClient.baseUrl}/notebooks/${notebookId}/chat-history/export/?format=${format}`, {
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
    return httpClient.get(`/notebooks/${notebookId}/chat-stats/`);
  }
}

// Export singleton instance
export default new ChatService(); 