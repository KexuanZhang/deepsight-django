/**
 * Global type definitions and utilities
 */

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: DeepPartial<T[P]>;
};

export type RequireAtLeastOne<T, Keys extends keyof T = keyof T> = Pick<T, Exclude<keyof T, Keys>> &
  {
    [K in Keys]-?: Required<Pick<T, K>> & Partial<Pick<T, Exclude<Keys, K>>>;
  }[Keys];

export type Prettify<T> = {
  [K in keyof T]: T[K];
} & {};

// Common API types
export type ID = string;
export type Timestamp = string;

// Status types
export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type SourceType = 'file' | 'url' | 'text';

// UI State types
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export type ViewMode = 'grid' | 'list' | 'card';

export type ThemeMode = 'light' | 'dark' | 'system';

// Error types
export interface AppError {
  message: string;
  code?: string;
  details?: Record<string, any>;
}

export interface ValidationError {
  field: string;
  message: string;
}

// Pagination types
export interface PaginationInfo {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

// Filter and search types
export interface SearchFilters {
  query?: string;
  dateRange?: {
    start?: string;
    end?: string;
  };
  tags?: string[];
  status?: ProcessingStatus[];
  sourceType?: SourceType[];
}

export type SortOrder = 'asc' | 'desc';
export type SortableField = 'name' | 'createdAt' | 'updatedAt' | 'status';

export interface SortConfig {
  field: SortableField;
  order: SortOrder;
}

// Component prop types
export interface BaseComponentProps {
  className?: string;
  'data-testid'?: string;
}

export interface BaseModalProps extends BaseComponentProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
}

export interface BaseButtonProps extends BaseComponentProps {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
}

// Form types
export interface FormField<T = any> {
  name: string;
  value: T;
  error?: string;
  touched: boolean;
  required?: boolean;
}

export interface FormState<T extends Record<string, any> = Record<string, any>> {
  values: T;
  errors: Partial<Record<keyof T, string>>;
  touched: Partial<Record<keyof T, boolean>>;
  isSubmitting: boolean;
  isValid: boolean;
}

// Event types
export type KeyboardEventHandler = (event: React.KeyboardEvent) => void;
export type MouseEventHandler = (event: React.MouseEvent) => void;
export type ChangeEventHandler<T = string> = (value: T) => void;
export type SubmitEventHandler<T = Record<string, any>> = (values: T) => void | Promise<void>;

// Feature flag types
export type FeatureFlag = 
  | 'modern_notebook_api'
  | 'enhanced_chat'
  | 'batch_operations'
  | 'advanced_search'
  | 'export_functionality';

// Navigation types
export interface BreadcrumbItem {
  label: string;
  href?: string;
  isActive?: boolean;
}

export interface NavigationItem {
  id: string;
  label: string;
  href: string;
  icon?: React.ComponentType<any>;
  badge?: string | number;
  children?: NavigationItem[];
}

// Toast/notification types
export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

// Media types
export interface FileMetadata {
  id?: string;
  name?: string;
  type?: string;
  size?: number;
  url?: string;
  createdAt?: string;
  updatedAt?: string;
  file_id?: string;
  original_filename?: string;
  file_extension?: string;
  file_size?: number;
  content_type?: string;
  upload_timestamp?: string;
  processing_type?: string;
  source_type?: string;
  source_url?: string;
  textContent?: string;
  knowledge_item_id?: string;
  upload_file_id?: string;
  parsing_status?: 'pending' | 'processing' | 'in_progress' | 'completed' | 'failed' | 'error' | 'cancelled' | 'unsupported' | 'uploading';
  processing_status?: string;
  format?: string;
  fileSize?: string;
  duration?: string;
  resolution?: string;
  language?: string;
  pageCount?: string;
  wordCount?: number;
  uploadedAt?: string;
  featuresAvailable?: string[];
  ext?: string;
  title?: string;
  content?: string;
  pdfUrl?: string;
  videoUrl?: string;
  audioUrl?: string;
  error?: string;
  extraction_type?: string;
  processing_method?: string;
  caption_generation_status?: 'pending' | 'in_progress' | 'completed' | 'failed';
  caption_generation_error?: string;
  caption_generation_completed_at?: string;
  images_requiring_captions?: number;
  image_count?: number;
  metadata?: any;
  [key: string]: any;
}

export interface UploadProgress {
  fileId: string;
  progress: number;
  status: 'uploading' | 'processing' | 'complete' | 'error';
  error?: string;
}

// Development types
export interface DevTools {
  enabled: boolean;
  version: string;
  environment: 'development' | 'staging' | 'production';
}

// React component types
export type PropsWithChildren<P = {}> = P & {
  children?: React.ReactNode;
};

export type ComponentWithChildren<P = {}> = React.FC<PropsWithChildren<P>>;

// Async operation types
export interface AsyncOperation<T = any> {
  data: T | null;
  loading: boolean;
  error: AppError | null;
  execute: (...args: any[]) => Promise<T>;
  reset: () => void;
}

// URL and routing types
export interface RouteParams {
  [key: string]: string | undefined;
}

export interface SearchParams {
  [key: string]: string | string[] | undefined;
}

// Configuration types
export interface AppConfig {
  apiBaseUrl: string;
  environment: 'development' | 'staging' | 'production';
  version: string;
  features: Record<FeatureFlag, boolean>;
  limits: {
    maxFileSize: number;
    maxFilesPerUpload: number;
    maxNotebooks: number;
  };
}