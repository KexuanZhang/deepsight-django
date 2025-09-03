// Core Notebook Types
export interface Notebook {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  user: string;
  file_count?: number;
  last_activity?: string;
  isPublic?: boolean;
  tags?: string[];
}

export interface CreateNotebookRequest {
  name: string;
  description: string;
}

export interface UpdateNotebookRequest {
  name?: string;
  description?: string;
}

// File Types
export interface File {
  id: string;
  name: string;
  size: number;
  type: string;
  uploaded_at: string;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  url?: string;
  thumbnail_url?: string;
  metadata?: Record<string, any>;
}

export interface FileUploadResponse {
  file: File;
  upload_url?: string;
}

// Chat Types
export interface NotebookChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  file_ids?: string[];
  metadata?: Record<string, any>;
}

export interface ChatRequest {
  file_ids: string[];
  question: string;
}

export interface ChatResponse {
  message: NotebookChatMessage;
  suggested_questions?: string[];
}

// Studio Types
export interface GenerationJob {
  id: string;
  type: 'report' | 'podcast';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  created_at: string;
  completed_at?: string;
  result_url?: string;
  error_message?: string;
  metadata?: Record<string, any>;
}

export interface GenerationRequest {
  type: 'report' | 'podcast';
  file_ids: string[];
  options?: Record<string, any>;
}

// API Response Types
export interface PaginatedResponse<T> {
  count: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  next: string | null;
  previous: string | null;
  stats?: {
    total_notebooks: number;
    active_notebooks: number;
    total_items_across_notebooks: number;
  };
  results: T[];
}

// State Types
export interface NotebookState {
  notebooks: Notebook[];
  currentNotebook: Notebook | null;
  isLoading: boolean;
  error: string | null;
  lastFetched: number | null;
  searchTerm: string;
  sortOrder: 'recent' | 'oldest' | 'name' | 'updated';
  viewMode: 'grid' | 'list';
}

export interface FileState {
  files: File[];
  selectedFiles: string[];
  uploadProgress: Record<string, number>;
  isLoading: boolean;
  error: string | null;
}

export interface ChatState {
  messages: NotebookChatMessage[];
  isLoading: boolean;
  error: string | null;
  suggestedQuestions: string[];
}

export interface StudioState {
  jobs: GenerationJob[];
  currentJob: GenerationJob | null;
  isLoading: boolean;
  error: string | null;
}

// Component Props Types
export interface NotebookCardProps {
  notebook: Notebook;
  onSelect: (notebook: Notebook) => void;
  onEdit: (notebook: Notebook) => void;
  onDelete: (notebookId: string) => void;
  isSelected?: boolean;
}

export interface CreateNotebookFormProps {
  onSubmit: (data: CreateNotebookRequest) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export interface FileUploadProps {
  notebookId: string;
  onUploadComplete: (file: File) => void;
  onUploadError: (error: string) => void;
  accept?: string;
  multiple?: boolean;
}

export interface ChatPanelProps {
  notebookId: string;
  messages: NotebookChatMessage[];
  onSendMessage: (message: string) => void;
  isLoading?: boolean;
  suggestedQuestions?: string[];
}

export interface StudioPanelProps {
  notebookId: string;
  selectedFiles: string[];
  onGenerate: (request: GenerationRequest) => void;
  jobs: GenerationJob[];
  isLoading?: boolean;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  timestamp: number;
}


// Filter and Sort Types
export interface NotebookFilters {
  searchTerm?: string;
  dateRange?: {
    start: string;
    end: string;
  };
  sortBy?: 'created_at' | 'updated_at' | 'name';
  sortOrder?: 'asc' | 'desc';
}

export interface FileFilters {
  type?: string;
  status?: File['status'];
  dateRange?: {
    start: string;
    end: string;
  };
}

// Utility Types
export type ViewMode = 'grid' | 'list';
export type SortOrder = 'recent' | 'oldest' | 'name' | 'updated';
export type FileStatus = 'uploading' | 'processing' | 'completed' | 'error';
export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type GenerationType = 'report' | 'podcast';

// Additional Notebook-specific types (moved from global types)
export interface FileUpload {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
}

// Source type for notebook feature
export interface Source {
  id: string | number;
  name?: string;
  type: 'file' | 'url' | 'text' | 'parsed' | 'uploading' | 'parsing';
  content?: string;
  url?: string;
  metadata?: any;
  createdAt?: string;
  file_id?: string;
  title?: string;
  selected?: boolean;
  file?: string | File;
  upload_file_id?: string;
  parsing_status?: 'pending' | 'processing' | 'in_progress' | 'completed' | 'failed' | 'error' | 'cancelled' | 'unsupported' | 'uploading';
  ext?: string;
  authors?: string;
  error_message?: string;
  textContent?: string;
  originalFile?: any;
}

// Component Props (moved from global types)
export interface SourcesListProps {
  notebookId: string;
  onSelectionChange?: () => void;
  onToggleCollapse?: () => void;
  isCollapsed?: boolean;
  onOpenModal?: (modalType: string, content?: React.ReactElement) => void;
  onCloseModal?: (modalType: string) => void;
  onSourcesRemoved?: () => void;
  sourcesRemovedTrigger?: number;
}

export interface SourceItemProps {
  source: Source;
  onToggle: (id: string) => void;
  onPreview: (source: Source) => void;
  getSourceTooltip: (source: Source) => string;
  getPrincipleFileIcon: (source: Source) => React.ComponentType<any>;
  renderFileStatus: (source: Source) => React.ReactNode;
}

// Re-export global types that are used in notebook feature
// export type { 
//   FileMetadata,
//   ChatMessage,
//   GenerationState,
//   FileData,
//   StatusProps,
//   GenerationConfig,
//   GalleryImage,
//   ExtractResult,
//   StatusUpdate,
//   FileIcons,
//   ProgressState,
//   KnowledgeBaseItem,
//   Suggestion
// } from '@/features/notebook/type';
