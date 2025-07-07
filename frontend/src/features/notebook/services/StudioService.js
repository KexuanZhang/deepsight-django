// ====== DEPENDENCY INVERSION PRINCIPLE (DIP) ======
// Abstracting dependencies and inverting control from concrete to abstract

// Abstract service interface - components depend on this abstraction, not concrete implementation
export class IStudioService {
  async generateReport(config) { throw new Error('Not implemented'); }
  async generatePodcast(config) { throw new Error('Not implemented'); }
  async cancelGeneration(jobId) { throw new Error('Not implemented'); }
  async getAvailableModels() { throw new Error('Not implemented'); }
  async loadReports(notebookId) { throw new Error('Not implemented'); }
  async loadPodcasts(notebookId) { throw new Error('Not implemented'); }
  async loadReportContent(reportId) { throw new Error('Not implemented'); }
  async downloadFile(fileId, filename) { throw new Error('Not implemented'); }
  async deleteFile(fileId) { throw new Error('Not implemented'); }
  async updateFile(fileId, content) { throw new Error('Not implemented'); }
  async loadAudio(podcastId) { throw new Error('Not implemented'); }
}

// Concrete implementation using the new get/post methods
export class ApiStudioService extends IStudioService {
  constructor(apiClient, notebookId) {
    super();
    this.api = apiClient; // Dependency injection
    this.notebookId = notebookId; // Store notebook ID for API calls
  }

  async generateReport(config) {
    const response = await this.api.post(`/notebooks/${this.notebookId}/report-jobs/`, config);
    return response;
  }

  async generatePodcast(config) {
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

  async cancelGeneration(jobId) {
    // For now, we'll determine the type and call the appropriate cancel method
    // This could be improved by storing job type metadata
    try {
      return await this.api.post(`/notebooks/${this.notebookId}/report-jobs/${jobId}/cancel/`);
    } catch (error) {
      // If report cancel fails, try podcast cancel
      return await this.api.post(`/notebooks/${this.notebookId}/podcast-jobs/${jobId}/cancel/`);
    }
  }

  async getAvailableModels() {
    const response = await this.api.get('/notebooks/reports/models/');
    return {
      model_providers: response.model_providers || response.providers || [],
      retrievers: response.retrievers || []
    };
  }

  async loadReports(notebookId) {
    const response = await this.api.get(`/notebooks/${notebookId}/report-jobs/`);
    return response.reports || response.jobs || response || [];
  }

  async loadPodcasts(notebookId) {
    const response = await this.api.get(`/notebooks/${notebookId}/podcast-jobs/`);
    return response.results || response.jobs || response || [];
  }

  async loadReportContent(reportId) {
    const response = await this.api.get(`/notebooks/${this.notebookId}/report-jobs/${reportId}/content/`);
    return response;
  }

  async downloadFile(fileId, filename) {
    try {
      // Download report as PDF instead of markdown
      const blob = await this.api.downloadReportPdf(fileId, this.notebookId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      // Change file extension to .pdf
      const pdfFilename = filename.replace(/\.[^/.]+$/, '') + '.pdf';
      link.download = pdfFilename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('PDF download failed:', error);
      throw error;
    }
  }

  async deleteFile(fileId) {
    // Try to delete as report first, then as podcast
    try {
      return await this.api.delete(`/notebooks/${this.notebookId}/report-jobs/${fileId}/`);
    } catch (error) {
      return await this.api.delete(`/notebooks/${this.notebookId}/podcast-jobs/${fileId}/`);
    }
  }

  async updateFile(fileId, content) {
    // Use the dedicated updateReport method for proper report content updates
    return await this.api.updateReport(fileId, this.notebookId, content);
  }

  async loadAudio(podcastId) {
    const blob = await this.api.downloadPodcastAudio(podcastId, this.notebookId);
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
export class IJobService {
  subscribe(jobId, onUpdate) { throw new Error('Not implemented'); }
  unsubscribe(jobId) { throw new Error('Not implemented'); }
  saveJob(jobId, jobData) { throw new Error('Not implemented'); }
  getJob(jobId) { throw new Error('Not implemented'); }
  clearJob(jobId) { throw new Error('Not implemented'); }
}

export class LocalStorageJobService extends IJobService {
  constructor() {
    super();
    this.subscribers = new Map();
  }

  subscribe(jobId, onUpdate) {
    this.subscribers.set(jobId, onUpdate);
  }

  unsubscribe(jobId) {
    this.subscribers.delete(jobId);
  }

  saveJob(jobId, jobData) {
    const key = `studio_job_${jobId}`;
    localStorage.setItem(key, JSON.stringify(jobData));
  }

  getJob(jobId) {
    const key = `studio_job_${jobId}`;
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : null;
  }

  clearJob(jobId) {
    const key = `studio_job_${jobId}`;
    localStorage.removeItem(key);
  }
}