// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Breaking down monolithic interfaces into focused, single-purpose contracts

// Generation state interface
export const GenerationState = {
  IDLE: 'idle',
  GENERATING: 'generating', 
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
};

// Status display props - focused interface for status components
export const createStatusProps = (state, title, progress, error, onCancel) => ({
  state,
  title,
  progress,
  error,
  onCancel,
  showCancel: state === GenerationState.GENERATING
});

// File operation props - segregated interface for file actions  
export const createFileOperationProps = (file, operations) => ({
  file,
  onDownload: operations.download,
  onEdit: operations.edit,  
  onDelete: operations.delete,
  onSelect: operations.select
});

// Generation config props - focused on configuration concerns
export const createGenerationConfigProps = (config, onConfigChange, models) => ({
  config,
  onConfigChange,
  availableModels: models,
  onGenerate: null // To be injected
});

// Audio management props - single responsibility for audio features
export const createAudioProps = (audioState, operations) => ({
  isLoading: audioState.loading,
  audioUrl: audioState.url,
  onPlay: operations.play,
  onPause: operations.pause,
  onDownload: operations.download
});

// UI state props - presentation concerns only
export const createUIStateProps = (uiState, handlers) => ({
  isExpanded: uiState.expanded,
  viewMode: uiState.viewMode,
  collapsedSections: uiState.collapsedSections,
  onToggleExpand: handlers.toggleExpand,
  onToggleViewMode: handlers.toggleViewMode,
  onToggleSection: handlers.toggleSection
});