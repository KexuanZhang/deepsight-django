// Global type declarations for the frontend application

// Extend Window interface for any global properties
declare global {
  interface Window {
    // Add any global window properties here
    __REDUX_DEVTOOLS_EXTENSION__?: any;
  }
}

// Common utility types
export type Nullable<T> = T | null;
export type Optional<T> = T | undefined;

// Common event types
export type InputChangeEvent = React.ChangeEvent<HTMLInputElement>;
export type FormSubmitEvent = React.FormEvent<HTMLFormElement>;
export type ButtonClickEvent = React.MouseEvent<HTMLButtonElement>;

// File type enumeration
export type FileType = 'pdf' | 'txt' | 'md' | 'ppt' | 'pptx' | 'mp3' | 'mp4' | 'avi' | 'mov' | 'wmv' | 'flv' | 'webm' | 'doc' | 'docx' | 'xls' | 'xlsx' | 'csv' | 'json' | 'xml' | 'html' | 'css' | 'js' | 'py' | 'java' | 'cpp' | 'c' | 'h' | 'hpp' | 'cs' | 'php' | 'rb' | 'go' | 'rs' | 'swift' | 'kt' | 'scala' | 'r' | 'matlab' | 'sql' | 'sh' | 'bat' | 'ps1' | 'yaml' | 'yml' | 'toml' | 'ini' | 'cfg' | 'conf' | 'log' | 'zip' | 'rar' | '7z' | 'tar' | 'gz' | 'bz2' | 'xz' | 'media';

// API response types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// Enhanced File and media types (merged from notebook types)
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
  parsing_status?: 'pending' | 'processing' | 'in_progress' | 'completed' | 'failed';
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
  // Caption generation fields
  caption_generation_status?: 'pending' | 'in_progress' | 'completed' | 'failed';
  caption_generation_error?: string;
  caption_generation_completed_at?: string;
  images_requiring_captions?: number;
  image_count?: number;
  [key: string]: any;
}

export interface FileSource {
  id?: string;
  name?: string;
  type?: 'file' | 'url' | 'text';
  content?: string;
  url?: string;
  file_id: string;
  metadata: FileMetadata;
  textContent?: string;
  createdAt?: string;
  selected?: boolean;
  file?: string;
  upload_file_id?: string;
  parsing_status?: 'pending' | 'processing' | 'in_progress' | 'completed' | 'failed';
  title?: string;
  ext?: string;
  [key: string]: any;
}

export interface Source {
  id: string;
  name: string;
  type: 'file' | 'url' | 'text';
  content?: string;
  url?: string;
  metadata?: FileMetadata;
  createdAt: string;
  selected?: boolean;
  file_id?: string;
  file?: string;
  upload_file_id?: string;
  parsing_status?: 'pending' | 'processing' | 'in_progress' | 'completed' | 'failed';
  title?: string;
  ext?: string;
}

export interface KnowledgeBaseItem {
  id: string;
  title?: string;
  filename?: string;
  original_filename?: string;
  linked_to_notebook: boolean;
  metadata?: Record<string, any>;
  processing_status?: string;
}

// Chat and messaging types (enhanced)
export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  [key: string]: any;
}

// Chat suggestion types
export interface Suggestion {
  text: string;
  icon: React.ComponentType<any>;
}

// Preview state types
export interface PreviewState {
  type: 'video' | 'audio' | 'pdf' | 'image' | 'text' | 'markdown' | 'unknown';
  format: string;
  fileSize: string;
  duration: string;
  resolution: string;
  language: string;
  pageCount: string;
  wordCount: number;
  uploadedAt: string;
  featuresAvailable: string[];
  content: string;
  pdfUrl: string;
  videoUrl: string;
  audioUrl: string;
  title: string;
  error?: string;
  hasTranscript?: boolean;
  isPdfPreview?: boolean;
  lines?: number;
  processingType?: string;
  contentLength?: number;
  extractedAt?: string;
  domain?: string;
  url?: string;
  sampleRate?: string;
  processingStatus?: string;
}

// Studio generation types
export enum GenerationState {
  IDLE = 'idle',
  GENERATING = 'generating', 
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface FileData {
  id: string;
  name: string;
  type: string;
  size: number;
  url: string;
  createdAt: string;
  updatedAt: string;
}

export interface StatusProps {
  state: GenerationState;
  title: string;
  progress?: number;
  error?: string;
  onCancel?: () => void;
  showCancel: boolean;
}

export interface GenerationConfig {
  model: string;
  temperature?: number;
  maxTokens?: number;
  systemPrompt?: string;
  [key: string]: any;
}

// Gallery types
export interface GalleryImage {
  name: string;
  imageUrl?: string;
  blobUrl?: string;
  loading: boolean;
}

export interface ExtractResult {
  success: boolean;
  result?: {
    statistics?: {
      final_frames?: number;
    };
  };
}

// Event types
export interface VideoErrorEvent {
  target?: {
    error?: any;
    networkState?: number;
    readyState?: number;
    src?: string;
  };
}

export interface StatusUpdate {
  status: string;
  progress?: number;
  error?: string;
  result?: any;
}

// Utility interfaces
export interface FileIcons {
  [key: string]: React.ComponentType<any>;
}

export interface ProgressState {
  [key: string]: {
    status: string;
    progress?: number;
    error?: string;
  };
}

// Export empty object to make this a module
export {};