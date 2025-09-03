// ====== REPORT SERVICE ======
// Handles all report-related API operations and business logic

import { ApiClient } from "@/shared/utils/generation";
import { 
  Report, 
  ReportGenerationRequest, 
  ReportGenerationResponse, 
  ReportContent, 
  ReportFilters,
  ReportStats 
} from "@/features/report/types/type";

export interface IReportService {
  getReports(filters?: ReportFilters): Promise<Report[]>;
  getReport(id: string): Promise<Report>;
  getReportContent(id: string): Promise<ReportContent>;
  generateReport(config: ReportGenerationRequest): Promise<ReportGenerationResponse>;
  cancelReport(id: string): Promise<void>;
  deleteReport(id: string): Promise<void>;
  downloadReport(id: string, filename?: string): Promise<void>;
  getReportStats(): Promise<ReportStats>;
  getAvailableModels(): Promise<any>;
}

export class ReportService implements IReportService {
  private api: ApiClient;
  private notebookId?: string;

  constructor(notebookId?: string) {
    this.api = new ApiClient();
    this.notebookId = notebookId;
  }

  async getReports(filters?: ReportFilters): Promise<Report[]> {
    try {
      let endpoint = '/reports/';
      
      // If notebookId is provided, get reports for that notebook
      if (this.notebookId) {
        endpoint = `/notebooks/${this.notebookId}/report-jobs/`;
      }

      // Add query parameters for filters
      const params = new URLSearchParams();
      if (filters?.status) params.append('status', filters.status);
      if (filters?.model_provider) params.append('model_provider', filters.model_provider);
      if (filters?.search) params.append('search', filters.search);
      if (filters?.date_range?.start) params.append('date_start', filters.date_range.start);
      if (filters?.date_range?.end) params.append('date_end', filters.date_range.end);

      if (params.toString()) {
        endpoint += `?${params.toString()}`;
      }

      const response = await this.api.get(endpoint);
      
      // Handle different response formats
      if (response.reports) return response.reports;
      if (response.jobs) return response.jobs;
      if (Array.isArray(response)) return response;
      
      return [];
    } catch (error) {
      console.error('Failed to fetch reports:', error);
      throw new Error('Failed to fetch reports');
    }
  }

  async getReport(id: string): Promise<Report> {
    try {
      let endpoint = `/reports/${id}/`;
      
      if (this.notebookId) {
        endpoint = `/notebooks/${this.notebookId}/report-jobs/${id}/`;
      }

      const response = await this.api.get(endpoint);
      return response;
    } catch (error) {
      console.error('Failed to fetch report:', error);
      throw new Error('Failed to fetch report');
    }
  }

  async getReportContent(id: string): Promise<ReportContent> {
    try {
      let endpoint = `/reports/${id}/content/`;
      
      if (this.notebookId) {
        endpoint = `/notebooks/${this.notebookId}/report-jobs/${id}/content/`;
      }

      const response = await this.api.get(endpoint);
      return response;
    } catch (error) {
      console.error('Failed to fetch report content:', error);
      throw new Error('Failed to fetch report content');
    }
  }

  async generateReport(config: ReportGenerationRequest): Promise<ReportGenerationResponse> {
    try {
      let endpoint = '/reports/';
      
      if (this.notebookId) {
        endpoint = `/notebooks/${this.notebookId}/report-jobs/`;
        config.notebook_id = this.notebookId;
      }

      const response = await this.api.post(endpoint, config);
      return response;
    } catch (error) {
      console.error('Failed to generate report:', error);
      throw new Error('Failed to generate report');
    }
  }

  async cancelReport(id: string): Promise<void> {
    try {
      let endpoint = `/reports/${id}/cancel/`;
      
      if (this.notebookId) {
        endpoint = `/notebooks/${this.notebookId}/report-jobs/${id}/cancel/`;
      }

      await this.api.post(endpoint);
    } catch (error) {
      console.error('Failed to cancel report:', error);
      throw new Error('Failed to cancel report');
    }
  }

  async deleteReport(id: string): Promise<void> {
    try {
      let endpoint = `/reports/${id}/`;
      
      if (this.notebookId) {
        endpoint = `/notebooks/${this.notebookId}/report-jobs/${id}/`;
      }

      await this.api.delete(endpoint);
    } catch (error) {
      console.error('Failed to delete report:', error);
      throw new Error('Failed to delete report');
    }
  }

  async downloadReport(id: string, filename?: string): Promise<void> {
    try {
      let endpoint = `/reports/${id}/download/`;
      
      if (this.notebookId) {
        endpoint = `/notebooks/${this.notebookId}/report-jobs/${id}/download/`;
      }

      const blob = await this.api.downloadFile(endpoint);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || `report-${id}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download report:', error);
      throw new Error('Failed to download report');
    }
  }

  async getReportStats(): Promise<ReportStats> {
    try {
      const endpoint = '/reports/stats/';
      const response = await this.api.get(endpoint);
      return response;
    } catch (error) {
      console.error('Failed to fetch report stats:', error);
      // Return default stats if API fails
      return {
        total: 0,
        completed: 0,
        failed: 0,
        pending: 0,
        running: 0,
        cancelled: 0
      };
    }
  }

  async getAvailableModels(): Promise<any> {
    try {
      const endpoint = '/reports/models/';
      const response = await this.api.get(endpoint);
      return response;
    } catch (error) {
      console.error('Failed to fetch available models:', error);
      // Return default models if API fails
      return {
        model_providers: ['openai', 'google'],
        retrievers: ['tavily', 'brave', 'serper', 'you', 'bing', 'duckduckgo', 'searxng'],
        models: ['gpt-4', 'gpt-3.5-turbo']
      };
    }
  }

  // ====== UTILITY METHODS ======

  setNotebookId(notebookId: string): void {
    this.notebookId = notebookId;
  }

  getNotebookId(): string | undefined {
    return this.notebookId;
  }

  // ====== FILTERING AND SORTING ======

  filterReports(reports: Report[], filters: ReportFilters): Report[] {
    return reports.filter(report => {
      if (filters.status && report.status !== filters.status) return false;
      if (filters.model_provider && report.model_provider !== filters.model_provider) return false;
      if (filters.notebook_id && report.notebook_id !== filters.notebook_id) return false;
      if (filters.search) {
        const searchLower = filters.search.toLowerCase();
        const matchesTitle = report.title?.toLowerCase().includes(searchLower);
        const matchesTopic = report.topic?.toLowerCase().includes(searchLower);
        const matchesContent = report.content?.toLowerCase().includes(searchLower);
        if (!matchesTitle && !matchesTopic && !matchesContent) return false;
      }
      return true;
    });
  }

  sortReports(reports: Report[], sortOrder: 'recent' | 'oldest' | 'title'): Report[] {
    return [...reports].sort((a, b) => {
      switch (sortOrder) {
        case 'recent':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case 'oldest':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        case 'title':
          return (a.title || '').localeCompare(b.title || '');
        default:
          return 0;
      }
    });
  }

  // ====== STATUS HELPERS ======

  isReportCompleted(report: Report): boolean {
    return report.status === 'completed';
  }

  isReportFailed(report: Report): boolean {
    return report.status === 'failed';
  }

  isReportRunning(report: Report): boolean {
    return report.status === 'running' || report.status === 'pending';
  }

  canDownloadReport(report: Report): boolean {
    return this.isReportCompleted(report) && !this.isReportFailed(report);
  }

  canCancelReport(report: Report): boolean {
    return this.isReportRunning(report);
  }

  canDeleteReport(report: Report): boolean {
    return !this.isReportRunning(report);
  }
} 