/**
 * API Migration Utility for gradual transition from legacy to API v1
 * Supports feature flags and parallel endpoint support
 */

import { config } from "@/config";

// Feature flags for API migration
const API_MIGRATION_FLAGS = {
  USE_V1_NOTEBOOKS: true,
  USE_V1_SOURCES: true, 
  USE_V1_CHAT: true,
  USE_V1_REPORTS: true,
  USE_V1_PODCASTS: true,
  USE_V1_AUTH: false, // Keep legacy auth for now
} as const;

// Endpoint mapping from legacy to v1
const ENDPOINT_MAPPING = {
  // Notebooks
  'GET /notebooks/': 'GET /api/v1/notebooks/',
  'POST /notebooks/': 'POST /api/v1/notebooks/',
  'GET /notebooks/{id}/': 'GET /api/v1/notebooks/{id}/',
  'PUT /notebooks/{id}/': 'PUT /api/v1/notebooks/{id}/',
  'DELETE /notebooks/{id}/': 'DELETE /api/v1/notebooks/{id}/',
  
  // Sources (formerly files)
  'GET /notebooks/{id}/files/': 'GET /api/v1/notebooks/{id}/sources/',
  'POST /notebooks/{id}/files/upload/': 'POST /api/v1/notebooks/{id}/sources/',
  'DELETE /notebooks/{id}/files/{fileId}/': 'DELETE /api/v1/notebooks/{id}/sources/{sourceId}/',
  'PUT /notebooks/{id}/files/{fileId}/': 'PUT /api/v1/notebooks/{id}/sources/{sourceId}/',
  
  // Chat
  'POST /notebooks/{id}/chat/': 'POST /api/v1/notebooks/{id}/chat/',
  'GET /notebooks/{id}/chat/history/': 'GET /api/v1/notebooks/{id}/chat/history/',
  
  // Reports
  'GET /notebooks/{id}/reports/': 'GET /api/v1/notebooks/{id}/reports/',
  'POST /notebooks/{id}/reports/': 'POST /api/v1/notebooks/{id}/reports/',
  'GET /notebooks/{id}/reports/{reportId}/': 'GET /api/v1/notebooks/{id}/reports/{reportId}/',
  
  // Podcasts
  'GET /notebooks/{id}/podcasts/': 'GET /api/v1/notebooks/{id}/podcasts/',
  'POST /notebooks/{id}/podcasts/': 'POST /api/v1/notebooks/{id}/podcasts/',
  'GET /notebooks/{id}/podcasts/{podcastId}/': 'GET /api/v1/notebooks/{id}/podcasts/{podcastId}/',
} as const;

type EndpointKey = keyof typeof ENDPOINT_MAPPING;
type FeatureFlag = keyof typeof API_MIGRATION_FLAGS;

/**
 * Migration adapter that determines which endpoint to use
 */
export class ApiMigrationAdapter {
  private static instance: ApiMigrationAdapter;
  
  static getInstance(): ApiMigrationAdapter {
    if (!ApiMigrationAdapter.instance) {
      ApiMigrationAdapter.instance = new ApiMigrationAdapter();
    }
    return ApiMigrationAdapter.instance;
  }

  /**
   * Get the appropriate endpoint based on migration flags
   */
  getEndpoint(legacyEndpoint: string, notebookId?: string, resourceId?: string): string {
    // Substitute path parameters
    let endpoint = legacyEndpoint;
    if (notebookId) {
      endpoint = endpoint.replace('{id}', notebookId);
    }
    if (resourceId) {
      endpoint = endpoint.replace('{fileId}', resourceId)
                         .replace('{sourceId}', resourceId)
                         .replace('{reportId}', resourceId)
                         .replace('{podcastId}', resourceId);
    }

    const endpointKey = endpoint as EndpointKey;
    const v1Endpoint = ENDPOINT_MAPPING[endpointKey];
    
    if (!v1Endpoint) {
      console.warn(`No v1 mapping found for endpoint: ${endpoint}`);
      return this.buildFullUrl(endpoint);
    }

    // Determine which version to use based on feature flags
    const shouldUseV1 = this.shouldUseV1Endpoint(endpoint);
    const finalEndpoint = shouldUseV1 ? v1Endpoint.replace(/^[A-Z]+ /, '') : endpoint.replace(/^[A-Z]+ /, '');
    
    return this.buildFullUrl(finalEndpoint);
  }

