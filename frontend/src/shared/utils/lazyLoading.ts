/**
 * Enhanced lazy loading utilities for better performance
 * Includes preloading, retry logic, and loading states
 */

import React, { Suspense, ComponentType, lazy } from 'react';
import { ErrorBoundary } from "@/shared/components/ui/ErrorBoundary";
import { LoadingSpinner, PageLoading } from "@/shared/components/ui/LoadingSpinner";

// Types
interface LazyComponentOptions {
  fallback?: React.ComponentType;
  retryDelay?: number;
  maxRetries?: number;
  preload?: boolean;
  chunkName?: string;
}

interface LazyImportResult<T> {
  Component: ComponentType<T>;
  preload: () => Promise<void>;
  reload: () => Promise<void>;
}

// Enhanced lazy loading with retry logic
export function createLazyComponent<T = any>(
  importFn: () => Promise<{ default: ComponentType<T> }>,
  options: LazyComponentOptions = {}
): LazyImportResult<T> {
  const {
    fallback: FallbackComponent = LoadingSpinner,
    retryDelay = 1000,
    maxRetries = 3,
    preload = false,
  } = options;

  let componentPromise: Promise<{ default: ComponentType<T> }> | null = null;
  let retryCount = 0;

  const loadComponent = (): Promise<{ default: ComponentType<T> }> => {
    if (componentPromise) {
      return componentPromise;
    }

    componentPromise = importFn().catch((error) => {
      console.error('Failed to load component:', error);
      componentPromise = null;

      if (retryCount < maxRetries) {
        retryCount++;
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve(loadComponent());
          }, retryDelay * retryCount);
        });
      }

      throw error;
    });

    return componentPromise;
  };

  const LazyComponent = lazy(loadComponent);

  const Component: ComponentType<T> = (props) => {
    return React.createElement(ErrorBoundary, { 
      level: "component",
      children: React.createElement(Suspense, { 
        fallback: React.createElement(FallbackComponent),
        children: React.createElement(LazyComponent, props as any)
      })
    });
  };

  const preloadFn = async (): Promise<void> => {
    try {
      await loadComponent();
    } catch (error) {
      console.warn('Failed to preload component:', error);
    }
  };

  const reloadFn = async (): Promise<void> => {
    componentPromise = null;
    retryCount = 0;
    await loadComponent();
  };

  // Auto-preload if requested
  if (preload) {
    preloadFn();
  }

  return {
    Component,
    preload: preloadFn,
    reload: reloadFn,
  };
}

// Route-based lazy loading
export function createLazyRoute<T = any>(
  importFn: () => Promise<{ default: ComponentType<T> }>,
  pageName?: string
) {
  return createLazyComponent(importFn, {
    fallback: () => React.createElement(PageLoading, { 
      message: `Loading ${pageName || 'page'}...` 
    }),
    maxRetries: 2,
    retryDelay: 1500,
  });
}

// Feature-based lazy loading
export function createLazyFeature<T = any>(
  importFn: () => Promise<{ default: ComponentType<T> }>,
  featureName?: string
) {
  return createLazyComponent(importFn, {
    fallback: () => React.createElement('div', 
      { className: "flex items-center justify-center h-64" },
      React.createElement('div', 
        { className: "text-center" },
        React.createElement(LoadingSpinner, { size: "lg" }),
        React.createElement('p', 
          { className: "mt-2 text-sm text-gray-600" },
          `Loading ${featureName || 'feature'}...`
        )
      )
    ),
    maxRetries: 3,
    retryDelay: 1000,
  });
}

// Preload multiple components
export const preloadComponents = async (
  components: Array<LazyImportResult<any>>
): Promise<void> => {
  try {
    await Promise.all(components.map((comp) => comp.preload()));
  } catch (error) {
    console.warn('Some components failed to preload:', error);
  }
};

