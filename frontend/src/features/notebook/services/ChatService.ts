import httpClient from '@/common/utils/httpClient';
import type {
  ChatResponse,
  NotebookChatMessage
} from '@/features/notebook/type';

/**
 * Service class for chat-related API operations
 * Handles all chat functionality for notebooks
 */
class ChatService {

  // Get suggested questions for a notebook
  async getSuggestedQuestions(notebookId: string): Promise<string[]> {
    return httpClient.get<string[]>(`/notebooks/${notebookId}/suggested-questions/`);
  }

  // Get chat history for a notebook
  async getChatHistory(notebookId: string): Promise<NotebookChatMessage[]> {
    return httpClient.get<NotebookChatMessage[]>(`/notebooks/${notebookId}/chat-history/`);
  }

  // Clear chat history for a notebook
  async clearChatHistory(notebookId: string): Promise<{ success: boolean }> {
    return httpClient.delete<{ success: boolean }>(`/notebooks/${notebookId}/chat-history/clear/`);
  }

  // Send a chat message
  async sendChatMessage(notebookId: string, fileIds: string[], question: string): Promise<ChatResponse> {
    return httpClient.post<ChatResponse>(`/notebooks/${notebookId}/chat/`, {
      file_ids: fileIds,
      question: question
    });
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