  /**
   * Check if we should use v1 endpoint based on feature flags
   */
  private shouldUseV1Endpoint(endpoint: string): boolean {
    if (endpoint.includes('/notebooks/') && !endpoint.includes('/chat/') && !endpoint.includes('/reports/') && !endpoint.includes('/podcasts/')) {
      return API_MIGRATION_FLAGS.USE_V1_NOTEBOOKS;
    }
    
    if (endpoint.includes('/files/') || endpoint.includes('/sources/')) {
      return API_MIGRATION_FLAGS.USE_V1_SOURCES;
    }
    
    if (endpoint.includes('/chat/')) {
      return API_MIGRATION_FLAGS.USE_V1_CHAT;
    }
    
    if (endpoint.includes('/reports/')) {
      return API_MIGRATION_FLAGS.USE_V1_REPORTS;
    }
    
    if (endpoint.includes('/podcasts/')) {
      return API_MIGRATION_FLAGS.USE_V1_PODCASTS;
    }
    
    if (endpoint.includes('/users/') || endpoint.includes('/auth/')) {
      return API_MIGRATION_FLAGS.USE_V1_AUTH;
    }

    return false;
  }

  /**
   * Build full URL with base API URL
   */
  private buildFullUrl(endpoint: string): string {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    return `${config.API_BASE_URL}${cleanEndpoint}`;
  }

  /**
   * Get migration status for debugging
   */
  getMigrationStatus() {
    return {
      flags: API_MIGRATION_FLAGS,
      mappings: Object.keys(ENDPOINT_MAPPING).length,
      v1Ready: Object.values(API_MIGRATION_FLAGS).filter(Boolean).length,
    };
  }

  /**
   * Enable/disable specific migration flags (for testing)
   */
  setFlag(flag: FeatureFlag, enabled: boolean) {
    (API_MIGRATION_FLAGS as any)[flag] = enabled;
  }
}

/**
 * Data transformation utilities for API migration
 */
export class DataMigrationAdapter {
  /**
   * Transform legacy source/file data to v1 format
   */
  static transformSourceData(legacyData: any): any {
    if (!legacyData) return legacyData;

    // Handle array of sources
    if (Array.isArray(legacyData)) {
      return legacyData.map(item => this.transformSingleSource(item));
    }

    // Handle single source
    return this.transformSingleSource(legacyData);
  }

  private static transformSingleSource(source: any): any {
    return {
      ...source,
      // Map legacy field names to v1
      source_type: source.file_type || source.source_type || 'file',
      original_name: source.filename || source.original_name,
      file_extension: source.ext || source.file_extension,
      // Ensure v1 required fields exist
      processing_status: source.processing_status || source.status || 'pending',
      created_at: source.created_at || new Date().toISOString(),
      updated_at: source.updated_at || source.created_at || new Date().toISOString(),
    };
  }

  /**
   * Transform v1 response data to legacy format (for backward compatibility)
   */
  static transformToLegacyFormat(v1Data: any, resourceType: 'source' | 'notebook' | 'chat' | 'report' | 'podcast'): any {
    if (!v1Data) return v1Data;

    switch (resourceType) {
      case 'source':
        return this.transformSourceToLegacy(v1Data);
      case 'notebook':
        return this.transformNotebookToLegacy(v1Data);
      default:
        return v1Data;
    }
  }

  private static transformSourceToLegacy(v1Data: any): any {
    if (Array.isArray(v1Data)) {
      return v1Data.map(item => ({
        ...item,
        filename: item.original_name || item.filename,
        ext: item.file_extension || item.ext,
        file_type: item.source_type || item.file_type,
        status: item.processing_status || item.status,
      }));
    }

    return {
      ...v1Data,
      filename: v1Data.original_name || v1Data.filename,
      ext: v1Data.file_extension || v1Data.ext,
      file_type: v1Data.source_type || v1Data.file_type,
      status: v1Data.processing_status || v1Data.status,
    };
  }

  private static transformNotebookToLegacy(v1Data: any): any {
    // Notebooks structure is mostly compatible, minimal transformation needed
    return v1Data;
  }
}

// Export singleton instance
export const apiMigration = ApiMigrationAdapter.getInstance();

// Export utilities for direct use
export const migrateEndpoint = (endpoint: string, notebookId?: string, resourceId?: string) => 
  apiMigration.getEndpoint(endpoint, notebookId, resourceId);

export const transformData = DataMigrationAdapter.transformSourceData;

export const getMigrationStatus = () => apiMigration.getMigrationStatus();