/**
 * Core API types and interfaces
 */

export interface ApiResponse<T> {
  data: T;
  meta?: {
    pagination?: PaginationMeta;
    filters?: FiltersMeta;
  };
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  data: T[];
  meta: {
    pagination: {
      count: number;
      page: number;
      pages: number;
      pageSize: number;
      hasNext: boolean;
      hasPrevious: boolean;
    };
  };
}

export interface PaginationMeta {
  count: number;
  page: number;
  pages: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface FiltersMeta {
  search?: string;
  ordering?: string;
  [key: string]: any;
}

export interface PaginationParams {
  page?: number;
  pageSize?: number;
  search?: string;
  ordering?: string;
}

export interface RequestConfig extends RequestInit {
  params?: Record<string, any>;
  timeout?: number;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: Response
  ) {
    super(message);
    this.name = 'ApiError';
  }
}