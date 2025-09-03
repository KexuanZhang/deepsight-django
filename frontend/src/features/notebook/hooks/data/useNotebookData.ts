import { useCallback } from 'react';
import { useApiUtils } from "@/features/notebook/hooks/shared/useApiUtils";
import { useAsyncState } from "@/features/notebook/hooks/shared/useAsyncState";
import type { Notebook, CreateNotebookRequest, UpdateNotebookRequest, PaginatedResponse } from "@/features/notebook/type";

/**
 * Optimized notebook data management hook
 * 
 * This hook provides notebook CRUD operations with improved performance,
 * type safety, and maintainability using shared utilities.
 * 
 * Features:
 * - Notebook CRUD operations (Create, Read, Update, Delete)
 * - Sorting and filtering capabilities
 * - Current notebook selection and management
 * - Error handling and loading states
 * - Data freshness tracking
 * - Optimistic updates for better UX
 * 
 * Dependencies:
 * - useApiUtils: For authenticated API calls and CSRF token management
 * - useAsyncState: For state management and async operation handling
 * 
 * @returns Object containing notebook data and operations
 */
export const useNotebookData = () => {
  const { get, post, patch, del, primeCsrfToken } = useApiUtils();
  const { 
    data: notebooks, 
    loading, 
    error, 
    execute,
    setData: setNotebooks,
    clearError,
    isStale
  } = useAsyncState<Notebook[]>();

  const { 
    data: currentNotebook,
    setData: setCurrentNotebook,
    clear: clearCurrentNotebook
  } = useAsyncState<Notebook | null>();

  /**
   * Fetch all notebooks with optional sorting
   * @param sortOrder - Sort order ('recent', 'oldest', 'name', 'updated')
   * @returns Promise with fetch result
   */
  const fetchNotebooks = useCallback(async (sortOrder: 'recent' | 'oldest' | 'name' | 'updated' = 'recent') => {
    return execute(async () => {
      try {
        const response = await get<PaginatedResponse<Notebook>>('/notebooks/');
        
        console.log('API Response:', response);
        
        // Handle paginated response - extract results array
        const notebooks = response.results || response;
        
        console.log('Extracted notebooks:', notebooks);
        
        
        // Ensure notebooks is an array
        if (!Array.isArray(notebooks)) {
          console.error('Expected notebooks array, got:', typeof notebooks, notebooks);
          return [];
        }
        
        // Sort notebooks based on sort order
        const sortedData = [...notebooks].sort((a, b) => {
          switch (sortOrder) {
            case 'recent':
              return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
            case 'oldest':
              return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
            case 'name':
              return a.name.localeCompare(b.name);
            case 'updated':
              return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
            default:
              return 0;
          }
        });
        
        return sortedData;
      } catch (error) {
        console.error('Error fetching notebooks:', error);
        throw error;
      }
    });
  }, [execute, get]);

  /**
   * Fetch a single notebook by ID
   * @param notebookId - Notebook ID to fetch
   * @returns Promise with fetch result
   */
  const fetchNotebook = useCallback(async (notebookId: string) => {
    return execute(async () => {
      const data = await get<Notebook>(`/notebooks/${notebookId}/`);
      setCurrentNotebook(data);
      return data;
    }, { updateData: false }); // Don't update notebooks array, just current notebook
  }, [execute, get, setCurrentNotebook]);

  /**
   * Create a new notebook
   * @param request - Notebook creation data
   * @returns Promise with created notebook
   */
  const createNotebook = useCallback(async (request: CreateNotebookRequest) => {
    if (!request.name.trim()) {
      throw new Error('Name is required');
    }

    return execute(async () => {
      const newNotebook = await post<Notebook>('/notebooks/', request);
      
      // Optimistically update notebooks list
      if (notebooks) {
        setNotebooks([newNotebook, ...notebooks]);
      } else {
        setNotebooks([newNotebook]);
      }
      
      return newNotebook;
    }, { updateData: false }); // We manually update the notebooks list
  }, [execute, post, setNotebooks, notebooks]);

  /**
   * Update an existing notebook
   * @param notebookId - Notebook ID to update
   * @param updates - Update data
   * @returns Promise with updated notebook
   */
  const updateNotebook = useCallback(async (notebookId: string, updates: UpdateNotebookRequest) => {
    return execute(async () => {
      const updatedNotebook = await patch<Notebook>(`/notebooks/${notebookId}/`, updates);
      
      // Update notebooks list
      if (notebooks) {
        setNotebooks(notebooks.map(nb => nb.id === notebookId ? updatedNotebook : nb));
      }
      
      // Update current notebook if it's the one being updated
      if (currentNotebook?.id === notebookId) {
        setCurrentNotebook(updatedNotebook);
      }
      
      return updatedNotebook;
    }, { updateData: false });
  }, [execute, patch, setNotebooks, setCurrentNotebook, notebooks, currentNotebook]);

  /**
   * Delete a notebook
   * @param notebookId - Notebook ID to delete
   * @returns Promise with deletion result
   */
  const deleteNotebook = useCallback(async (notebookId: string) => {
    return execute(async () => {
      await del(`/notebooks/${notebookId}/`);
      
      // Remove from notebooks list
      if (notebooks) {
        setNotebooks(notebooks.filter(nb => nb.id !== notebookId));
      }
      
      // Clear current notebook if it was deleted
      if (currentNotebook?.id === notebookId) {
        setCurrentNotebook(null);
      }
      
      return { success: true };
    }, { updateData: false });
  }, [execute, del, setNotebooks, setCurrentNotebook, notebooks, currentNotebook]);

  /**
   * Search notebooks by name or description
   * @param searchTerm - Search term
   * @returns Filtered notebooks
   */
  const searchNotebooks = useCallback((searchTerm: string) => {
    if (!notebooks || !searchTerm.trim()) return notebooks;
    
    const term = searchTerm.toLowerCase();
    return notebooks.filter(notebook => 
      notebook.name.toLowerCase().includes(term) ||
      notebook.description.toLowerCase().includes(term)
    );
  }, [notebooks]);

  /**
   * Get notebook by ID from current list
   * @param notebookId - Notebook ID
   * @returns Notebook or undefined
   */
  const getNotebookById = useCallback((notebookId: string) => {
    return notebooks?.find(nb => nb.id === notebookId);
  }, [notebooks]);

  /**
   * Check if data needs refresh (stale data)
   * @param maxAge - Maximum age in milliseconds (default: 5 minutes)
   * @returns True if data is stale
   */
  const needsRefresh = useCallback((maxAge: number = 5 * 60 * 1000) => {
    return isStale(maxAge);
  }, [isStale]);

  return {
    // State
    notebooks,
    currentNotebook,
    loading,
    error,
    
    // Actions
    fetchNotebooks,
    fetchNotebook,
    createNotebook,
    updateNotebook,
    deleteNotebook,
    clearCurrentNotebook,
    clearError,
    
    // Utilities
    searchNotebooks,
    getNotebookById,
    needsRefresh,
    
    // API Utils
    primeCsrfToken,
    
    // Computed
    hasNotebooks: notebooks !== null && notebooks.length > 0,
    hasCurrentNotebook: currentNotebook !== null,
  };
};