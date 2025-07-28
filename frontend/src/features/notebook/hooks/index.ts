// ============================================================================
// SHARED HOOKS - Common utilities and patterns
// ============================================================================

/**
 * Shared API utilities for authentication, CSRF tokens, and HTTP requests
 * Use this hook in any component that needs to make authenticated API calls
 */
export { useApiUtils } from './shared/useApiUtils';

/**
 * Generic async state management for loading, error, and data states
 * Use this hook as a base for any async operation
 */
export { useAsyncState } from './shared/useAsyncState';

// ============================================================================
// DOMAIN-SPECIFIC HOOKS
// ============================================================================

// Chat functionality
export { useChat } from './chat/useChat';

// Data management
export { useNotebookData } from './data/useNotebookData';

// File handling
export { useFileUpload } from './file/useFileUpload';
export { useFileSelection } from './file/useFileSelection';

// Generation and job management
export { useJobStatus } from './generation/useJobStatus';
export { useGenerationState } from './generation/useGenerationState';

// Studio functionality
export { useStudioData } from './studio/useStudioData';