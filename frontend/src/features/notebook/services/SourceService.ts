import httpClient from "@/shared/utils/httpClient";

interface ListOptions {
  limit?: number;
  offset?: number;
  content_type?: string | null;
}

interface BatchResponse {
  [key: string]: any;
  is_batch: boolean;
  total_items: number;
}

/**
 * Service class for source-related operations
 * Handles all functionality for the Sources panel
 */
class SourceService {

  // ─── FILES ────────────────────────────────────────────────────────────────

  async listParsedFiles(notebookId: string, { limit = 50, offset = 0 }: ListOptions = {}): Promise<any> {
    return httpClient.get(`/notebooks/${notebookId}/files/?limit=${limit}&offset=${offset}`);
  }

  async getParsedFile(fileId: string, notebookId: string): Promise<any> {
    return httpClient.get(`/notebooks/${notebookId}/files/${fileId}/content/`);
  }

  async getFileContentWithMinIOUrls(fileId: string, notebookId: string, expires: number = 86400): Promise<any> {
    return httpClient.get(`/notebooks/${notebookId}/files/${fileId}/content/?expires=${expires}`);
  }

  getFileRaw(fileId: string, notebookId: string): string {
    return `${httpClient.baseUrl}/notebooks/${notebookId}/files/${fileId}/raw/`;
  }

  async parseFile(file: File | File[], uploadFileId: string, notebookId: string): Promise<BatchResponse> {
    const files = Array.isArray(file) ? file : [file];
    const isBatch = Array.isArray(file);
    
    const form = new FormData();
    
    if (isBatch) {
      files.forEach(f => form.append('files', f));
    } else {
      form.append('file', file);
    }
    
    if (uploadFileId) form.append('upload_file_id', uploadFileId);

    const response = await httpClient.post(`/notebooks/${notebookId}/files/`, form);
    
    return {
      ...response,
      is_batch: isBatch,
      total_items: isBatch ? files.length : 1
    };
  }

  async deleteFile(fileId: string, notebookId: string): Promise<any> {
    return httpClient.delete(`/notebooks/${notebookId}/files/${fileId}/`);
  }

  async deleteFileByUploadId(uploadFileId: string, notebookId: string): Promise<any> {
    return httpClient.delete(`/notebooks/${notebookId}/files/${uploadFileId}/`);
  }

  async deleteParsedFile(fileId: string, notebookId: string): Promise<any> {
    return httpClient.delete(`/notebooks/${notebookId}/files/${fileId}/`);
  }

  async getUrlParsingStatus(uploadUrlId: string, notebookId: string): Promise<any> {
    return httpClient.get(`/notebooks/${notebookId}/files/${uploadUrlId}/status/`);
  }

  // ─── KNOWLEDGE BASE ───────────────────────────────────────────────────────

  async getKnowledgeBase(notebookId: string, { limit = 50, offset = 0, content_type = null }: ListOptions = {}): Promise<any> {
    let url = `/notebooks/${notebookId}/knowledge/?limit=${limit}&offset=${offset}`;
    if (content_type) {
      url += `&content_type=${content_type}`;
    }
    return httpClient.get(url);
  }

  async linkKnowledgeBaseItem(notebookId: string, knowledgeBaseItemId: string, notes: string = ''): Promise<any> {
    return httpClient.post(`/notebooks/${notebookId}/knowledge/`, {
      knowledge_base_item_id: knowledgeBaseItemId,
      notes: notes
    });
  }

  async deleteKnowledgeBaseItem(notebookId: string, knowledgeBaseItemId: string): Promise<any> {
    return httpClient.delete(`/notebooks/${notebookId}/knowledge/${knowledgeBaseItemId}/`);
  }

  // ─── STATUS ───────────────────────────────────────────────────────────────

  async getStatus(uploadFileId: string, notebookId: string): Promise<any> {
    return httpClient.get(`/notebooks/${notebookId}/files/${uploadFileId}/status/`);
  }

  // ─── URL PARSING ─────────────────────────────────────────────────────────

  async parseUrl(url: string | string[], notebookId: string, searchMethod: string = 'cosine', uploadFileId: string | null = null): Promise<BatchResponse> {
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

    const response = await httpClient.post(`/notebooks/${notebookId}/files/parse_url/`, body);
    
    return {
      ...response,
      is_batch: isBatch,
      total_items: isBatch ? urls.length : 1
    };
  }

  async parseUrlWithMedia(url: string | string[], notebookId: string, searchMethod: string = 'cosine', uploadFileId: string | null = null): Promise<BatchResponse> {
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

    const response = await httpClient.post(`/notebooks/${notebookId}/files/parse_url_with_media/`, body);
    
    return {
      ...response,
      is_batch: isBatch,
      total_items: isBatch ? urls.length : 1
    };
  }

  async parseDocumentUrl(url: string | string[], notebookId: string, searchMethod: string = 'cosine', uploadFileId: string | null = null): Promise<BatchResponse> {
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

    const response = await httpClient.post(`/notebooks/${notebookId}/files/parse_document_url/`, body);
    
    return {
      ...response,
      is_batch: isBatch,
      total_items: isBatch ? urls.length : 1
    };
  }

  // ─── BATCH OPERATIONS ────────────────────────────────────────────────────

  async getBatchJobStatus(notebookId: string, batchJobId: string): Promise<any> {
    return httpClient.get(`/notebooks/${notebookId}/batches/${batchJobId}/`);
  }

  // Note: Video image extraction endpoint needs to be implemented on backend
  async extractVideoImages(notebookId: string, data: any = {}): Promise<any> {
    throw new Error('Video image extraction endpoint not yet implemented on backend');
  }
}

export default new SourceService();