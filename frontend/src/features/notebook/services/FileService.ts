import { config } from '@/config';
import apiService from '@/common/utils/api';

/**
 * Service class for file-related operations
 * Handles file uploads, parsing, and management
 */
class FileService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = config.API_BASE_URL;
  }

  // Helper to get CSRF token
  getCsrfToken(): string | null {
    const match = document.cookie.match(new RegExp(`(^| )csrftoken=([^;]+)`));
    return match ? decodeURIComponent(match[2]) : null;
  }

  // Helper to handle API responses
  async handleResponse(response: Response): Promise<any> {
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

  // Get parsed files for a notebook
  async getParsedFiles(notebookId: string): Promise<any> {
    try {
      const response = await apiService.listParsedFiles(notebookId);
      return response;
    } catch (error: any) {
      throw new Error(`Failed to get parsed files: ${error.message}`);
    }
  }

  // Parse/upload file
  async parseFile(file: File | File[], uploadFileId: string, notebookId: string): Promise<any> {
    try {
      const response = await apiService.parseFile(file, uploadFileId, notebookId);
      return response;
    } catch (error: any) {
      throw new Error(`Failed to parse file: ${error.message}`);
    }
  }

  // Parse URL
  async parseUrl(url: string | string[], notebookId: string, algorithm: string = 'cosine', uploadFileId: string | null = null): Promise<any> {
    try {
      const response = await apiService.parseUrl(url, notebookId, algorithm, uploadFileId);
      return response;
    } catch (error: any) {
      throw new Error(`Failed to parse URL: ${error.message}`);
    }
  }

  // Parse URL with media support
  async parseUrlWithMedia(url: string | string[], notebookId: string, algorithm: string = 'cosine', uploadFileId: string | null = null): Promise<any> {
    try {
      const response = await apiService.parseUrlWithMedia(url, notebookId, algorithm, uploadFileId);
      return response;
    } catch (error: any) {
      throw new Error(`Failed to parse media URL: ${error.message}`);
    }
  }

  // Delete parsed file
  async deleteParsedFile(fileId: string, notebookId: string): Promise<any> {
    try {
      const response = await apiService.deleteParsedFile(fileId, notebookId);
      return response;
    } catch (error: any) {
      throw new Error(`Failed to delete file: ${error.message}`);
    }
  }

  // Delete file by upload ID
  async deleteFileByUploadId(uploadFileId: string, notebookId: string): Promise<any> {
    try {
      const response = await apiService.deleteFileByUploadId(uploadFileId, notebookId);
      return response;
    } catch (error: any) {
      throw new Error(`Failed to delete file by upload ID: ${error.message}`);
    }
  }

  // Get URL parsing status
  async getUrlParsingStatus(uploadUrlId: string, notebookId: string): Promise<any> {
    try {
      const response = await apiService.getUrlParsingStatus(uploadUrlId, notebookId);
      return response;
    } catch (error: any) {
      throw new Error(`Failed to get URL parsing status: ${error.message}`);
    }
  }

  // Create SSE connection for parsing status
  createParsingStatusStream(
    notebookId: string, 
    uploadFileId: string, 
    onMessage: (data: any) => void, 
    onError: (error: any) => void, 
    onClose: () => void
  ): EventSource {
    try {
      return apiService.createParsingStatusStream(notebookId, uploadFileId, onMessage, onError, onClose);
    } catch (error: any) {
      throw new Error(`Failed to create parsing status stream: ${error.message}`);
    }
  }

  // Get raw file URL
  getRawFileUrl(fileId: string, notebookId: string | null = null): string {
    return notebookId ? 
      `${this.baseUrl}/notebooks/${notebookId}/files/${fileId}/raw/` : 
      `${this.baseUrl}/files/${fileId}/raw`;
  }

  // Get file image URL
  getFileImageUrl(fileId: string, imageName: string, notebookId: string): string {
    return `${this.baseUrl}/notebooks/${notebookId}/files/${fileId}/images/${imageName}`;
  }

  // Knowledge base operations
  async getKnowledgeBase(notebookId: string): Promise<any> {
    try {
      const response = await apiService.getKnowledgeBase(notebookId);
      return response;
    } catch (error: any) {
      throw new Error(`Failed to get knowledge base: ${error.message}`);
    }
  }

  async linkKnowledgeBaseItem(notebookId: string, itemId: string): Promise<any> {
    try {
      const response = await apiService.linkKnowledgeBaseItem(notebookId, itemId);
      return response;
    } catch (error: any) {
      throw new Error(`Failed to link knowledge base item: ${error.message}`);
    }
  }

  async deleteKnowledgeBaseItem(notebookId: string, itemId: string): Promise<any> {
    try {
      const response = await apiService.deleteKnowledgeBaseItem(notebookId, itemId);
      return response;
    } catch (error: any) {
      throw new Error(`Failed to delete knowledge base item: ${error.message}`);
    }
  }

  // File utility methods
  generateUploadId(prefix: string = 'upload'): string {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  createTextFile(text: string, filename: string = 'pasted_text.txt'): File {
    const blob = new Blob([text], { type: 'text/plain' });
    return new File([blob], filename, { type: 'text/plain' });
  }

  // Domain extraction helper
  getDomainFromUrl(url: string): string {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname.replace('www.', '');
    } catch (error) {
      // If URL parsing fails, try to extract manually
      const match = url.match(/^https?:\/\/(?:www\.)?([^\/]+)/);
      return match ? match[1] : url;
    }
  }
}

// Export singleton instance
export default new FileService();