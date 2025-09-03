// ====== REPORT FEATURE TYPES ======

export interface Report {
  id: string;
  job_id?: string;
  title: string;
  article_title?: string;
  description?: string;
  content?: string;
  markdown_content?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress?: string;
  topic?: string;
  model_provider?: string;
  retriever?: string;
  prompt_type?: string;
  include_image?: boolean;
  include_domains?: boolean;
  time_range?: string;
  notebook_id?: string;
  selected_files_paths?: string[];
  created_at: string;
  updated_at: string;
  user?: string;
  error_message?: string;
  result_metadata?: any;
  file_metadata?: any;
  generated_files?: string[];
  processing_logs?: string[];
  main_report_object_key?: string;
  figure_data_object_key?: string;
}

export interface ReportState {
  reports: Report[];
  currentReport: Report | null;
  isLoading: boolean;
  error: string | null;
  lastFetched: number | null;
  searchTerm: string;
  sortOrder: 'recent' | 'oldest' | 'title';
  viewMode: 'grid' | 'list';
  filters: {
    status?: string;
    model_provider?: string;
    notebook_id?: string;
  };
}

export interface ReportGenerationRequest {
  topic: string;
  article_title?: string;
  model_provider?: string;
  retriever?: string;
  prompt_type?: string;
  include_image?: boolean;
  include_domains?: boolean;
  time_range?: string;
  notebook_id?: string;
  selected_files_paths?: string[];
  model?: string;
  temperature?: number;
  maxTokens?: number;
  systemPrompt?: string;
}

export interface ReportGenerationResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface ReportContent {
  content: string;
  markdown_content?: string;
  title?: string;
  metadata?: any;
}

export interface ReportFilters {
  status?: string;
  model_provider?: string;
  notebook_id?: string;
  date_range?: {
    start: string;
    end: string;
  };
  search?: string;
}

export interface ReportStats {
  total: number;
  completed: number;
  failed: number;
  pending: number;
  running: number;
  cancelled: number;
}

// ====== COMPONENT PROPS ======

export interface ReportCardProps {
  report: Report;
  onSelect: (report: Report) => void;
  onDownload: (report: Report) => void;
  onDelete: (report: Report) => void;
  onEdit?: (report: Report) => void;
  isSelected?: boolean;
}

export interface ReportListProps {
  reports: Report[];
  isLoading: boolean;
  onSelectReport: (report: Report) => void;
  onDownloadReport: (report: Report) => void;
  onDeleteReport: (report: Report) => void;
  onEditReport?: (report: Report) => void;
  selectedReportId?: string;
  viewMode: 'grid' | 'list';
}

export interface ReportDetailProps {
  report: Report;
  content?: ReportContent;
  isLoading: boolean;
  onDownload: (report: Report) => void;
  onDelete: (report: Report) => void;
  onEdit?: (report: Report) => void;
  onBack: () => void;
}

export interface ReportFiltersProps {
  filters: ReportFilters;
  onFiltersChange: (filters: ReportFilters) => void;
  stats?: ReportStats;
}

export interface ReportGenerationFormProps {
  config: any;
  onConfigChange: (config: any) => void;
  onGenerate: () => void;
  onCancel: () => void;
  isLoading: boolean;
  availableModels?: any;
  selectedFiles?: any[];
  notebookId?: string;
}
