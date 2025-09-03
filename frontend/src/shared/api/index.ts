/**
 * API library exports
 */

// Core API client
export { apiClient, legacyApiClient, ApiClient } from './client';

// Types
export type {
  ApiResponse,
  PaginatedResponse,
  PaginationMeta,
  FiltersMeta,
  PaginationParams,
  RequestConfig,
} from './types';

export { ApiError } from './types';

// Resources
export { notebooksApi } from './resources/notebooks';
export type {
  Notebook,
  CreateNotebookRequest,
  UpdateNotebookRequest,
  NotebookStats,
  GetNotebooksParams,
  Source,
  CreateSourceRequest,
  UpdateSourceRequest,
  ProcessUrlRequest,
  AddTextRequest,
  ChatMessage,
  ChatResponse,
  KnowledgeBaseItem,
  KnowledgeBaseImage,
} from './resources/notebooks';

// TODO: Add other resources as they are created
// export { reportsApi } from './resources/reports';
// export { podcastsApi } from './resources/podcasts';
// export { conferencesApi } from './resources/conferences';