// Intersection Observer based lazy loading for components
export function createIntersectionLazyComponent<T = any>(
  importFn: () => Promise<{ default: ComponentType<T> }>,
  options: LazyComponentOptions & { 
    rootMargin?: string;
    threshold?: number;
  } = {}
) {
  const { rootMargin = '100px', threshold = 0.1, ...lazyOptions } = options;
  const lazyResult = createLazyComponent(importFn, lazyOptions);

  const IntersectionComponent: ComponentType<T> = (props) => {
    const [isVisible, setIsVisible] = React.useState(false);
    const ref = React.useRef<HTMLDivElement>(null);

    React.useEffect(() => {
      const observer = new IntersectionObserver(
        (entries) => {
          const entry = entries[0];
          if (entry && entry.isIntersecting) {
            setIsVisible(true);
            observer.disconnect();
          }
        },
        {
          rootMargin,
          threshold,
        }
      );

      if (ref.current) {
        observer.observe(ref.current);
      }

      return () => observer.disconnect();
    }, []);

    return React.createElement('div', 
      { ref },
      isVisible 
        ? React.createElement(lazyResult.Component, props as any)
        : React.createElement('div', 
            { className: "h-32 flex items-center justify-center" },
            React.createElement(LoadingSpinner, { size: "sm" })
          )
    );
  };

  return {
    Component: IntersectionComponent,
    preload: lazyResult.preload,
    reload: lazyResult.reload,
  };
}

// Hook for managing lazy loading state
export const useLazyLoading = (components: LazyImportResult<any>[]) => {
  const [loadingStates, setLoadingStates] = React.useState<Record<string, boolean>>({});

  const preloadComponent = React.useCallback(async (index: number) => {
    const component = components[index];
    if (!component) return;

    setLoadingStates(prev => ({ ...prev, [index]: true }));
    
    try {
      await component.preload();
    } finally {
      setLoadingStates(prev => ({ ...prev, [index]: false }));
    }
  }, [components]);

  const preloadAll = React.useCallback(async () => {
    await Promise.all(
      components.map((_, index) => preloadComponent(index))
    );
  }, [components, preloadComponent]);

  return {
    loadingStates,
    preloadComponent,
    preloadAll,
  };
};

// Bundle splitting utilities
export const bundleUtils = {
  // Split vendor libraries
  vendor: {
    react: () => import('react'),
    reactDom: () => import('react-dom'),
    reactQuery: () => import('@tanstack/react-query'),
    reactTable: () => import('@tanstack/react-table'),
  },
  
  // Split feature bundles
  features: {
    notebook: () => import("@/features/notebook/pages/NotebookListPage"),
    report: () => import("@/features/report/pages/ReportPage"),
    podcast: () => import("@/features/podcast/pages/PodcastPage"),
    conference: () => import("@/features/conference/pages/ConferencePage"),
  },
  
  // Split UI bundles
  ui: {
    dataTable: () => import("@/shared/components/ui/DataTable"),
    virtualizedList: () => import('@/shared/components/common/VirtualizedList'),
    errorBoundary: () => import("@/shared/components/ui/ErrorBoundary"),
  },
};

// Performance monitoring for lazy loading
export class LazyLoadingPerformance {
  private static instance: LazyLoadingPerformance;
  private loadTimes: Map<string, number> = new Map();
  private loadCounts: Map<string, number> = new Map();

  static getInstance(): LazyLoadingPerformance {
    if (!LazyLoadingPerformance.instance) {
      LazyLoadingPerformance.instance = new LazyLoadingPerformance();
    }
    return LazyLoadingPerformance.instance;
  }

  startLoad(componentName: string): void {
    this.loadTimes.set(componentName, performance.now());
  }

  endLoad(componentName: string): number {
    const startTime = this.loadTimes.get(componentName);
    if (!startTime) return 0;

    const loadTime = performance.now() - startTime;
    this.loadTimes.delete(componentName);
    
    const currentCount = this.loadCounts.get(componentName) || 0;
    this.loadCounts.set(componentName, currentCount + 1);

    if (import.meta.env.DEV) {
      console.log(`Lazy loaded ${componentName} in ${loadTime.toFixed(2)}ms`);
    }

    return loadTime;
  }

  getStats(): Record<string, { count: number; averageTime: number }> {
    const stats: Record<string, { count: number; averageTime: number }> = {};
    
    this.loadCounts.forEach((count, componentName) => {
      stats[componentName] = {
        count,
        averageTime: 0, // Would need to track total time to calculate average
      };
    });

    return stats;
  }
}