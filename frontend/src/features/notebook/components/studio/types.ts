// ====== STUDIO PANEL TYPE DEFINITIONS ======
// This file contains all type definitions for the Studio Panel functionality

import React from 'react';

// ====== CORE TYPES ======

export enum GenerationState {
  IDLE = 'idle',
  GENERATING = 'generating', 
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

// ====== MODEL AND CONFIGURATION TYPES ======

export interface AvailableModels {
  model_providers?: string[];
  [key: string]: any;
}

export interface GenerationConfig {
  model: string;
  temperature?: number;
  maxTokens?: number;
  systemPrompt?: string;
  [key: string]: any;
}

export interface ReportConfig extends GenerationConfig {
  topic?: string;
  article_title?: string;
  model_provider?: string;
  retriever?: string;
  prompt_type?: string;
  include_image?: boolean;
  include_domains?: boolean;
  time_range?: string;
  notebook_id?: string;
  selected_files_paths?: string[];
}

export interface PodcastConfig extends GenerationConfig {
  title?: string;
  description?: string;
  topic?: string;
  expert_names?: {
    host?: string;
    expert1?: string;
    expert2?: string;
  };
  notebook_id?: string;
  source_file_ids?: string[];
}

// ====== GENERATION STATE TYPES ======

export interface GenerationStateHook {
  state: GenerationState;
  progress: string;
  error: string | null;
  config: any;
  currentJobId: string | null;
  isGenerating: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  isCancelled: boolean;
  isIdle: boolean;
  startGeneration: (jobId: string) => void;
  updateProgress: (progress: string) => void;
  completeGeneration: () => void;
  failGeneration: (error: string) => void;
  cancelGeneration: () => void;
  resetState: () => void;
  updateConfig: (updates: any) => void;
}

// ====== FILE AND CONTENT TYPES ======

export interface FileItem {
  id: string;
  name: string;
  type: string;
  size?: number;
  url?: string;
  createdAt?: string;
  title?: string;
  content?: string;
  job_id?: string;
  status?: string;
  progress?: string;
  audio_file?: string;
  created_at?: string;
  article_title?: string;
  markdown_content?: string;
  [key: string]: any;
}

export interface ReportItem extends FileItem {
  article_title?: string;
  markdown_content?: string;
  job_id?: string;
}

export interface PodcastItem extends FileItem {
  audio_file?: string;
  job_id?: string;
}

export interface SourceItem {
  id: string;
  name: string;
  type: 'file' | 'url' | 'text';
  content?: string;
  url?: string;
  selected?: boolean;
  [key: string]: any;
}

// ====== COMPONENT PROP TYPES ======

export interface StudioPanelProps {
  notebookId: string;
  sourcesListRef: React.RefObject<{
    getSelectedFiles?: () => FileItem[];
    getSelectedSources?: () => SourceItem[];
  }> | null;
  onSelectionChange: (callback: () => void) => void;
  onOpenModal: (id: string, content: React.ReactNode) => void;
  onCloseModal: (id: string) => void;
  onToggleExpand?: () => void;
  isStudioExpanded?: boolean;
}

export interface StatusDisplayProps {
  state: GenerationState;
  progress?: string;
  error?: string;
  isGenerating: boolean;
}

export interface PodcastStatusProps {
  state: GenerationState;
  progress?: string;
  error?: string;
}

// ====== SERVICE TYPES ======

export interface StudioDataHook {
  reports: ReportItem[];
  podcasts: PodcastItem[];
  availableModels: AvailableModels;
  loading: {
    reports: boolean;
    podcasts: boolean;
    models: boolean;
  };
  error: {
    reports: string | null;
    podcasts: string | null;
    models: string | null;
  };
  loadReports: () => Promise<void>;
  loadPodcasts: () => Promise<void>;
  loadModels: () => Promise<void>;
  addReport: (report: ReportItem) => void;
  addPodcast: (podcast: PodcastItem) => void;
  removeReport: (reportId: string) => void;
  removePodcast: (podcastId: string) => void;
}

export interface JobStatusResult {
  progress?: string;
}

// ====== UTILITY FUNCTIONS ======

export const createStatusProps = (
  state: GenerationState,
  progress?: string,
  error?: string
): StatusDisplayProps => ({
  state,
  progress,
  error,
  isGenerating: state === GenerationState.GENERATING
});

export const createFileOperationProps = (
  file: FileItem,
  onSelect: (file: FileItem) => void,
  onDownload: (file: FileItem) => void,
  onDelete: (file: FileItem) => void
) => ({
  file,
  onSelect,
  onDownload,
  onDelete
});

// ====== COLLAPSED SECTIONS STATE ======

export interface CollapsedSections {
  report: boolean;
  podcast: boolean;
  reports: boolean;
  podcasts: boolean;
}