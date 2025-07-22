import { useState, useCallback } from 'react';

/**
 * Generic async state management hook
 * Provides common patterns for handling async operations:
 * - Loading states
 * - Error handling
 * - Data management
 * - Success/failure tracking
 */
export const useAsyncState = <T = any, E = string>() => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<E | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  /**
   * Execute an async operation with automatic state management
   * @param operation - Async function to execute
   * @param options - Configuration options
   * @returns Promise with operation result
   */
  const execute = useCallback(async <R = T>(
    operation: () => Promise<R>,
    options: {
      onSuccess?: (result: R) => void;
      onError?: (error: E) => void;
      updateData?: boolean;
      clearError?: boolean;
    } = {}
  ): Promise<{ success: boolean; data?: R; error?: E }> => {
    const { onSuccess, onError, updateData = true, clearError = true } = options;

    setLoading(true);
    if (clearError) setError(null);

    try {
      const result = await operation();
      
      if (updateData) {
        setData(result as T);
      }
      
      setLastUpdated(Date.now());
      setLoading(false);
      
      if (onSuccess) {
        onSuccess(result);
      }
      
      return { success: true, data: result };
    } catch (err) {
      const errorMessage = (err instanceof Error ? err.message : 'Unknown error') as E;
      setError(errorMessage);
      setLoading(false);
      
      if (onError) {
        onError(errorMessage);
      }
      
      return { success: false, error: errorMessage };
    }
  }, []);

  /**
   * Clear all state
   */
  const clear = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
    setLastUpdated(null);
  }, []);

  /**
   * Clear only error state
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Set data directly
   */
  const setDataDirectly = useCallback((newData: T) => {
    setData(newData);
    setLastUpdated(Date.now());
  }, []);

  /**
   * Set error directly
   */
  const setErrorDirectly = useCallback((newError: E) => {
    setError(newError);
  }, []);

  /**
   * Set loading state directly
   */
  const setLoadingDirectly = useCallback((isLoading: boolean) => {
    setLoading(isLoading);
  }, []);

  /**
   * Check if data is stale (older than specified time)
   * @param maxAge - Maximum age in milliseconds
   * @returns True if data is stale or doesn't exist
   */
  const isStale = useCallback((maxAge: number = 5 * 60 * 1000): boolean => {
    if (!lastUpdated) return true;
    return Date.now() - lastUpdated > maxAge;
  }, [lastUpdated]);

  /**
   * Get time since last update
   * @returns Time in milliseconds, or null if never updated
   */
  const getTimeSinceUpdate = useCallback((): number | null => {
    if (!lastUpdated) return null;
    return Date.now() - lastUpdated;
  }, [lastUpdated]);

  return {
    // State
    data,
    loading,
    error,
    lastUpdated,
    
    // Actions
    execute,
    clear,
    clearError,
    setData: setDataDirectly,
    setError: setErrorDirectly,
    setLoading: setLoadingDirectly,
    
    // Utilities
    isStale,
    getTimeSinceUpdate,
    
    // Computed
    hasData: data !== null,
    hasError: error !== null,
    isIdle: !loading && !error && data === null,
  };
}; 