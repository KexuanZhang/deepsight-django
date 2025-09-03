/**
 * Enhanced notebook operations hook with modern patterns
 */

import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { 
  useNotebook, 
  useUpdateNotebook, 
  useDeleteNotebook,
  useDuplicateNotebook,
  useNotebookStats,
  notebookQueries 
} from "@/shared/queries/notebooks";
import type { UpdateNotebookRequest } from "@/shared/api";
import { useErrorBoundary } from "@/shared/components/ui/ErrorBoundary";

interface UseNotebookOperationsOptions {
  onUpdate?: (notebook: any) => void;
  onDelete?: () => void;
  onDuplicate?: (notebook: any) => void;
  onError?: (error: Error) => void;
}

export const useNotebookOperations = (
  notebookId: string, 
  options: UseNotebookOperationsOptions = {}
) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { captureError } = useErrorBoundary();
  
  // Queries
  const {
    data: notebook,
    isLoading: isLoadingNotebook,
    error: notebookError,
    refetch: refetchNotebook,
  } = useNotebook(notebookId);

  const {
    data: stats,
    isLoading: isLoadingStats,
    error: statsError,
  } = useNotebookStats(notebookId);

  // Mutations
  const updateNotebook = useUpdateNotebook();
  const deleteNotebook = useDeleteNotebook();
  const duplicateNotebook = useDuplicateNotebook();

  // Prefetch related data
  const prefetchSources = useCallback(() => {
    queryClient.prefetchQuery({
      queryKey: ['notebooks', notebookId, 'sources'],
      queryFn: () => {
        // This will be implemented when we create the sources API
        return Promise.resolve([]);
      },
      staleTime: 2 * 60 * 1000,
    });
  }, [notebookId, queryClient]);

  const prefetchChat = useCallback(() => {
    queryClient.prefetchQuery({
      queryKey: ['notebooks', notebookId, 'chat', 'history'],
      queryFn: () => {
        // This will be implemented when we create the chat API
        return Promise.resolve([]);
      },
      staleTime: 30 * 1000,
    });
  }, [notebookId, queryClient]);

  // Operations
  const handleUpdate = useCallback(
    async (updates: UpdateNotebookRequest) => {
      try {
        const updatedNotebook = await updateNotebook.mutateAsync({
          id: notebookId,
          data: updates,
        });
        options.onUpdate?.(updatedNotebook);
        return updatedNotebook;
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Update failed');
        options.onError?.(err);
        captureError(err);
        throw err;
      }
    },
    [notebookId, updateNotebook, options, captureError]
  );

  const handleDelete = useCallback(
    async (redirectPath: string = '/notebooks') => {
      try {
        await deleteNotebook.mutateAsync(notebookId);
        options.onDelete?.();
        navigate(redirectPath);
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Delete failed');
        options.onError?.(err);
        captureError(err);
        throw err;
      }
    },
    [notebookId, deleteNotebook, navigate, options, captureError]
  );

  const handleDuplicate = useCallback(
    async (name?: string) => {
      try {
        const duplicatedNotebook = await duplicateNotebook.mutateAsync({
          id: notebookId,
          name,
        });
        options.onDuplicate?.(duplicatedNotebook);
        return duplicatedNotebook;
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Duplicate failed');
        options.onError?.(err);
        captureError(err);
        throw err;
      }
    },
    [notebookId, duplicateNotebook, options, captureError]
  );

  const handleRefresh = useCallback(() => {
    refetchNotebook();
    queryClient.invalidateQueries({
      queryKey: notebookQueries.detail(notebookId),
    });
  }, [refetchNotebook, queryClient, notebookId]);

  // Derived state
  const isLoading = isLoadingNotebook || isLoadingStats;
  const error = notebookError || statsError;
  const isUpdating = updateNotebook.isPending;
  const isDeleting = deleteNotebook.isPending;
  const isDuplicating = duplicateNotebook.isPending;
  const isBusy = isUpdating || isDeleting || isDuplicating;

  return {
    // Data
    notebook,
    stats,
    
    // State
    isLoading,
    error,
    isUpdating,
    isDeleting,
    isDuplicating,
    isBusy,
    
    // Operations
    operations: {
      update: handleUpdate,
      delete: handleDelete,
      duplicate: handleDuplicate,
      refresh: handleRefresh,
      prefetchSources,
      prefetchChat,
    },
    
    // Mutation objects (for more granular control)
    mutations: {
      update: updateNotebook,
      delete: deleteNotebook,
      duplicate: duplicateNotebook,
    },
  };
};

// Simplified hook for basic notebook data
export const useNotebookData = (notebookId: string) => {
  const { data, isLoading, error } = useNotebook(notebookId);
  
  return {
    notebook: data,
    isLoading,
    error,
  };
};

// Hook for notebook statistics
export const useNotebookStatsData = (notebookId: string) => {
  const { data, isLoading, error } = useNotebookStats(notebookId);
  
  return {
    stats: data,
    isLoading,
    error,
  };
};