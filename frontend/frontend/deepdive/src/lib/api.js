// API service for backend communication
const API_BASE_URL = 'http://localhost:8000/api/v1';

class ApiService {
  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        let errorMessage = `HTTP error! status: ${response.status}`;
        
        try {
          const errorData = await response.json();
          
          // Handle FastAPI validation errors
          if (errorData.detail) {
            if (Array.isArray(errorData.detail)) {
              // Format validation errors nicely
              const validationErrors = errorData.detail.map(err => 
                `${err.loc?.join('.')} - ${err.msg}`
              ).join('; ');
              errorMessage = `Validation error: ${validationErrors}`;
            } else {
              errorMessage = errorData.detail;
            }
          }
        } catch (parseError) {
          console.error('Failed to parse error response:', parseError);
        }
        
        throw new Error(errorMessage);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Health check
  async healthCheck() {
    return this.request('/health');
  }

  // ===== REPORT GENERATION =====
  
  // Generate report with new unified endpoint
  async generateReport(requestData) {
    return this.request('/reports/generate', {
      method: 'POST',
      body: JSON.stringify(requestData),
    });
  }

  // Legacy support - redirect to new endpoint
  async generateAdvancedReport(requestData) {
    return this.generateReport(requestData);
  }

  // Legacy support - redirect to new endpoint  
  async generateReportWithSourceIds(requestData) {
    return this.generateReport(requestData);
  }

  // Legacy support - redirect to new endpoint
  async generateAdvancedReportWithSourceIds(requestData) {
    return this.generateReport(requestData);
  }

  // Get report status
  async getReportStatus(jobId) {
    return this.request(`/reports/status/${jobId}`);
  }

  // Cancel a report generation job
  async cancelJob(jobId) {
    return this.request('/reports/cancel', {
      method: 'POST',
      body: JSON.stringify({ job_id: jobId }),
    });
  }

  // List all jobs
  async listJobs(limit = 50, userId = null) {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (userId) {
      params.append('user_id', userId);
    }
    return this.request(`/reports/jobs?${params}`);
  }

  // Get report content
  async getReportContent(jobId) {
    return this.request(`/reports/${jobId}/content`);
  }

  // Download report file
  async downloadFile(jobId, filename = null) {
    const params = filename ? `?filename=${encodeURIComponent(filename)}` : '';
    const url = `${this.baseUrl}/reports/${jobId}/download${params}`;
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Download failed: ${response.status}`);
    }
    
    return response.blob();
  }

  // List files for a job
  async listJobFiles(jobId) {
    return this.request(`/reports/${jobId}/files`);
  }

  // Get available models and options
  async getAvailableModels() {
    return this.request('/reports/available-models');
  }

  // Clean up old jobs
  async cleanupOldJobs(days = 7) {
    return this.request(`/reports/cleanup?days=${days}`, {
      method: 'DELETE',
    });
  }

  // ===== PODCAST GENERATION =====

  // Generate podcast from source files
  async generatePodcast(formData) {
    return this.request('/podcasts/generate', {
      method: 'POST',
      headers: {}, // Let browser set Content-Type for FormData
      body: formData,
    });
  }

  // Get podcast job status
  async getPodcastJobStatus(jobId) {
    return this.request(`/podcasts/jobs/${jobId}/status`);
  }

  // List all podcast jobs
  async listPodcastJobs() {
    return this.request('/podcasts/jobs');
  }

  // Cancel podcast generation job
  async cancelPodcastJob(jobId) {
    return this.request(`/podcasts/jobs/${jobId}/cancel`, {
      method: 'DELETE',
    });
  }

  // Delete podcast job
  async deletePodcastJob(jobId) {
    return this.request(`/podcasts/jobs/${jobId}`, {
      method: 'DELETE',
    });
  }

  // Get podcast conversation text
  async getPodcastConversation(jobId) {
    return this.request(`/podcasts/jobs/${jobId}/conversation`);
  }

  // ===== FILE MANAGEMENT =====

  // Upload and parse file
  async parseFile(file, uploadFileId = null) {
    const formData = new FormData();
    formData.append('file', file);
    if (uploadFileId) {
      formData.append('upload_file_id', uploadFileId);
    }
    
    return this.request('/files/upload', {
      method: 'POST',
      headers: {}, // Let browser set Content-Type for FormData
      body: formData,
    });
  }

  // Parse URL
  async parseUrl(url, extractionStrategy = 'cosine', uploadUrlId = null) {
    const formData = new FormData();
    formData.append('url', url);
    formData.append('extraction_strategy', extractionStrategy);
    if (uploadUrlId) {
      formData.append('upload_url_id', uploadUrlId);
    }
    
    return this.request('/files/urls/parse', {
      method: 'POST',
      headers: {}, // Let browser set Content-Type for FormData
      body: formData,
    });
  }

  // Parse multiple URLs in batch
  async parseUrlsBatch(urls, extractionStrategy = 'cosine') {
    return this.request('/files/urls/batch-parse', {
      method: 'POST',
      body: JSON.stringify({
        urls: urls,
        extraction_strategy: extractionStrategy
      }),
    });
  }

  // List all parsed files
  async listParsedFiles() {
    return this.request('/files/list');
  }

  // List all parsed URLs
  async listParsedUrls() {
    return this.request('/files/urls/list');
  }

  // Get knowledge base (all files and URLs)
  async getKnowledgeBase() {
    return this.request('/files/knowledge-base');
  }

  // Get parsed file content and metadata
  async getParsedFile(fileId) {
    return this.request(`/files/${fileId}/content`);
  }

  // Get parsed file metadata
  async getParsedFileMetadata(fileId) {
    return this.request(`/files/${fileId}/metadata`);
  }

  // Get parsed URL content and metadata
  async getParsedUrl(urlId) {
    return this.request(`/files/urls/${urlId}/content`);
  }

  // Delete parsed file
  async deleteParsedFile(fileId) {
    return this.request(`/files/${fileId}`, {
      method: 'DELETE',
    });
  }

  // Delete file by upload ID (cancels parsing if running, deletes if completed)
  async deleteFileByUploadId(uploadFileId) {
    return this.request(`/files/upload/${uploadFileId}`, {
      method: 'DELETE',
    });
  }

  // Get parsing status by upload file ID
  async getParsingStatus(uploadFileId) {
    return this.request(`/files/upload/${uploadFileId}/status`);
  }

  // Create SSE connection for real-time parsing status updates
  createParsingStatusStream(uploadFileId, onMessage, onError = null, onClose = null) {
    const eventSource = new EventSource(`${this.baseUrl}/files/upload/${uploadFileId}/status/stream`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('Error parsing SSE data:', error);
        if (onError) onError(error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      if (onError) onError(error);
    };

    eventSource.onclose = () => {
      console.log('SSE connection closed');
      if (onClose) onClose();
    };

    return eventSource;
  }

  // Delete parsed URL
  async deleteParsedUrl(urlId) {
    return this.request(`/files/urls/${urlId}`, {
      method: 'DELETE',
    });
  }

  // Delete URL by upload ID (cancels parsing if running, deletes if completed)
  async deleteUrlByUploadId(uploadUrlId) {
    return this.request(`/files/urls/upload/${uploadUrlId}`, {
      method: 'DELETE',
    });
  }

  // Get URL parsing status by upload URL ID
  async getUrlParsingStatus(uploadUrlId) {
    return this.request(`/files/urls/upload/${uploadUrlId}/status`);
  }

  // ===== WEBSOCKET =====

  // Create WebSocket connection for job status updates
  createJobStatusWebSocket(jobId, onMessage, onError, onClose) {
    const wsUrl = `ws://localhost:8000/api/v1/ws/job-status/${jobId}`;
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
        onError?.(error);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      onError?.(error);
    };
    
    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      onClose?.(event);
    };
    
    // Helper method to send messages
    ws.sendMessage = (message) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
      }
    };
    
    // Helper method to cancel job via WebSocket
    ws.cancelJob = () => {
      ws.sendMessage({ type: 'cancel_job' });
    };
    
    // Helper method to send ping
    ws.ping = () => {
      ws.sendMessage({ type: 'ping' });
    };
    
    return ws;
  }

  // ===== LEGACY SUPPORT =====
  
  // Legacy method names for backward compatibility
  async deleteJob(jobId) {
    return this.cancelJob(jobId);
  }
}

const apiService = new ApiService();
export default apiService;

// Export individual methods for easier importing
export const {
  healthCheck,
  generateReport,
  generateAdvancedReport,
  generateReportWithSourceIds,
  generateAdvancedReportWithSourceIds,
  getReportStatus,
  cancelJob,
  listJobs,
  getReportContent,
  downloadFile,
  listJobFiles,
  getAvailableModels,
  cleanupOldJobs,
  generatePodcast,
  getPodcastJobStatus,
  listPodcastJobs,
  cancelPodcastJob,
  deletePodcastJob,
  getPodcastConversation,
  parseFile,
  parseUrl,
  parseUrlsBatch,
  listParsedFiles,
  listParsedUrls,
  getKnowledgeBase,
  getParsedFile,
  getParsedFileMetadata,
  getParsedUrl,
  deleteParsedFile,
  deleteFileByUploadId,
  getParsingStatus,
  createParsingStatusStream,
  deleteParsedUrl,
  deleteUrlByUploadId,
  getUrlParsingStatus,
  createJobStatusWebSocket,
  deleteJob,
} = apiService; 