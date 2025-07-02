import { config } from '../config.js';

const API_BASE_URL = config.API_BASE_URL;

// Helper to get CSRF token from cookie
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

class ApiService {
  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http')
      ? endpoint
      : `${this.baseUrl}${endpoint}`;

    const config = {
      credentials: 'include',
      // if we're sending FormData, let the browser set Content-Type for us
      headers: options.body instanceof FormData
        ? { ...options.headers }
        : { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        let msg = `HTTP ${response.status}`;
        try {
          const err = await response.json();
          if (err.detail) {
            if (Array.isArray(err.detail)) {
              msg = err.detail.map(d => `${d.loc.join('.')} – ${d.msg}`).join('; ');
            } else {
              msg = err.detail;
            }
          }
        } catch {}
        throw new Error(msg);
      }
      
      // Handle 204 No Content responses (common for DELETE operations)
      if (response.status === 204) {
        return { success: true };
      }
      
      return await response.json();
    } catch (e) {
      console.error('API request failed:', e);
      throw e;
    }
  }

  // ─── FILES ────────────────────────────────────────────────────────────────

  async listParsedFiles(notebookId, { limit = 50, offset = 0 } = {}) {
    return this.request(`/notebooks/${notebookId}/files/?limit=${limit}&offset=${offset}`);
  }

  async getParsedFile(fileId) {
    // Get file content from knowledge base item
    // Use the correct notebooks endpoint structure
    return this.request(`/notebooks/files/${fileId}/content/`);
  }

  async getFileRaw(fileId, notebookId) {
    // Serve raw file content (for PDFs, videos, audio, etc.)
    const url = `${this.baseUrl}/notebooks/${notebookId}/files/${fileId}/raw/`;
    return url; // Return URL for direct browser access
  }

  async parseFile(file, uploadFileId, notebookId) {
    // Support both single file and multiple files
    const files = Array.isArray(file) ? file : [file];
    const isBatch = Array.isArray(file);
    
    const form = new FormData();
    
    if (isBatch) {
      files.forEach(f => form.append('files', f));
    } else {
      form.append('file', file);
    }
    
    form.append('notebook', notebookId);
    if (uploadFileId) form.append('upload_file_id', uploadFileId);

    const response = await this.request(
      `/notebooks/${notebookId}/files/upload/`,
      { method: 'POST', headers: {'X-CSRFToken': getCookie('csrftoken')}, body: form, credentials: 'include' }
    );
    
    // Return response with batch indicator
    return {
      ...response,
      is_batch: isBatch,
      total_items: isBatch ? files.length : 1
    };
  }

  // createParsingStatusStream(uploadFileId, notebookId, onMessage, onError, onClose) {
  //   const url = `${this.baseUrl}/${notebookId}/files/${uploadFileId}/status/stream`;
  //   const es  = new EventSource(url, { withCredentials: true });
  //   // …
  // }
  createParsingStatusStream(notebookId, uploadFileId, onMessage, onError, onClose) {
    const url = `${this.baseUrl}/notebooks/${notebookId}/files/${uploadFileId}/status/stream`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };

    eventSource.onerror = (err) => {
      onError(err);
      eventSource.close(); // optional but safe
    };

    eventSource.onclose = () => {
      onClose();
    };

    return eventSource;
  }

  async deleteFile(fileId, notebookId) {
    return this.request(`/notebooks/${notebookId}/files/${fileId}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });
  }

  async deleteUpload(uploadFileId, notebookId) {
    return this.deleteFile(uploadFileId, notebookId); // same as deleteFile
  }

  async deleteFileByUploadId(uploadFileId, notebookId) {
    return this.request(`/notebooks/${notebookId}/files/${uploadFileId}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });
  }

  async deleteParsedFile(fileId, notebookId) {
    return this.request(`/notebooks/${notebookId}/files/${fileId}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });
  }

  async getUrlParsingStatus(uploadUrlId, notebookId) {
    // Implement proper URL parsing status check
    return this.request(`/notebooks/${notebookId}/files/${uploadUrlId}/status/`);
  }

  // ─── KNOWLEDGE BASE ───────────────────────────────────────────────────────

  async getKnowledgeBase(notebookId, { limit = 50, offset = 0, content_type = null } = {}) {
    let url = `/notebooks/${notebookId}/knowledge-base/?limit=${limit}&offset=${offset}`;
    if (content_type) {
      url += `&content_type=${content_type}`;
    }
    return this.request(url);
  }

  async linkKnowledgeBaseItem(notebookId, knowledgeBaseItemId, notes = '') {
    return this.request(`/notebooks/${notebookId}/knowledge-base/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({
        knowledge_base_item_id: knowledgeBaseItemId,
        notes: notes
      }),
    });
  }

  async deleteKnowledgeBaseItem(notebookId, knowledgeBaseItemId) {
    return this.request(`/notebooks/${notebookId}/knowledge-base/`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({
        knowledge_base_item_id: knowledgeBaseItemId
      }),
    });
  }

  // ─── STATUS ───────────────────────────────────────────────────────────────

  async getStatus(uploadFileId, notebookId) {
    return this.request(`/notebooks/${notebookId}/files/${uploadFileId}/status/`);
  }

  createStatusStream(uploadFileId, notebookId, onMessage, onError, onClose) {
    const url = `${this.baseUrl}/notebooks/${notebookId}/files/${uploadFileId}/status/stream`;
    const es = new EventSource(url, { withCredentials: true }); // include session

    es.onmessage = e => {
      try {
        onMessage(JSON.parse(e.data));
      } catch (err) {
        console.error('SSE parse error', err);
        onError?.(err);
      }
    };
    es.onerror = err => {
      console.error('SSE error', err);
      onError?.(err);
      es.close();
      onClose?.();
    };
    return es;
  }

  // ─── URL PARSING ─────────────────────────────────────────────────────────

  async parseUrl(url, notebookId, searchMethod = 'cosine', uploadFileId = null) {
    // Support both single URL (string) and multiple URLs (array)
    const urls = Array.isArray(url) ? url : [url];
    const isBatch = Array.isArray(url);
    
    const body = {
      search_method: searchMethod
    };
    
    if (isBatch) {
      body.urls = urls;
    } else {
      body.url = url;
    }
    
    if (uploadFileId) body.upload_url_id = uploadFileId;

    const response = await this.request(`/notebooks/${notebookId}/files/parse_url/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify(body),
    });
    
    // Return response with batch indicator
    return {
      ...response,
      is_batch: isBatch,
      total_items: isBatch ? urls.length : 1
    };
  }

  async parseUrlWithMedia(url, notebookId, searchMethod = 'cosine', uploadFileId = null) {
    // Support both single URL (string) and multiple URLs (array)
    const urls = Array.isArray(url) ? url : [url];
    const isBatch = Array.isArray(url);
    
    const body = {
      search_method: searchMethod,
      media_processing: true
    };
    
    if (isBatch) {
      body.urls = urls;
    } else {
      body.url = url;
    }
    
    if (uploadFileId) body.upload_url_id = uploadFileId;

    const response = await this.request(`/notebooks/${notebookId}/files/parse_url_media/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify(body),
    });
    
    // Return response with batch indicator
    return {
      ...response,
      is_batch: isBatch,
      total_items: isBatch ? urls.length : 1
    };
  }

  // ─── REPORTS & AI GENERATION ─────────────────────────────────────────────

  async getAvailableModels() {
    try {
      const response = await this.request('/notebooks/reports/models/');
      return {
        providers: response.model_providers || ['openai', 'google'],
        retrievers: response.retrievers || ['tavily', 'brave', 'serper', 'you', 'bing', 'duckduckgo', 'searxng'],
        time_ranges: response.time_ranges || ['day', 'week', 'month', 'year'],
      };
    } catch (error) {
      console.warn('Failed to load available models, using defaults:', error);
      // Return default models as fallback
      return {
        providers: ['openai', 'google'],
        retrievers: ['tavily', 'brave', 'serper', 'you', 'bing', 'duckduckgo', 'searxng'],
        time_ranges: ['day', 'week', 'month', 'year'],
      };
    }
  }

  async generateReport(config, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for report generation');
    }
    
    const url = `/notebooks/${notebookId}/report-jobs/`;
    const response = await this.request(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify(config),
    });
    return response;
  }

  async generateReportWithSourceIds(requestData, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for report generation');
    }
    
    const url = `/notebooks/${notebookId}/report-jobs/`;
    const response = await this.request(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify(requestData),
    });
    return response;
  }

  async listReportJobs(notebookId, limit = 50) {
    const response = await this.request(`/notebooks/${notebookId}/report-jobs/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });
    // Transform the response to match expected format (consistent with podcasts)
    return { 
      jobs: response.reports || response.jobs || response || []
    };
  }

  async getReportContent(jobId, notebookId) {
    const response = await this.request(`/notebooks/${notebookId}/report-jobs/${jobId}/content/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });
    return response;
  }

  async getReportStatus(jobId, notebookId) {
    const response = await this.request(`/notebooks/${notebookId}/report-jobs/${jobId}/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });
    return response;
  }

  async listReportFiles(jobId, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for listing report files');
    }
    
    const url = `/notebooks/${notebookId}/report-jobs/${jobId}/files/`;
    const response = await this.request(url);
    return response;
  }

  async downloadReportFile(jobId, notebookId, filename = null) {
    if (!notebookId) {
      throw new Error('notebookId is required for downloading report files');
    }
    
    let url = `/notebooks/${notebookId}/report-jobs/${jobId}/download/`;
    if (filename) {
      url += `?filename=${encodeURIComponent(filename)}`;
    }
    
    const response = await fetch(`${this.baseUrl}${url}`, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.detail || errorMessage;
      } catch (e) {
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    return response.blob();
  }

  async cancelReportJob(jobId, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for cancelling report jobs');
    }
    
    const url = `/notebooks/${notebookId}/report-jobs/${jobId}/cancel/`;
    const response = await this.request(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });
    return response;
  }

  // ─── PODCASTS ────────────────────────────────────────────────────────────

  async generatePodcast(formData, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for podcast generation');
    }
    
    const url = `/notebooks/${notebookId}/podcast-jobs/`;
    const response = await this.request(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: formData,
      // Don't set Content-Type, let browser set it for FormData
    });
    return response;
  }

  async listPodcastJobs(notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for listing podcast jobs');
    }
    
    const url = `/notebooks/${notebookId}/podcast-jobs/`;
    const response = await this.request(url);
    // Transform the response to match expected format
    return { 
      jobs: response.results || response || []
    };
  }

  async cancelPodcastJob(jobId, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for cancelling podcast jobs');
    }
    
    const url = `/notebooks/${notebookId}/podcast-jobs/${jobId}/cancel/`;
    const response = await this.request(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });
    return response;
  }

  async getPodcastJobStatus(jobId, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for getting podcast job status');
    }
    
    const url = `/notebooks/${notebookId}/podcast-jobs/${jobId}/`;
    const response = await this.request(url);
    return response;
  }

  async downloadPodcastAudio(jobId, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for downloading podcast audio');
    }
    
    const url = `/notebooks/${notebookId}/podcast-jobs/${jobId}/audio/`;
    
    const response = await fetch(`${this.baseUrl}${url}`, {
      method: 'GET',
      credentials: 'include', // This includes session cookies for authentication
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.detail || errorMessage;
      } catch (e) {
        // If we can't parse the error response, use the status text
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    return response.blob();
  }

  async deletePodcast(jobId, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for deleting podcast');
    }
    
    const url = `/notebooks/${notebookId}/podcast-jobs/${jobId}/`;
    const response = await this.request(url, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });
    return response;
  }

  async deleteReport(jobId, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for deleting report');
    }
    
    const url = `/notebooks/${notebookId}/report-jobs/${jobId}/`;
    const response = await this.request(url, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });
    return response;
  }

  // Get the correct SSE endpoint for podcast job status
  getPodcastJobStatusStreamUrl(jobId, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for podcast job status stream');
    }
    
    return `${this.baseUrl}/notebooks/${notebookId}/podcast-jobs/${jobId}/stream/`;
  }

  async getReportJobStatus(jobId, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for getting report job status');
    }
    
    const url = `/notebooks/${notebookId}/report-jobs/${jobId}/`;
    const response = await this.request(url);
    return response;
  }

  // Get the correct SSE endpoint for report job status
  getReportJobStatusStreamUrl(jobId, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for report job status stream');
    }
    
    return `${this.baseUrl}/notebooks/${notebookId}/report-jobs/${jobId}/stream/`;
  }

  // ─── HEALTH CHECK ────────────────────────────────────────────────────────

  async healthCheck() {
    try {
      // Simple health check - try to make a basic request
      const response = await fetch(`${this.baseUrl}/health/`, { credentials: 'include' });
      return response.ok;
    } catch (error) {
      console.warn('Health check failed:', error);
      return false;
    }
  }

  // New method for getting batch job status
  async getBatchJobStatus(notebookId, batchJobId) {
    return this.request(`/${notebookId}/batch-jobs/${batchJobId}/status/`);
  }
}

const apiService = new ApiService();
export default apiService;
