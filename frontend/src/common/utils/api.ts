import { config } from '@/config';

const API_BASE_URL = config.API_BASE_URL;

// Helper to get CSRF token from cookie
function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

// Request options interface
interface RequestOptions extends RequestInit {
  headers?: Record<string, string>;
}

// File listing options
interface ListOptions {
  limit?: number;
  offset?: number;
  content_type?: string | null;
}

// Generation config interfaces
interface GenerationConfig {
  model?: string;
  temperature?: number;
  max_tokens?: number;
  system_prompt?: string;
  [key: string]: any;
}

// Batch response interface
interface BatchResponse {
  [key: string]: any;
  is_batch: boolean;
  total_items: number;
}

// Stream callback types
type StreamCallback = (data: any) => void;
type StreamErrorCallback = (error: any) => void;
type StreamCloseCallback = () => void;

class ApiService {
  public baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  async request<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const url = endpoint.startsWith('http')
      ? endpoint
      : `${this.baseUrl}${endpoint}`;

    const config: RequestInit = {
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
              msg = err.detail.map((d: any) => `${d.loc.join('.')} – ${d.msg}`).join('; ');
            } else {
              msg = err.detail;
            }
          } else if (err.error) {
            // Handle StandardAPIView error responses (notebooks app)
            msg = err.error;
          } else if (err.message) {
            // Handle other possible error message fields
            msg = err.message;
          }
        } catch {}
        throw new Error(msg);
      }
      
      // Handle 204 No Content responses (common for DELETE operations)
      if (response.status === 204) {
        return { success: true } as T;
      }
      
      return await response.json();
    } catch (e) {
      console.error('API request failed:', e);
      throw e;
    }
  }

  // ─── STANDARD HTTP METHODS ──────────────────────────────────────────────
  
  async get<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    return this.request(endpoint, {
      method: 'GET',
      ...options
    });
  }

  async post<T = any>(endpoint: string, data: any = null, options: RequestOptions = {}): Promise<T> {
    const config = {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
        ...options.headers
      },
      ...options
    };

    // Handle different data types
    if (data instanceof FormData) {
      config.body = data;
    } else if (data !== null) {
      config.body = JSON.stringify(data);
      config.headers = {
        'Content-Type': 'application/json',
        ...config.headers
      };
    }

    return this.request(endpoint, config);
  }

  async put<T = any>(endpoint: string, data: any = null, options: RequestOptions = {}): Promise<T> {
    const config = {
      method: 'PUT',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
        ...options.headers
      },
      ...options
    };

    if (data instanceof FormData) {
      config.body = data;
    } else if (data !== null) {
      config.body = JSON.stringify(data);
      config.headers = {
        'Content-Type': 'application/json',
        ...config.headers
      };
    }

    return this.request(endpoint, config);
  }

  async delete<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    return this.request(endpoint, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
        ...options.headers
      },
      ...options
    });
  }

  async patch<T = any>(endpoint: string, data: any = null, options: RequestOptions = {}): Promise<T> {
    const config = {
      method: 'PATCH',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
        ...options.headers
      },
      ...options
    };

    if (data instanceof FormData) {
      config.body = data;
    } else if (data !== null) {
      config.body = JSON.stringify(data);
      config.headers = {
        'Content-Type': 'application/json',
        ...config.headers
      };
    }

    return this.request(endpoint, config);
  }

  // ─── FILES ────────────────────────────────────────────────────────────────

  async listParsedFiles(notebookId: string, { limit = 50, offset = 0 }: ListOptions = {}): Promise<any> {
    return this.request(`/notebooks/${notebookId}/files/?limit=${limit}&offset=${offset}`);
  }

  async getParsedFile(fileId: string): Promise<any> {
    // Get file content from knowledge base item
    // Use the correct notebooks endpoint structure
    return this.request(`/notebooks/files/${fileId}/content/`);
  }

  async getFileContentWithMinIOUrls(fileId: string, expires: number = 86400): Promise<any> {
    // Get file content with direct MinIO pre-signed URLs for images
    return this.request(`/notebooks/files/${fileId}/content/minio/?expires=${expires}`);
  }

  async getFileRaw(fileId: string, notebookId: string): Promise<string> {
    // Serve raw file content (for PDFs, videos, audio, etc.)
    const url = `${this.baseUrl}/notebooks/${notebookId}/files/${fileId}/raw/`;
    return url; // Return URL for direct browser access
  }

  async parseFile(file: File | File[], uploadFileId: string, notebookId: string): Promise<BatchResponse> {
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
      { method: 'POST', headers: {'X-CSRFToken': getCookie('csrftoken') ?? ''}, body: form, credentials: 'include' }
    );
    
    // Return response with batch indicator
    return {
      ...response,
      is_batch: isBatch,
      total_items: isBatch ? files.length : 1
    };
  }

  // Legacy method - deprecated in favor of fetchEventSource in hooks
  // createParsingStatusStream(uploadFileId, notebookId, onMessage, onError, onClose) {
  //   const url = `${this.baseUrl}/${notebookId}/files/${uploadFileId}/status/stream`;
  //   const es  = new EventSource(url, { withCredentials: true });
  //   // …
  // }

  async deleteFile(fileId: string, notebookId: string): Promise<any> {
    return this.request(`/notebooks/${notebookId}/files/${fileId}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
    });
  }

  async deleteUpload(uploadFileId: string, notebookId: string): Promise<any> {
    return this.deleteFile(uploadFileId, notebookId); // same as deleteFile
  }

  async deleteFileByUploadId(uploadFileId: string, notebookId: string): Promise<any> {
    return this.request(`/notebooks/${notebookId}/files/${uploadFileId}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
    });
  }

  async deleteParsedFile(fileId: string, notebookId: string): Promise<any> {
    return this.request(`/notebooks/${notebookId}/files/${fileId}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
    });
  }

  async getUrlParsingStatus(uploadUrlId: string, notebookId: string): Promise<any> {
    // Implement proper URL parsing status check
    return this.request(`/notebooks/${notebookId}/files/${uploadUrlId}/status/`);
  }

  // ─── KNOWLEDGE BASE ───────────────────────────────────────────────────────

  async getKnowledgeBase(notebookId: string, { limit = 50, offset = 0, content_type = null }: ListOptions = {}): Promise<any> {
    let url = `/notebooks/${notebookId}/knowledge-base/?limit=${limit}&offset=${offset}`;
    if (content_type) {
      url += `&content_type=${content_type}`;
    }
    return this.request(url);
  }

  async linkKnowledgeBaseItem(notebookId: string, knowledgeBaseItemId: string, notes: string = ''): Promise<any> {
    return this.request(`/notebooks/${notebookId}/knowledge-base/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
      body: JSON.stringify({
        knowledge_base_item_id: knowledgeBaseItemId,
        notes: notes
      }),
    });
  }

  async deleteKnowledgeBaseItem(notebookId: string, knowledgeBaseItemId: string): Promise<any> {
    return this.request(`/notebooks/${notebookId}/knowledge-base/`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
      body: JSON.stringify({
        knowledge_base_item_id: knowledgeBaseItemId
      }),
    });
  }

  // ─── STATUS ───────────────────────────────────────────────────────────────

  async getStatus(uploadFileId: string, notebookId: string): Promise<any> {
    return this.request(`/notebooks/${notebookId}/files/${uploadFileId}/status/`);
  }

  // Legacy method - deprecated in favor of fetchEventSource in hooks
  // createStatusStream(uploadFileId: string, notebookId: string, onMessage: StreamCallback, onError?: StreamErrorCallback, onClose?: StreamCloseCallback): EventSource {
  //   const url = `${this.baseUrl}/notebooks/${notebookId}/files/${uploadFileId}/status/stream`;
  //   const es = new EventSource(url, { withCredentials: true }); // include session
  //   ...
  // }

  // ─── URL PARSING ─────────────────────────────────────────────────────────

  async parseUrl(url: string | string[], notebookId: string, searchMethod: string = 'cosine', uploadFileId: string | null = null): Promise<BatchResponse> {
    // Support both single URL (string) and multiple URLs (array)
    const urls = Array.isArray(url) ? url : [url];
    const isBatch = Array.isArray(url);
    
    const body: any = {
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
        'X-CSRFToken': getCookie('csrftoken') ?? '',
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

  async parseUrlWithMedia(url: string | string[], notebookId: string, searchMethod: string = 'cosine', uploadFileId: string | null = null): Promise<BatchResponse> {
    // Support both single URL (string) and multiple URLs (array)
    const urls = Array.isArray(url) ? url : [url];
    const isBatch = Array.isArray(url);
    
    const body: any = {
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
        'X-CSRFToken': getCookie('csrftoken') ?? '',
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

  async parseDocumentUrl(url: string | string[], notebookId: string, searchMethod: string = 'cosine', uploadFileId: string | null = null): Promise<BatchResponse> {
    // Support both single URL (string) and multiple URLs (array)
    const urls = Array.isArray(url) ? url : [url];
    const isBatch = Array.isArray(url);
    
    const body: any = {
      search_method: searchMethod,
      document_processing: true
    };
    
    if (isBatch) {
      body.urls = urls;
    } else {
      body.url = url;
    }
    
    if (uploadFileId) body.upload_url_id = uploadFileId;

    const response = await this.request(`/notebooks/${notebookId}/files/parse_document_url/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken') ?? '',
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

  async getAvailableModels(): Promise<{ providers: string[]; retrievers: string[]; time_ranges: string[]; }> {
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

  async generateReport(config: GenerationConfig, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for report generation');
    }
    
    const url = `/notebooks/${notebookId}/report-jobs/`;
    const response = await this.request(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
      body: JSON.stringify(config),
    });
    return response;
  }

  async generateReportWithSourceIds(requestData: any, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for report generation');
    }
    
    const url = `/notebooks/${notebookId}/report-jobs/`;
    const response = await this.request(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
      body: JSON.stringify(requestData),
    });
    return response;
  }

  async listReportJobs(notebookId: string): Promise<{ jobs: any[]; }> {
    const response = await this.request(`/notebooks/${notebookId}/report-jobs/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
    });
    // Transform the response to match expected format (consistent with podcasts)
    return { 
      jobs: response.reports || response.jobs || response || []
    };
  }

  async getReportContent(jobId: string, notebookId: string): Promise<any> {
    const response = await this.request(`/notebooks/${notebookId}/report-jobs/${jobId}/content/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
    });
    return response;
  }

  async getReportStatus(jobId: string, notebookId: string): Promise<any> {
    const response = await this.request(`/notebooks/${notebookId}/report-jobs/${jobId}/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
    });
    return response;
  }

  async listReportFiles(jobId: string, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for listing report files');
    }
    
    const url = `/notebooks/${notebookId}/report-jobs/${jobId}/files/`;
    const response = await this.request(url);
    return response;
  }

  async downloadReportFile(jobId: string, notebookId: string, filename: string | null = null): Promise<Blob> {
    if (!notebookId) {
      throw new Error('notebookId is required for downloading report files');
    }
    
    if (!jobId) {
      throw new Error('jobId is required for downloading report files');
    }
    
    let url = `/notebooks/${notebookId}/report-jobs/${jobId}/download/`;
    if (filename) {
      url += `?filename=${encodeURIComponent(filename)}`;
    }
    
    
    // Always use manual redirect handling to avoid CORS issues with MinIO
    let response;
    try {
      response = await fetch(`${this.baseUrl}${url}`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'X-CSRFToken': getCookie('csrftoken') ?? '',
        },
        redirect: 'manual' // Always handle redirects manually
      });
    } catch (fetchError) {
      console.error('=== FETCH ERROR ===');
      console.error('Error type:', fetchError.constructor.name);
      console.error('Error message:', fetchError.message);
      console.error('Error stack:', fetchError.stack);
      
      // Special handling for common error types
      if (fetchError.name === 'TypeError' && fetchError.message.includes('Failed to fetch')) {
        console.error('This looks like a network connectivity or CORS issue');
      } else if (fetchError.message.includes('NetworkError') || fetchError.message.includes('net::ERR_FAILED')) {
        console.error('This looks like a network error (possibly server down or DNS issue)');
      }
      
      console.error('==================');
      throw new Error(`Network request failed (HTTP 0): ${fetchError.message}. Check console for details.`);
    }


    // Handle redirects to MinIO
    if (response.status === 302 || response.status === 301) {
      const redirectUrl = response.headers.get('Location');
      if (redirectUrl) {
        
        // Fetch MinIO URL without credentials to avoid CORS
        const minioResponse = await fetch(redirectUrl, {
          method: 'GET',
          credentials: 'omit', // Critical: no credentials for MinIO
          mode: 'cors'
        });
        
        
        if (minioResponse.ok) {
          return minioResponse.blob();
        } else {
          throw new Error(`MinIO download failed: ${minioResponse.status} ${minioResponse.statusText}`);
        }
      } else {
        throw new Error('No redirect URL found in response headers');
      }
    }

    // Handle direct responses (no redirect)
    if (response.ok) {
      return response.blob();
    }

    // Handle errors
    let errorMessage = `HTTP ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.error || errorData.detail || errorMessage;
    } catch (e) {
      errorMessage = response.statusText || errorMessage;
    }
    throw new Error(errorMessage);
  }

  async downloadReportPdf(jobId: string, notebookId: string): Promise<Blob> {
    if (!notebookId) {
      throw new Error('notebookId is required for downloading report PDF');
    }
    
    const url = `/notebooks/${notebookId}/report-jobs/${jobId}/download-pdf/`;
    
    const response = await fetch(`${this.baseUrl}${url}`, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
      redirect: 'manual' // Handle redirects manually to avoid CORS issues with MinIO
    });

    if (response.status === 302 || response.status === 301) {
      // Handle redirect to MinIO URL - fetch without credentials to avoid CORS
      const redirectUrl = response.headers.get('Location');
      if (redirectUrl) {
        const minioResponse = await fetch(redirectUrl, {
          method: 'GET',
          credentials: 'omit', // Don't send credentials to MinIO
        });
        
        if (!minioResponse.ok) {
          throw new Error(`MinIO PDF download failed: ${minioResponse.status}`);
        }
        
        return minioResponse.blob();
      }
    }

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

  async cancelReportJob(jobId: string, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for cancelling report jobs');
    }
    
    const url = `/notebooks/${notebookId}/report-jobs/${jobId}/cancel/`;
    const response = await this.request(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
    });
    return response;
  }

  // ─── PODCASTS ────────────────────────────────────────────────────────────

  async generatePodcast(formData: FormData, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for podcast generation');
    }
    
    const url = `/notebooks/${notebookId}/podcast-jobs/`;
    const response = await this.request(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
      body: formData,
      // Don't set Content-Type, let browser set it for FormData
    });
    return response;
  }

  async listPodcastJobs(notebookId: string): Promise<{ jobs: any[]; }> {
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

  async cancelPodcastJob(jobId: string, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for cancelling podcast jobs');
    }
    
    const url = `/notebooks/${notebookId}/podcast-jobs/${jobId}/cancel/`;
    const response = await this.request(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
    });
    return response;
  }

  async getPodcastJobStatus(jobId: string, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for getting podcast job status');
    }
    
    const url = `/notebooks/${notebookId}/podcast-jobs/${jobId}/`;
    const response = await this.request(url);
    return response;
  }

  async downloadPodcastAudio(jobId: string, notebookId: string): Promise<Blob> {
    if (!notebookId) {
      throw new Error('notebookId is required for downloading podcast audio');
    }
    
    const url = `/notebooks/${notebookId}/podcast-jobs/${jobId}/audio/`;
    
    const response = await fetch(`${this.baseUrl}${url}`, {
      method: 'GET',
      credentials: 'include', // This includes session cookies for authentication
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
        'Accept': 'application/json',
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

    const data = await response.json();
    if (!data.audio_url) {
      throw new Error('No audio URL returned from server');
    }
    
    // Download the file from the pre-signed URL
    const audioResponse = await fetch(data.audio_url);
    if (!audioResponse.ok) {
      throw new Error('Failed to download audio file');
    }
    
    return audioResponse.blob();
  }

  async deletePodcast(jobId: string, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for deleting podcast');
    }
    
    const url = `/notebooks/${notebookId}/podcast-jobs/${jobId}/`;
    const response = await this.request(url, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
    });
    return response;
  }

  async deleteReport(jobId: string, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for deleting report');
    }
    
    const url = `/notebooks/${notebookId}/report-jobs/${jobId}/`;
    const response = await this.request(url, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
    });
    return response;
  }

  async updateReport(jobId: string, notebookId: string, content: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for updating report');
    }
    
    if (!content) {
      throw new Error('content is required for updating report');
    }
    
    
    const url = `/notebooks/${notebookId}/report-jobs/${jobId}/`;
    const result = await this.put(url, { content });
    
    
    return result;
  }

  // Get the correct SSE endpoint for podcast job status
  getPodcastJobStatusStreamUrl(jobId: string, notebookId: string): string {
    if (!notebookId) {
      throw new Error('notebookId is required for podcast job status stream');
    }
    
    return `${this.baseUrl}/notebooks/${notebookId}/podcast-jobs/${jobId}/stream/`;
  }

  async getReportJobStatus(jobId: string, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for getting report job status');
    }
    
    const url = `/notebooks/${notebookId}/report-jobs/${jobId}/`;
    const response = await this.request(url);
    return response;
  }

  // Get the correct SSE endpoint for report job status
  getReportJobStatusStreamUrl(jobId: string, notebookId: string): string {
    if (!notebookId) {
      throw new Error('notebookId is required for report job status stream');
    }
    
    return `${this.baseUrl}/notebooks/${notebookId}/report-jobs/${jobId}/stream/`;
  }

  // ─── HEALTH CHECK ────────────────────────────────────────────────────────

  async healthCheck(): Promise<boolean> {
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
  async getBatchJobStatus(notebookId: string, batchJobId: string): Promise<any> {
    return this.request(`/notebooks/${notebookId}/batch-jobs/${batchJobId}/status/`);
  }

  async extractVideoImages(notebookId: string, data: any = {}): Promise<any> {
    return this.post(`/notebooks/${notebookId}/extraction/video_image_extraction/`, data);
  }
}

const apiService = new ApiService();
export default apiService;
