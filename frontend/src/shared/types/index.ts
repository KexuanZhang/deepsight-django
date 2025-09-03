/**
 * Global application types and re-exports
 * 
 * This file provides backward compatibility while transitioning to the new type structure.
 * New code should import from "@/shared/types/global").
 */

// Modern global types
export * from './global';

// API types (for backward compatibility - prefer importing from "@/shared/api)
export type {
  ApiResponse,
  PaginatedResponse,
  PaginationParams,
  ApiError,
} from "@/shared/api";

// Notebook types (for backward compatibility - prefer importing from "@/shared/api)
export type {
  Notebook,
  CreateNotebookRequest,
  UpdateNotebookRequest,
  Source as NotebookSource,
  ChatMessage as NotebookChatMessage,
  KnowledgeBaseItem as NotebookKnowledgeBaseItem,
} from "@/shared/api";

// Legacy types - maintained for compatibility during migration
export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  role: string;
  createdAt: string;
  updatedAt: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  isLoading: boolean;
  error: string | null;
}

// Legacy UI types - use global types instead
/**
 * @deprecated Use LoadingState from "@/shared/types/global"
 */
export interface LegacyLoadingState {
  isLoading: boolean;
  error: string | null;
  progress?: number;
}

/**
 * @deprecated Use PaginationInfo from "@/shared/types/global"
 */
export interface LegacyPaginationState {
  page: number;
  limit: number;
  total: number;
  hasMore: boolean;
}

/**
 * @deprecated Use SearchFilters from "@/shared/types/global"
 */
export interface FilterState {
  search: string;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  filters: Record<string, any>;
}

// Event handlers (keep for backward compatibility)
export type EventHandler<T = any> = (data: T) => void;
export type AsyncEventHandler<T = any> = (data: T) => Promise<void>;

// Utility types (keep for backward compatibility)
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredField<T, K extends keyof T> = T & Required<Pick<T, K>>;

// Legacy re-exports from global.d.ts (for backward compatibility)
// These will be removed once components are migrated
export type { 
  PreviewState, 
  VideoErrorEvent,
  FileMetadata as LegacyFileMetadata,
  FileSource,
  Source,
  ChatMessage,
  GenerationState,
  FileData,
  StatusProps,
  GenerationConfig,
  GalleryImage,
  ExtractResult,
  StatusUpdate,
  FileIcons,
  ProgressState,
  KnowledgeBaseItem,
  Suggestion
} from './global.d';