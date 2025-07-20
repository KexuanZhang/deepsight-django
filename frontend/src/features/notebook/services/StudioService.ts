// ====== DEPENDENCY INVERSION PRINCIPLE (DIP) ======
// Abstracting dependencies and inverting control from concrete to abstract

import type { GenerationConfig } from '@/types/global';

// API Client interface
interface ApiClient {
  get(url: string): Promise<any>;
  post(url: string, data?: any): Promise<any>;
  delete(url: string): Promise<any>;
  put(url: string, data?: any): Promise<any>;
}

// Abstract service interface - components depend on this abstraction, not concrete implementation
export abstract class IStudioService {
  abstract generateReport(config: GenerationConfig): Promise<any>;
  abstract generatePodcast(config: GenerationConfig): Promise<any>;
  abstract cancelGeneration(jobId: string): Promise<any>;
  abstract getAvailableModels(): Promise<string[]>;
  abstract loadReports(notebookId: string): Promise<any>;
  abstract loadPodcasts(notebookId: string): Promise<any>;
  abstract loadReportContent(reportId: string): Promise<any>;
  abstract downloadFile(fileId: string, filename: string): Promise<any>;
  abstract deleteFile(fileId: string): Promise<any>;
  abstract updateFile(fileId: string, content: string): Promise<any>;
  abstract loadAudio(podcastId: string): Promise<string>;
}

// Concrete implementation using the new get/post methods
export class ApiStudioService extends IStudioService {
  private api: ApiClient;
  private notebookId: string;

  constructor(apiClient: ApiClient, notebookId: string) {
    super();
    this.api = apiClient; // Dependency injection
    this.notebookId = notebookId; // Store notebook ID for API calls
  }

  async generateReport(config: GenerationConfig): Promise<any> {
    const response = await this.api.post(`/notebooks/${this.notebookId}/report-jobs/`, config);
    return response;
  }

  async generatePodcast(config: GenerationConfig): Promise<any> {
    // Convert config to FormData as expected by the API
    const formData = new FormData();
    
    // Add all config fields to FormData
    Object.keys(config).forEach(key => {
      if (config[key] !== undefined && config[key] !== null) {
        if (Array.isArray(config[key])) {
          // Handle arrays (like selected_files)
          config[key].forEach(item => {
            formData.append(key, item);
          });
        } else {
          formData.append(key, config[key]);
        }
      }
    });

    const response = await this.api.post(`/notebooks/${this.notebookId}/podcast-jobs/`, formData);
    return response;
  }

  async cancelGeneration(jobId: string): Promise<any> {
    // For now, we'll determine the type and call the appropriate cancel method
    // This could be improved by storing job type metadata
    try {
      // Try report cancel first
      const reportUrl = `/notebooks/${this.notebookId}/report-jobs/${jobId}/cancel/`;
      const result = await this.api.post(reportUrl);
      return result;
    } catch (error) {
      // If report cancel fails, try podcast cancel
      try {
        const podcastUrl = `/notebooks/${this.notebookId}/podcast-jobs/${jobId}/cancel/`;
        const result = await this.api.post(podcastUrl);
        return result;
      } catch (podcastError) {
        throw podcastError;
      }
    }
  }

  async getAvailableModels(): Promise<any> {
    const response = await this.api.get('/notebooks/reports/models/');
    return {
      model_providers: response.model_providers || response.providers || [],
      retrievers: response.retrievers || []
    };
  }

  async loadReports(notebookId: string): Promise<any> {
    const response = await this.api.get(`/notebooks/${notebookId}/report-jobs/`);
    return response.reports || response.jobs || response || [];
  }

  async loadPodcasts(notebookId: string): Promise<any> {
    const response = await this.api.get(`/notebooks/${notebookId}/podcast-jobs/`);
    return response.results || response.jobs || response || [];
  }

  async loadReportContent(reportId: string): Promise<any> {
    const response = await this.api.get(`/notebooks/${this.notebookId}/report-jobs/${reportId}/content/`);
    return response;
  }

  async downloadFile(fileId: string, filename: string): Promise<any> {
    try {
      // Open report PDF in browser instead of downloading
      // TODO: Implement downloadReportPdf in ApiService
      const response = await this.api.get(`/notebooks/${this.notebookId}/reports/${fileId}/download/`);
      const blob = new Blob([response], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      // Open PDF in new tab/window
      window.open(url, '_blank');
      // Clean up the blob URL after a short delay to allow browser to load it
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
      }, 1000);
    } catch (error) {
      console.error('PDF open failed:', error);
      throw error;
    }
  }

  async deleteFile(fileId: string): Promise<any> {
    // Try to delete as report first, then as podcast
    try {
      return await this.api.delete(`/notebooks/${this.notebookId}/report-jobs/${fileId}/`);
    } catch (error) {
      return await this.api.delete(`/notebooks/${this.notebookId}/podcast-jobs/${fileId}/`);
    }
  }

  async updateFile(fileId: string, content: string): Promise<any> {
    // Use the dedicated updateReport method for proper report content updates
    // TODO: Implement updateReport in ApiService
    return await this.api.put(`/notebooks/${this.notebookId}/reports/${fileId}/`, { content });
  }

  async loadAudio(podcastId: string): Promise<string> {
    // TODO: Implement downloadPodcastAudio in ApiService
    const response = await this.api.get(`/notebooks/${this.notebookId}/podcasts/${podcastId}/download/`);
    const blob = new Blob([response], { type: 'audio/mpeg' });
    return window.URL.createObjectURL(blob);
  }

  // Convenience methods for job recovery
  async getReports() {
    return await this.loadReports(this.notebookId);
  }

  async getPodcasts() {
    return await this.loadPodcasts(this.notebookId);
  }
}

// Job management service - separated concern
export abstract class IJobService {
  abstract subscribe(jobId: string, onUpdate: (data: any) => void): void;
  abstract unsubscribe(jobId: string): void;
  abstract saveJob(jobId: string, jobData: any): void;
  abstract getJob(jobId: string): any;
  abstract clearJob(jobId: string): void;
}

export class LocalStorageJobService extends IJobService {
  private subscribers: Map<string, (data: any) => void>;

  constructor() {
    super();
    this.subscribers = new Map();
  }

  subscribe(jobId: string, onUpdate: (data: any) => void): void {
    this.subscribers.set(jobId, onUpdate);
  }

  unsubscribe(jobId: string): void {
    this.subscribers.delete(jobId);
  }

  saveJob(jobId: string, jobData: any): void {
    const key = `studio_job_${jobId}`;
    localStorage.setItem(key, JSON.stringify(jobData));
  }

  getJob(jobId: string): any {
    const key = `studio_job_${jobId}`;
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : null;
  }

  clearJob(jobId: string): void {
    const key = `studio_job_${jobId}`;
    localStorage.removeItem(key);
  }
}