/**
 * Modern Notebook Service with API v1 migration support
 * Provides consistent interface while transitioning endpoints
 */

import { apiClient } from "@/shared/api";
import { apiMigration, DataMigrationAdapter } from "@/shared/api/migration";
import type { Notebook, CreateNotebookRequest, UpdateNotebookRequest } from '@/features/notebook/type';

export class NotebookService {
  private static instance: NotebookService;
  
  static getInstance(): NotebookService {
    if (!NotebookService.instance) {
      NotebookService.instance = new NotebookService();
    }
    return NotebookService.instance;
  }

  /**
   * Get all notebooks for the current user
   */
  async getAll(): Promise<Notebook[]> {
    const response = await apiClient.request<Notebook[]>('/notebooks/', {
      method: 'GET',
    });

    return response;
  }

  /**
   * Get a specific notebook by ID
   */
  async getById(id: string): Promise<Notebook> {
    const response = await apiClient.request<Notebook>(`/notebooks/${id}/`, {
      method: 'GET',
      migrationContext: { notebookId: id },
    });

    return response;
  }

  /**
   * Create a new notebook
   */
  async create(notebook: CreateNotebookRequest): Promise<Notebook> {
    const response = await apiClient.request<Notebook>('/notebooks/', {
      method: 'POST',
      body: JSON.stringify(notebook),
    });

    return response;
  }

  /**
   * Update an existing notebook
   */
  async update(id: string, notebook: UpdateNotebookRequest): Promise<Notebook> {
    const response = await apiClient.request<Notebook>(`/notebooks/${id}/`, {
      method: 'PUT',
      body: JSON.stringify(notebook),
      migrationContext: { notebookId: id },
    });

    return response;
  }

  /**
   * Delete a notebook
   */
  async delete(id: string): Promise<void> {
    await apiClient.request<void>(`/notebooks/${id}/`, {
      method: 'DELETE',
      migrationContext: { notebookId: id },
    });
  }

  /**
   * Get notebook sources (migrated from files)
   */
  async getSources(notebookId: string): Promise<any[]> {
    const response = await apiClient.request<any[]>(`/notebooks/${notebookId}/files/`, {
      method: 'GET',
      migrationContext: { notebookId },
    });

    // Transform legacy file data to modern source format
    return DataMigrationAdapter.transformSourceData(response);
  }

  /**
   * Upload source to notebook (migrated from file upload)
   */
  async uploadSource(notebookId: string, formData: FormData): Promise<any> {
    const response = await apiClient.request<any>(`/notebooks/${notebookId}/files/upload/`, {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type for FormData
      migrationContext: { notebookId },
    });

    return DataMigrationAdapter.transformSourceData(response);
  }

  /**
   * Delete a source from notebook
   */
  async deleteSource(notebookId: string, sourceId: string): Promise<void> {
    await apiClient.request<void>(`/notebooks/${notebookId}/files/${sourceId}/`, {
      method: 'DELETE',
      migrationContext: { notebookId, resourceId: sourceId },
    });
  }

  /**
   * Send chat message to notebook
   */
  async sendChatMessage(notebookId: string, message: string): Promise<any> {
    const response = await apiClient.request<any>(`/notebooks/${notebookId}/chat/`, {
      method: 'POST',
      body: JSON.stringify({ message }),
      migrationContext: { notebookId },
    });

    return response;
  }

  /**
   * Get chat history for notebook
   */
  async getChatHistory(notebookId: string): Promise<any[]> {
    const response = await apiClient.request<any[]>(`/notebooks/${notebookId}/chat/history/`, {
      method: 'GET',
      migrationContext: { notebookId },
    });

    return response;
  }

  /**
   * Get reports for notebook
   */
  async getReports(notebookId: string): Promise<any[]> {
    const response = await apiClient.request<any[]>(`/notebooks/${notebookId}/reports/`, {
      method: 'GET',
      migrationContext: { notebookId },
    });

    return response;
  }

  /**
   * Generate report for notebook
   */
  async generateReport(notebookId: string, config: any): Promise<any> {
    const response = await apiClient.request<any>(`/notebooks/${notebookId}/reports/`, {
      method: 'POST',
      body: JSON.stringify(config),
      migrationContext: { notebookId },
    });

    return response;
  }

  /**
   * Get podcasts for notebook
   */
  async getPodcasts(notebookId: string): Promise<any[]> {
    const response = await apiClient.request<any[]>(`/notebooks/${notebookId}/podcasts/`, {
      method: 'GET',
      migrationContext: { notebookId },
    });

    return response;
  }

  /**
   * Generate podcast for notebook
   */
  async generatePodcast(notebookId: string, config: any): Promise<any> {
    const response = await apiClient.request<any>(`/notebooks/${notebookId}/podcasts/`, {
      method: 'POST',
      body: JSON.stringify(config),
      migrationContext: { notebookId },
    });

    return response;
  }

  /**
   * Get migration status for debugging
   */
  getMigrationStatus() {
    return apiMigration.getMigrationStatus();
  }

  /**
   * Force enable/disable specific API versions for testing
   */
  setApiVersion(resource: string, useV1: boolean) {
    const flagMap: Record<string, keyof typeof apiMigration> = {
      notebooks: 'USE_V1_NOTEBOOKS' as any,
      sources: 'USE_V1_SOURCES' as any,
      chat: 'USE_V1_CHAT' as any,
      reports: 'USE_V1_REPORTS' as any,
      podcasts: 'USE_V1_PODCASTS' as any,
    };

    const flag = flagMap[resource];
    if (flag) {
      (apiMigration as any).setFlag(flag, useV1);
    }
  }
}

// Export singleton instance
export const notebookService = NotebookService.getInstance();
export default notebookService;