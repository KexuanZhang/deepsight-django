/**
 * TanStack Query client configuration
 */

import { QueryClient } from '@tanstack/react-query';
import { ApiError } from '../api';

// Default query client configuration
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Stale time: data is considered fresh for 5 minutes
      staleTime: 5 * 60 * 1000,
      // Garbage collection time: data is kept in cache for 10 minutes
      gcTime: 10 * 60 * 1000,
      // Retry configuration
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors (client errors)
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false;
        }
        // Retry up to 3 times for other errors
        return failureCount < 3;
      },
      // Retry delay with exponential backoff
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      // Refetch on window focus in production
      refetchOnWindowFocus: import.meta.env.PROD,
      // Network mode
      networkMode: 'online',
    },
    mutations: {
      // Retry mutations once on network error
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 1;
      },
      // Network mode
      networkMode: 'online',
    },
  },
});

// Test query client for testing
export const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });