/**
 * React 18 Concurrent Features Hooks
 * Implements modern React patterns for performance optimization
 */

import { 
  useTransition, 
  useDeferredValue, 
  useId,
  startTransition,
  useMemo,
  useCallback,
  useState,
  useEffect,
  useRef
} from 'react';

// Hook for deferred search with transition
export const useDeferredSearch = (initialQuery: string = '') => {
  const [isPending, startTransition] = useTransition();
  const [query, setQuery] = useState(initialQuery);
  const deferredQuery = useDeferredValue(query);

  const updateQuery = useCallback((newQuery: string) => {
    startTransition(() => {
      setQuery(newQuery);
    });
  }, []);

  const clearQuery = useCallback(() => {
    startTransition(() => {
      setQuery('');
    });
  }, []);

  return {
    query,
    deferredQuery,
    isPending,
    updateQuery,
    clearQuery,
    isStale: query !== deferredQuery,
  };
};

// Hook for non-urgent updates
export const useNonUrgentUpdate = () => {
  const [isPending, startTransitionInternal] = useTransition();

  const performUpdate = useCallback((updateFn: () => void) => {
    startTransitionInternal(updateFn);
  }, [startTransitionInternal]);

  return {
    isPending,
    performUpdate,
  };
};

// Hook for accessible form IDs
export const useAccessibleIds = (baseId?: string) => {
  const generatedId = useId();
  const id = baseId || generatedId;

  return useMemo(() => ({
    id,
    labelId: `${id}-label`,
    descriptionId: `${id}-description`,
    errorId: `${id}-error`,
    helperId: `${id}-helper`,
  }), [id]);
};

// Hook for deferred expensive computations
export const useDeferredComputation = <T>(
  computeFn: () => T,
  dependencies: React.DependencyList
) => {
  const [result, setResult] = useState<T | null>(null);
  const [isPending, startTransition] = useTransition();
  const computedValue = useMemo(computeFn, dependencies);
  const deferredValue = useDeferredValue(computedValue);

  useEffect(() => {
    if (deferredValue !== result) {
      startTransition(() => {
        setResult(deferredValue);
      });
    }
  }, [deferredValue, result]);

  return {
    result: result ?? deferredValue,
    isPending,
    isStale: deferredValue !== result,
  };
};

// Hook for prioritized rendering
export const usePrioritizedRendering = () => {
  const [highPriorityState, setHighPriorityState] = useState<any>(null);
  const [lowPriorityState, setLowPriorityState] = useState<any>(null);
  const [isPending, startTransition] = useTransition();

  const updateHighPriority = useCallback((value: any) => {
    setHighPriorityState(value);
  }, []);

  const updateLowPriority = useCallback((value: any) => {
    startTransition(() => {
      setLowPriorityState(value);
    });
  }, []);

  return {
    highPriorityState,
    lowPriorityState,
    updateHighPriority,
    updateLowPriority,
    isPending,
  };
};

// Hook for batch updates
export const useBatchedUpdates = () => {
  const [updates, setUpdates] = useState<Array<() => void>>([]);
  const [isPending, startTransition] = useTransition();
  const timeoutRef = useRef<NodeJS.Timeout>();

  const scheduleUpdate = useCallback((updateFn: () => void) => {
    setUpdates(prev => [...prev, updateFn]);

    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Batch updates with a short delay
    timeoutRef.current = setTimeout(() => {
      startTransition(() => {
        setUpdates(currentUpdates => {
          currentUpdates.forEach(fn => fn());
          return [];
        });
      });
    }, 16); // Next frame
  }, []);

  const flushUpdates = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    startTransition(() => {
      setUpdates(currentUpdates => {
        currentUpdates.forEach(fn => fn());
        return [];
      });
    });
  }, []);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    scheduleUpdate,
    flushUpdates,
    isPending,
    pendingUpdatesCount: updates.length,
  };
};

// Hook for smart loading states
export const useSmartLoading = (isLoading: boolean, minimumLoadingTime: number = 500) => {
  const [shouldShowLoading, setShouldShowLoading] = useState(false);
  const [isPending, startTransition] = useTransition();
  const timeoutRef = useRef<NodeJS.Timeout>();
  const startTimeRef = useRef<number>();

  useEffect(() => {
    if (isLoading && !shouldShowLoading) {
      startTimeRef.current = Date.now();
      
      // Show loading after a short delay to avoid flickers
      timeoutRef.current = setTimeout(() => {
        startTransition(() => {
          setShouldShowLoading(true);
        });
      }, 100);
    } else if (!isLoading && shouldShowLoading) {
      const elapsed = Date.now() - (startTimeRef.current || 0);
      const remainingTime = Math.max(0, minimumLoadingTime - elapsed);

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      if (remainingTime > 0) {
        timeoutRef.current = setTimeout(() => {
          startTransition(() => {
            setShouldShowLoading(false);
          });
        }, remainingTime);
      } else {
        startTransition(() => {
          setShouldShowLoading(false);
        });
      }
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [isLoading, shouldShowLoading, minimumLoadingTime]);

  return {
    shouldShowLoading,
    isPending: isPending || (shouldShowLoading && !isLoading),
  };
};

// Hook for concurrent UI updates
export const useConcurrentUI = () => {
  const [urgentState, setUrgentState] = useState<any>(null);
  const [deferredState, setDeferredState] = useState<any>(null);
  const [isPending, startTransition] = useTransition();
  
  const deferredValue = useDeferredValue(deferredState);

  const updateUrgent = useCallback((value: any) => {
    setUrgentState(value);
  }, []);

  const updateDeferred = useCallback((value: any) => {
    startTransition(() => {
      setDeferredState(value);
    });
  }, []);

  const updateBoth = useCallback((urgentValue: any, deferredValue: any) => {
    setUrgentState(urgentValue);
    startTransition(() => {
      setDeferredState(deferredValue);
    });
  }, []);

  return {
    urgentState,
    deferredState: deferredValue,
    updateUrgent,
    updateDeferred,
    updateBoth,
    isPending,
    isStale: deferredState !== deferredValue,
  };
};

// Global transition for app-wide updates
export const useGlobalTransition = () => {
  const [isPending, startTransition] = useTransition();

  const performGlobalUpdate = useCallback((updateFn: () => void) => {
    startTransition(updateFn);
  }, []);

  // Wrapper for startTransition for direct use
  const transition = useCallback((callback: () => void) => {
    startTransition(callback);
  }, []);

  return {
    isPending,
    performGlobalUpdate,
    transition,
    startTransition, // Export the original for direct use
  };
};