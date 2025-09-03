// ====== PODCAST FEATURE TYPES ======

export interface Podcast {
  id: string;
  job_id?: string;
  title: string;
  description?: string;
  audioUrl?: string;
  audio_file?: string;
  duration?: number;
  status: 'pending' | 'generating' | 'completed' | 'failed' | 'cancelled';
  progress?: string;
  topic?: string;
  expert_names?: {
    host?: string;
    expert1?: string;
    expert2?: string;
  };
  notebook_id?: string;
  source_file_ids?: string[];
  created_at: string;
  updated_at: string;
  user?: string;
  error_message?: string;
  conversation_text?: string;
  file_metadata?: any;
  audio_object_key?: string;
}

export interface PodcastState {
  podcasts: Podcast[];
  currentPodcast: Podcast | null;
  isLoading: boolean;
  error: string | null;
  lastFetched: number | null;
  searchTerm: string;
  sortOrder: 'recent' | 'oldest' | 'title';
  viewMode: 'grid' | 'list';
  filters: {
    status?: string;
    notebook_id?: string;
  };
}

export interface PodcastGenerationRequest {
  title: string;
  description?: string;
  topic?: string;
  expert_names?: {
    host?: string;
    expert1?: string;
    expert2?: string;
  };
  notebook_id?: string;
  source_file_ids?: string[];
  model?: string;
  temperature?: number;
  maxTokens?: number;
  systemPrompt?: string;
}

export interface PodcastGenerationResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface PodcastAudio {
  audioUrl: string;
  duration?: number;
  metadata?: any;
}

export interface PodcastFilters {
  status?: string;
  notebook_id?: string;
  date_range?: {
    start: string;
    end: string;
  };
  search?: string;
}

export interface PodcastStats {
  total: number;
  completed: number;
  failed: number;
  pending: number;
  generating: number;
  cancelled: number;
}

// ====== COMPONENT PROPS ======

export interface PodcastCardProps {
  podcast: Podcast;
  onSelect: (podcast: Podcast) => void;
  onDownload: (podcast: Podcast) => void;
  onDelete: (podcast: Podcast) => void;
  onPlay?: (podcast: Podcast) => void;
  onEdit?: (podcast: Podcast) => void;
  isSelected?: boolean;
}

export interface PodcastListProps {
  podcasts: Podcast[];
  isLoading: boolean;
  onSelectPodcast: (podcast: Podcast) => void;
  onDownloadPodcast: (podcast: Podcast) => void;
  onDeletePodcast: (podcast: Podcast) => void;
  onPlayPodcast?: (podcast: Podcast) => void;
  onEditPodcast?: (podcast: Podcast) => void;
  selectedPodcastId?: string;
  viewMode: 'grid' | 'list';
}

export interface PodcastDetailProps {
  podcast: Podcast;
  audio?: PodcastAudio;
  isLoading: boolean;
  onDownload: (podcast: Podcast) => void;
  onDelete: (podcast: Podcast) => void;
  onPlay?: (podcast: Podcast) => void;
  onEdit?: (podcast: Podcast) => void;
  onBack: () => void;
}

export interface PodcastFiltersProps {
  filters: PodcastFilters;
  onFiltersChange: (filters: PodcastFilters) => void;
  stats?: PodcastStats;
}

export interface PodcastGenerationFormProps {
  config: any;
  onConfigChange: (config: any) => void;
  onGenerate: () => void;
  onCancel: () => void;
  isLoading: boolean;
  selectedFiles?: any[];
  selectedSources?: any[];
  notebookId?: string;
}

export interface PodcastPlayerProps {
  podcast: Podcast;
  audioUrl?: string;
  onPlay?: () => void;
  onPause?: () => void;
  onSeek?: (time: number) => void;
  isPlaying?: boolean;
  currentTime?: number;
  duration?: number;
}
