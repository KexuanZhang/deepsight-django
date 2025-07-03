// Main Components
export { default as DeepdivePage } from './DeepdivePage';
export { default as NotebookListPage } from './NotebookListPage';

// Layout Components
export { default as NotebookLayout } from './components/layout/NotebookLayout';
export { default as NotebookHeader } from './components/layout/NotebookHeader';
export { default as SidebarMenu } from './components/layout/SidebarMenu';

// UI Components
export { default as CreateNotebookForm } from './components/CreateNotebookForm';
export { default as NotebookGrid } from './components/NotebookGrid';
export { default as NotebookList } from './components/NotebookList';
export { default as SourcesList } from './components/SourcesList';
export { default as ChatPanel } from './components/ChatPanel';
export { default as FilePreview } from './components/FilePreview';

// Hooks
export { useNotebookData } from './hooks/useNotebookData';
export { useFileUpload } from './hooks/useFileUpload';
export { useChat } from './hooks/useChat';

// Services
export { default as NotebookService } from './services/NotebookService';
export { default as FileService } from './services/FileService';

// Configuration
export * from './config/fileConfig';
export * from './config/uiConfig';

// Redux
export { default as notebookSlice } from './notebookSlice';
export * from './notebookSlice';