/**
 * TanStack Query hooks for notebook operations
 */

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { notebookService } from "@/shared/services/NotebookService";
import { notebooksApi } from '../api/resources/notebooks';
import type {
  Notebook,
  CreateNotebookRequest,
  UpdateNotebookRequest,
  GetNotebooksParams,
  CreateSourceRequest,
  ProcessUrlRequest,
  AddTextRequest,
} from '../api/resources/notebooks';

// Query Keys Factory
export const notebookQueries = {
  all: ['notebooks'] as const,
  lists: () => [...notebookQueries.all, 'list'] as const,
  list: (params?: GetNotebooksParams) => [...notebookQueries.lists(), params] as const,
  details: () => [...notebookQueries.all, 'detail'] as const,
  detail: (id: string) => [...notebookQueries.details(), id] as const,
  stats: (id: string) => [...notebookQueries.detail(id), 'stats'] as const,
  
  // Nested resources
  sources: (notebookId: string) => [...notebookQueries.detail(notebookId), 'sources'] as const,
  sourcesList: (notebookId: string, params?: any) => 
    [...notebookQueries.sources(notebookId), 'list', params] as const,
  
  chat: (notebookId: string) => [...notebookQueries.detail(notebookId), 'chat'] as const,
  chatHistory: (notebookId: string) => [...notebookQueries.chat(notebookId), 'history'] as const,
  
  knowledgeBase: (notebookId: string) => 
    [...notebookQueries.detail(notebookId), 'knowledge-base'] as const,
};

// Notebook Queries
export const useNotebooks = (params?: GetNotebooksParams) => {
  return useQuery({
    queryKey: notebookQueries.list(params),
    queryFn: () => notebookService.getAll(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
  });
};

export const useNotebook = (id: string) => {
  return useQuery({
    queryKey: notebookQueries.detail(id),
    queryFn: () => notebookService.getById(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

export const useNotebookStats = (id: string) => {
  return useQuery({
    queryKey: notebookQueries.stats(id),
    queryFn: () => notebooksApi.getStats(id),
    enabled: !!id,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
};

// Infinite query for large notebook lists
export const useInfiniteNotebooks = (params?: Omit<GetNotebooksParams, 'page'>) => {
  return useInfiniteQuery({
    queryKey: [...notebookQueries.lists(), 'infinite', params],
    queryFn: ({ pageParam = 1 }) =>
      notebooksApi.getAll({ ...params, page: pageParam }),
    getNextPageParam: (lastPage) =>
      lastPage.meta.pagination.hasNext 
        ? lastPage.meta.pagination.page + 1 
        : undefined,
    initialPageParam: 1,
    staleTime: 5 * 60 * 1000,
  });
};

// Notebook Mutations
export const useCreateNotebook = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: CreateNotebookRequest) => notebooksApi.create(data),
    onSuccess: (newNotebook) => {
      // Invalidate and refetch notebooks list
      queryClient.invalidateQueries({ queryKey: notebookQueries.lists() });
      
      // Add the new notebook to the cache
      queryClient.setQueryData(
        notebookQueries.detail(newNotebook.id),
        newNotebook
      );
    },
  });
};

export const useUpdateNotebook = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateNotebookRequest }) =>
      notebooksApi.update(id, data),
    onSuccess: (updatedNotebook) => {
      // Update the specific notebook in cache
      queryClient.setQueryData(
        notebookQueries.detail(updatedNotebook.id),
        updatedNotebook
      );
      
      // Update in lists cache
      queryClient.setQueriesData(
        { queryKey: notebookQueries.lists() },
        (oldData: any) => {
          if (!oldData?.data) return oldData;
          
          return {
            ...oldData,
            data: oldData.data.map((notebook: Notebook) =>
              notebook.id === updatedNotebook.id ? updatedNotebook : notebook
            ),
          };
        }
      );
    },
  });
};

export const useDeleteNotebook = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: string) => notebooksApi.delete(id),
    onSuccess: (_, deletedId) => {
      // Remove from lists cache
      queryClient.setQueriesData(
        { queryKey: notebookQueries.lists() },
        (oldData: any) => {
          if (!oldData?.data) return oldData;
          
          return {
            ...oldData,
            data: oldData.data.filter((notebook: Notebook) => notebook.id !== deletedId),
            meta: {
              ...oldData.meta,
              pagination: {
                ...oldData.meta.pagination,
                count: oldData.meta.pagination.count - 1,
              },
            },
          };
        }
      );
      
      // Remove specific notebook cache
      queryClient.removeQueries({ queryKey: notebookQueries.detail(deletedId) });
    },
  });
};

export const useDuplicateNotebook = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name?: string }) =>
      notebooksApi.duplicate(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notebookQueries.lists() });
    },
  });
};

// Source Queries
export const useNotebookSources = (notebookId: string, params?: any) => {
  return useQuery({
    queryKey: notebookQueries.sourcesList(notebookId, params),
    queryFn: () => notebooksApi.sources.getAll(notebookId, params),
    enabled: !!notebookId,
    staleTime: 2 * 60 * 1000,
  });
};

// Source Mutations
export const useCreateSource = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: CreateSourceRequest) =>
      notebooksApi.sources.create(notebookId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: notebookQueries.sources(notebookId),
      });
      queryClient.invalidateQueries({
        queryKey: notebookQueries.stats(notebookId),
      });
    },
  });
};

export const useUploadFile = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (file: File) => notebooksApi.sources.uploadFile(notebookId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: notebookQueries.sources(notebookId),
      });
      queryClient.invalidateQueries({
        queryKey: notebookQueries.stats(notebookId),
      });
    },
  });
};

export const useProcessUrl = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: ProcessUrlRequest) =>
      notebooksApi.sources.processUrl(notebookId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: notebookQueries.sources(notebookId),
      });
      queryClient.invalidateQueries({
        queryKey: notebookQueries.stats(notebookId),
      });
    },
  });
};

export const useAddText = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: AddTextRequest) =>
      notebooksApi.sources.addText(notebookId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: notebookQueries.sources(notebookId),
      });
      queryClient.invalidateQueries({
        queryKey: notebookQueries.stats(notebookId),
      });
    },
  });
};

// Chat Queries
export const useChatHistory = (notebookId: string) => {
  return useQuery({
    queryKey: notebookQueries.chatHistory(notebookId),
    queryFn: () => notebooksApi.chat.getHistory(notebookId),
    enabled: !!notebookId,
    staleTime: 30 * 1000, // 30 seconds
  });
};

export const useSendChatMessage = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (message: string) =>
      notebooksApi.chat.sendMessage(notebookId, message),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: notebookQueries.chatHistory(notebookId),
      });
    },
  });
};

export const useClearChatHistory = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => notebooksApi.chat.clearHistory(notebookId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: notebookQueries.chatHistory(notebookId),
      });
    },
  });
};

// Knowledge Base Queries
export const useKnowledgeBaseItems = (notebookId: string, params?: any) => {
  return useQuery({
    queryKey: [...notebookQueries.knowledgeBase(notebookId), 'items', params],
    queryFn: () => notebooksApi.knowledgeBase.getItems(notebookId, params),
    enabled: !!notebookId,
    staleTime: 5 * 60 * 1000,
  });
};

export const useSearchKnowledgeBase = (notebookId: string, query: string) => {
  return useQuery({
    queryKey: [...notebookQueries.knowledgeBase(notebookId), 'search', query],
    queryFn: () => notebooksApi.knowledgeBase.searchItems(notebookId, query),
    enabled: !!notebookId && query.length > 2,
    staleTime: 2 * 60 * 1000,
  });
};