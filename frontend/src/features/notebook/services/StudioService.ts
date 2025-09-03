import httpClient, { getCookie } from "@/shared/utils/httpClient";

interface GenerationConfig {
  model?: string;
  temperature?: number;
  max_tokens?: number;
  system_prompt?: string;
  [key: string]: any;
}

/**
 * Service class for studio-related operations
 * Handles all functionality for the Studio panel
 */
class StudioService {

  // ─── REPORTS & AI GENERATION ─────────────────────────────────────────────

  async getAvailableModels(): Promise<{ providers: string[]; retrievers: string[]; time_ranges: string[]; }> {
    try {
      const response = await httpClient.get('/notebooks/reports/models/');
      return {
        providers: response.model_providers || ['openai', 'google'],
        retrievers: response.retrievers || ['tavily', 'brave', 'serper', 'you', 'bing', 'duckduckgo', 'searxng'],
        time_ranges: response.time_ranges || ['day', 'week', 'month', 'year'],
      };
    } catch (error) {
      console.warn('Failed to load available models, using defaults:', error);
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
    
    return httpClient.post(`/notebooks/${notebookId}/report-jobs/`, config);
  }

  async generateReportWithSourceIds(requestData: any, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for report generation');
    }
    
    return httpClient.post(`/notebooks/${notebookId}/report-jobs/`, requestData);
  }

  async listReportJobs(notebookId: string): Promise<{ jobs: any[]; }> {
    const response = await httpClient.get(`/notebooks/${notebookId}/report-jobs/`);
    return { 
      jobs: response.reports || response.jobs || response || []
    };
  }

  async getReportContent(jobId: string, notebookId: string): Promise<any> {
    return httpClient.get(`/notebooks/${notebookId}/report-jobs/${jobId}/content/`);
  }

  async getReportStatus(jobId: string, notebookId: string): Promise<any> {
    return httpClient.get(`/notebooks/${notebookId}/report-jobs/${jobId}/`);
  }

  async listReportFiles(jobId: string, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for listing report files');
    }
    
    return httpClient.get(`/notebooks/${notebookId}/report-jobs/${jobId}/files/`);
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
    
    let response;
    try {
      response = await fetch(`${httpClient.baseUrl}${url}`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'X-CSRFToken': getCookie('csrftoken') ?? '',
        },
        redirect: 'manual'
      });
    } catch (fetchError: unknown) {
      console.error('=== FETCH ERROR ===');
      console.error('Error type:', (fetchError as Error).constructor.name);
      console.error('Error message:', (fetchError as Error).message);
      console.error('Error stack:', (fetchError as Error).stack);
      
      if ((fetchError as Error).name === 'TypeError' && (fetchError as Error).message.includes('Failed to fetch')) {
        console.error('This looks like a network connectivity or CORS issue');
      } else if ((fetchError as Error).message.includes('NetworkError') || (fetchError as Error).message.includes('net::ERR_FAILED')) {
        console.error('This looks like a network error (possibly server down or DNS issue)');
      }
      
      console.error('==================');
      throw new Error(`Network request failed (HTTP 0): ${(fetchError as Error).message}. Check console for details.`);
    }

    if (response.status === 302 || response.status === 301) {
      const redirectUrl = response.headers.get('Location');
      if (redirectUrl) {
        const minioResponse = await fetch(redirectUrl, {
          method: 'GET',
          credentials: 'omit',
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

    if (response.ok) {
      return response.blob();
    }

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
    
    const response = await fetch(`${httpClient.baseUrl}${url}`, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'X-CSRFToken': getCookie('csrftoken') ?? '',
      },
      redirect: 'manual'
    });

    if (response.status === 302 || response.status === 301) {
      const redirectUrl = response.headers.get('Location');
      if (redirectUrl) {
        const minioResponse = await fetch(redirectUrl, {
          method: 'GET',
          credentials: 'omit',
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
    
    return httpClient.post(`/notebooks/${notebookId}/report-jobs/${jobId}/cancel/`);
  }

  async deleteReport(jobId: string, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for deleting report');
    }
    
    return httpClient.delete(`/notebooks/${notebookId}/report-jobs/${jobId}/`);
  }

  async updateReport(jobId: string, notebookId: string, content: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for updating report');
    }
    
    if (!content) {
      throw new Error('content is required for updating report');
    }
    
    return httpClient.put(`/notebooks/${notebookId}/report-jobs/${jobId}/`, { content });
  }

  async getReportJobStatus(jobId: string, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for getting report job status');
    }
    
    return httpClient.get(`/notebooks/${notebookId}/report-jobs/${jobId}/`);
  }

  getReportJobStatusStreamUrl(jobId: string, notebookId: string): string {
    if (!notebookId) {
      throw new Error('notebookId is required for report job status stream');
    }
    
    return `${httpClient.baseUrl}/notebooks/${notebookId}/report-jobs/${jobId}/stream/`;
  }

  // ─── PODCASTS ────────────────────────────────────────────────────────────

  async generatePodcast(formData: FormData, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for podcast generation');
    }
    
    return httpClient.post(`/notebooks/${notebookId}/podcast-jobs/`, formData);
  }

  async listPodcastJobs(notebookId: string): Promise<{ jobs: any[]; }> {
    if (!notebookId) {
      throw new Error('notebookId is required for listing podcast jobs');
    }
    
    const response = await httpClient.get(`/notebooks/${notebookId}/podcast-jobs/`);
    return { 
      jobs: response.results || response || []
    };
  }

  async cancelPodcastJob(jobId: string, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for cancelling podcast jobs');
    }
    
    return httpClient.post(`/notebooks/${notebookId}/podcast-jobs/${jobId}/cancel/`);
  }

  async getPodcastJobStatus(jobId: string, notebookId: string): Promise<any> {
    if (!notebookId) {
      throw new Error('notebookId is required for getting podcast job status');
    }
    
    return httpClient.get(`/notebooks/${notebookId}/podcast-jobs/${jobId}/`);
  }

  async downloadPodcastAudio(jobId: string, notebookId: string): Promise<Blob> {
    if (!notebookId) {
      throw new Error('notebookId is required for downloading podcast audio');
    }
    
    const response = await fetch(`${httpClient.baseUrl}/notebooks/${notebookId}/podcast-jobs/${jobId}/audio/`, {
      method: 'GET',
      credentials: 'include',
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
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    if (!data.audio_url) {
      throw new Error('No audio URL returned from server');
    }
    
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
    
    return httpClient.delete(`/notebooks/${notebookId}/podcast-jobs/${jobId}/`);
  }

  getPodcastJobStatusStreamUrl(jobId: string, notebookId: string): string {
    if (!notebookId) {
      throw new Error('notebookId is required for podcast job status stream');
    }
    
    return `${httpClient.baseUrl}/notebooks/${notebookId}/podcast-jobs/${jobId}/stream/`;
  }
}

export default new StudioService();