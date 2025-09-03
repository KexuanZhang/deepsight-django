// Main Components
export { default as DeepdivePage } from './pages/DeepdivePage';
export { default as NotebookListPage } from './pages/NotebookListPage';

// Layout Components
export { default as NotebookLayout } from './components/layout/NotebookLayout';
export { default as NotebookHeader } from './components/layout/NotebookHeader';
export { default as SidebarMenu } from './components/layout/SidebarMenu';

// Main Panels
export { default as SourcesPanel } from './components/panels/SourcesPanel';
export { default as ChatPanel } from './components/panels/ChatPanel';
export { default as StudioPanel } from './components/panels/StudioPanel';

// UI Components
export { default as CreateNotebookForm } from './components/CreateNotebookForm';
export { default as NotebookGrid } from './components/NotebookGrid';
export { default as NotebookList } from './components/NotebookList';
export { default as FilePreview } from './components/shared/FilePreview';

// Individual Panel Components (for direct access if needed)
export { default as SourcesList } from './components/sources/SourcesList';
export { default as Chat } from './components/panels/ChatPanel';
export { default as Studio } from './components/studio/StudioPanel';

// Hooks
export { useNotebookData } from './hooks/data/useNotebookData';
export { useFileUpload } from './hooks/file/useFileUpload';
export { useFileSelection } from './hooks/file/useFileSelection';
export { useChat } from './hooks/chat/useChat';

// Services
export { default as NotebookService } from './services/NotebookService';
export { default as SourceService } from './services/SourceService';
export { default as ChatService } from './services/ChatService';
export { default as StudioService } from './services/StudioService';

// Configuration
export * from './config/fileConfig';
export { 
  ANIMATIONS,
  COLORS,
  SPACING,
  TYPOGRAPHY,
  PANEL_HEADERS,
  RADIUS,
  SHADOWS,
  Z_INDEX,
  BREAKPOINTS,
  RESPONSIVE_PANELS,
  SIZES,
  GRID,
  TRANSITIONS,
  STATES,
  buildGridCols,
  buildSpacing
} from './config/uiConfig';

// Types
export * from './type';

// Redux
export { default as notebookSlice } from './notebookSlice';
export * from './notebookSlice';