/**
 * Notebook API resource endpoints
 * Modern API v1 implementation
 */

import { apiClient } from '../client';
import { PaginatedResponse, PaginationParams } from '../types';

// Types - these should be moved to a types file eventually
export interface Notebook {
  readonly id: string;
  readonly createdAt: string;
  readonly updatedAt: string;
  name: string;
  description: string;
  sourceCount: number;
  itemCount: number;
  isProcessing: boolean;
}

export interface CreateNotebookRequest {
  name: string;
  description?: string;
}

export interface UpdateNotebookRequest {
  name?: string;
  description?: string;
}

export interface NotebookStats {
  sourceCount: number;
  itemCount: number;
  processingCount: number;
  lastUpdated: string;
}

export interface GetNotebooksParams extends PaginationParams {
  search?: string;
  ordering?: 'name' | '-name' | 'created_at' | '-created_at' | 'updated_at' | '-updated_at';
}

// API Resource
export const notebooksApi = {
  // Core CRUD operations
  getAll: (params?: GetNotebooksParams): Promise<PaginatedResponse<Notebook>> =>
    apiClient.get('/notebooks', params ? { params } : {}),

  getById: (id: string): Promise<Notebook> =>
    apiClient.get(`/notebooks/${id}`),

  create: (data: CreateNotebookRequest): Promise<Notebook> =>
    apiClient.post('/notebooks', data),

  update: (id: string, data: UpdateNotebookRequest): Promise<Notebook> =>
    apiClient.patch(`/notebooks/${id}`, data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/notebooks/${id}`),

  // Custom actions
  getStats: (id: string): Promise<NotebookStats> =>
    apiClient.get(`/notebooks/${id}/stats`),

  duplicate: (id: string, name?: string): Promise<Notebook> =>
    apiClient.post(`/notebooks/${id}/duplicate`, { name }),

  cleanupEmpty: (id: string): Promise<{ removed: number }> =>
    apiClient.post(`/notebooks/${id}/cleanup-empty`),

  // Nested resources - Sources
  sources: {
    getAll: (notebookId: string, params?: PaginationParams): Promise<PaginatedResponse<Source>> =>
      apiClient.get(`/notebooks/${notebookId}/sources`, params ? { params } : {}),

    getById: (notebookId: string, sourceId: string): Promise<Source> =>
      apiClient.get(`/notebooks/${notebookId}/sources/${sourceId}`),

    create: (notebookId: string, data: CreateSourceRequest): Promise<Source> =>
      apiClient.post(`/notebooks/${notebookId}/sources`, data),

    update: (notebookId: string, sourceId: string, data: UpdateSourceRequest): Promise<Source> =>
      apiClient.patch(`/notebooks/${notebookId}/sources/${sourceId}`, data),

    delete: (notebookId: string, sourceId: string): Promise<void> =>
      apiClient.delete(`/notebooks/${notebookId}/sources/${sourceId}`),

    // File upload
    uploadFile: (notebookId: string, file: File): Promise<Source> => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.post(`/notebooks/${notebookId}/sources`, formData);
    },

    // URL processing
    processUrl: (notebookId: string, data: ProcessUrlRequest): Promise<Source> =>
      apiClient.post(`/notebooks/${notebookId}/sources/process-url`, data),

    // Text content
    addText: (notebookId: string, data: AddTextRequest): Promise<Source> =>
      apiClient.post(`/notebooks/${notebookId}/sources/add-text`, data),
  },

  // Nested resources - Chat
  chat: {
    getHistory: (notebookId: string, params?: PaginationParams): Promise<PaginatedResponse<ChatMessage>> =>
      apiClient.get(`/notebooks/${notebookId}/chat/history`, params ? { params } : {}),

    sendMessage: (notebookId: string, message: string): Promise<ChatResponse> =>
      apiClient.post(`/notebooks/${notebookId}/chat`, { message }),

    clearHistory: (notebookId: string): Promise<void> =>
      apiClient.delete(`/notebooks/${notebookId}/chat/history`),

    getSuggestions: (notebookId: string): Promise<string[]> =>
      apiClient.get(`/notebooks/${notebookId}/chat/suggestions`),
  },

  // Knowledge base
  knowledgeBase: {
    getItems: (notebookId: string, params?: PaginationParams): Promise<PaginatedResponse<KnowledgeBaseItem>> =>
      apiClient.get(`/notebooks/${notebookId}/knowledge-base`, params ? { params } : {}),

    searchItems: (notebookId: string, query: string): Promise<KnowledgeBaseItem[]> =>
      apiClient.get(`/notebooks/${notebookId}/knowledge-base/search`, { 
        params: { q: query } 
      }),

    getImages: (notebookId: string, itemId: string): Promise<KnowledgeBaseImage[]> =>
      apiClient.get(`/notebooks/${notebookId}/knowledge-base/${itemId}/images`),
  },
};

// Supporting types (these should be moved to separate type files)
export interface Source {
  readonly id: string;
  readonly createdAt: string;
  readonly updatedAt: string;
  name: string;
  sourceType: 'file' | 'url' | 'text';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  metadata?: Record<string, any>;
}

export interface CreateSourceRequest {
  name?: string;
  sourceType: 'file' | 'url' | 'text';
}

export interface UpdateSourceRequest {
  name?: string;
}

export interface ProcessUrlRequest {
  url: string;
  includeImages?: boolean;
  includeDocuments?: boolean;
}

export interface AddTextRequest {
  title: string;
  content: string;
}

export interface ChatMessage {
  readonly id: string;
  readonly createdAt: string;
  message: string;
  response?: string;
  isUser: boolean;
}

export interface ChatResponse {
  id: string;
  message: string;
  response: string;
}

export interface KnowledgeBaseItem {
  readonly id: string;
  readonly createdAt: string;
  title: string;
  content: string;
  sourceId: string;
}

export interface KnowledgeBaseImage {
  readonly id: string;
  filename: string;
  url: string;
  caption?: string;
}