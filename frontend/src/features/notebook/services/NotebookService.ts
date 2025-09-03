import httpClient from "@/shared/utils/httpClient";
import type {
  Notebook,
  UpdateNotebookRequest
} from "@/features/notebook/type";

/**
 * Service class for core notebook management
 * Handles notebook CRUD operations only
 */
class NotebookService {

  // Prime CSRF token
  async primeCsrf(): Promise<void> {
    try {
      await httpClient.get('/users/csrf/');
    } catch (error) {
      console.error('Failed to prime CSRF:', error);
    }
  }

  // ─── NOTEBOOK MANAGEMENT ─────────────────────────────────────────────────

  async getNotebooks(): Promise<Notebook[]> {
    return httpClient.get<Notebook[]>('/notebooks/');
  }

  async getNotebook(notebookId: string): Promise<Notebook> {
    return httpClient.get<Notebook>(`/notebooks/${notebookId}/`);
  }

  async createNotebook(name: string, description: string): Promise<Notebook> {
    return httpClient.post<Notebook>('/notebooks/', {
      name: name.trim(),
      description: description.trim(),
    });
  }

  async updateNotebook(notebookId: string, updates: UpdateNotebookRequest): Promise<Notebook> {
    return httpClient.patch<Notebook>(`/notebooks/${notebookId}/`, updates);
  }

  async deleteNotebook(notebookId: string): Promise<{ success: boolean }> {
    return httpClient.delete<{ success: boolean }>(`/notebooks/${notebookId}/`);
  }
}

export default new NotebookService();
