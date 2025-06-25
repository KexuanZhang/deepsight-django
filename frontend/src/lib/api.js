import { config } from '../config.js';

const API_BASE_URL = `${config.API_BASE_URL}/notebooks`;

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
    return this.request(`/${notebookId}/files/?limit=${limit}&offset=${offset}`);
  }

  async getParsedFile(fileId) {
    // Get file content from knowledge base item
    // Use the correct notebooks endpoint structure
    return this.request(`${config.API_BASE_URL}/notebooks/files/${fileId}/content/`);
  }

  async getFileRaw(fileId, notebookId) {
    // Serve raw file content (for PDFs, videos, audio, etc.)
    const url = `${this.baseUrl}/${notebookId}/files/${fileId}/raw/`;
    return url; // Return URL for direct browser access
  }

  async parseFile(file, uploadFileId, notebookId) {
    const form = new FormData();
    form.append('file', file);
    form.append('notebook', notebookId);
    console.log(form)
    if (uploadFileId) form.append('upload_file_id', uploadFileId);


    return this.request(
      `/${notebookId}/files/upload/`,
      { method: 'POST', headers: {'X-CSRFToken': getCookie('csrftoken')}, body: form, credentials: 'include' }
    );
  }

  // createParsingStatusStream(uploadFileId, notebookId, onMessage, onError, onClose) {
  //   const url = `${this.baseUrl}/${notebookId}/files/${uploadFileId}/status/stream`;
  //   const es  = new EventSource(url, { withCredentials: true });
  //   // …
  // }
  createParsingStatusStream(notebookId, uploadFileId, onMessage, onError, onClose) {
  const url = `${config.API_BASE_URL}/notebooks/${notebookId}/files/${uploadFileId}/status/stream`;
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
    return this.request(`/${notebookId}/files/${fileId}/`, {
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
    return this.request(`/${notebookId}/files/${uploadFileId}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });
  }

  async deleteParsedFile(fileId, notebookId) {
    return this.request(`/${notebookId}/files/${fileId}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });
  }

  async getUrlParsingStatus(uploadUrlId) {
    // This is a placeholder - URL parsing might use a different endpoint
    return { success: false, error: 'URL parsing status not implemented' };
  }

  // ─── KNOWLEDGE BASE ───────────────────────────────────────────────────────

  async getKnowledgeBase(notebookId, { limit = 50, offset = 0, content_type = null } = {}) {
    let url = `/${notebookId}/knowledge-base/?limit=${limit}&offset=${offset}`;
    if (content_type) {
      url += `&content_type=${content_type}`;
    }
    return this.request(url);
  }

  async linkKnowledgeBaseItem(notebookId, knowledgeBaseItemId, notes = '') {
    return this.request(`/${notebookId}/knowledge-base/`, {
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
    return this.request(`/${notebookId}/knowledge-base/`, {
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
    return this.request(`/${notebookId}/files/${uploadFileId}/status/`);
  }

  createStatusStream(uploadFileId, notebookId, onMessage, onError, onClose) {
    const url = `${this.baseUrl}/${notebookId}/files/${uploadFileId}/status/stream`;
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

  async parseUrl(url, searchMethod = 'cosine', uploadFileId = null) {
    const body = {
      url: url,
      search_method: searchMethod
    };
    if (uploadFileId) body.upload_file_id = uploadFileId;

    return this.request('/parse-url/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify(body),
    });
  }

  async parseUrlWithMedia(url, searchMethod = 'cosine', uploadFileId = null) {
    const body = {
      url: url,
      search_method: searchMethod,
      media_processing: true
    };
    if (uploadFileId) body.upload_file_id = uploadFileId;

    return this.request('/parse-url/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify(body),
    });
  }

  // ─── REPORTS & AI GENERATION ─────────────────────────────────────────────

  async getAvailableModels() {
    // Return default models as fallback
    return {
      providers: ['openai', 'google'],
      retrievers: ['tavily', 'brave', 'serper', 'you', 'bing', 'duckduckgo', 'searxng'],
      time_ranges: ['day', 'week', 'month', 'year'],
    };
  }

  async generateReport(config) {
    // Placeholder for report generation
    console.warn('generateReport not implemented yet');
    return { job_id: 'mock_job_' + Date.now() };
  }

  async generateReportWithSourceIds(requestData) {
    // Placeholder for report generation with source IDs
    console.warn('generateReportWithSourceIds not implemented yet');
    return { job_id: 'mock_job_' + Date.now() };
  }

  async listJobs(limit = 50) {
    // Placeholder for listing jobs
    console.warn('listJobs not implemented yet');
    return { jobs: [] };
  }

  async getReportContent(jobId) {
    // Placeholder for getting report content
    console.warn('getReportContent not implemented yet');
    return { content: `# Mock Report\n\nThis is a placeholder report for job ${jobId}.` };
  }

  async listJobFiles(jobId) {
    // Placeholder for listing job files
    console.warn('listJobFiles not implemented yet');
    return { files: [] };
  }

  async downloadFile(jobId, filename = null) {
    // Placeholder for file download
    console.warn('downloadFile not implemented yet');
    const content = `Mock file content for job ${jobId}`;
    return new Blob([content], { type: 'text/plain' });
  }

  async cancelJob(jobId) {
    // Placeholder for canceling jobs
    console.warn('cancelJob not implemented yet');
    return { success: true };
  }

  // ─── PODCASTS ────────────────────────────────────────────────────────────

  async generatePodcast(formData, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for podcast generation');
    }
    
    const url = `${config.API_BASE_URL}/notebooks/${notebookId}/jobs/`;
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
    
    const url = `${config.API_BASE_URL}/notebooks/${notebookId}/jobs/`;
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
    
    const url = `${config.API_BASE_URL}/notebooks/${notebookId}/jobs/${jobId}/cancel/`;
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
    
    const url = `${config.API_BASE_URL}/notebooks/${notebookId}/jobs/${jobId}/`;
    const response = await this.request(url);
    return response;
  }

  async downloadPodcastAudio(jobId, notebookId) {
    if (!notebookId) {
      throw new Error('notebookId is required for downloading podcast audio');
    }
    
    const url = `${config.API_BASE_URL}/notebooks/${notebookId}/jobs/${jobId}/audio/`;
    
    const response = await fetch(url, {
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
    
    const url = `${config.API_BASE_URL}/notebooks/${notebookId}/jobs/${jobId}/`;
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
    
    return `${config.API_BASE_URL}/notebooks/${notebookId}/jobs/${jobId}/stream/`;
  }

  // ─── HEALTH CHECK ────────────────────────────────────────────────────────

  async healthCheck() {
    try {
      // Simple health check - try to make a basic request
      const response = await fetch(`${config.API_BASE_URL}/health/`, { credentials: 'include' });
      return response.ok;
    } catch (error) {
      console.warn('Health check failed:', error);
      return false;
    }
  }
}

const apiService = new ApiService();
export default apiService;
