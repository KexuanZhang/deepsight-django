// ====== GLOBAL APPLICATION TYPES ======
// These types are used across multiple features and should remain centralized

// User and Authentication
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

// Global API Response types
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  success: boolean;
}

export interface ApiError {
  message: string;
  code?: number;
  details?: Record<string, any>;
}

// Global UI and Component Props
export interface LoadingState {
  isLoading: boolean;
  error: string | null;
  progress?: number;
}

export interface PaginationState {
  page: number;
  limit: number;
  total: number;
  hasMore: boolean;
}

export interface FilterState {
  search: string;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  filters: Record<string, any>;
}

// Global Event handlers and callbacks
export type EventHandler<T = any> = (data: T) => void;
export type AsyncEventHandler<T = any> = (data: T) => Promise<void>;

// Global Utility types
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredField<T, K extends keyof T> = T & Required<Pick<T, K>>;

// Re-export types from global.d.ts
export type { 
  PreviewState, 
  VideoErrorEvent,
  FileMetadata,
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
} from './global';