/**
 * Performance monitoring and optimization utilities
 * Includes React 18 performance patterns and monitoring
 */

import { useCallback, useEffect, useRef, useMemo, useState } from 'react';
import { startTransition } from 'react';

// Performance metrics collection
export class PerformanceMonitor {
  private static instance: PerformanceMonitor;
  private metrics: Map<string, PerformanceEntry[]> = new Map();
  private observers: Map<string, PerformanceObserver> = new Map();

  static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor();
    }
    return PerformanceMonitor.instance;
  }

  // Start monitoring specific metrics
  startMonitoring(type: 'navigation' | 'resource' | 'measure' | 'paint') {
    if (this.observers.has(type) || typeof PerformanceObserver === 'undefined') {
      return;
    }

    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const existing = this.metrics.get(type) || [];
      this.metrics.set(type, [...existing, ...entries]);
    });

    try {
      observer.observe({ entryTypes: [type] });
      this.observers.set(type, observer);
    } catch (error) {
      console.warn(`Failed to observe ${type} performance:`, error);
    }
  }

  // Get collected metrics
  getMetrics(type?: string): PerformanceEntry[] {
    if (type) {
      return this.metrics.get(type) || [];
    }
    
    const allMetrics: PerformanceEntry[] = [];
    this.metrics.forEach((entries) => {
      allMetrics.push(...entries);
    });
    return allMetrics;
  }

  // Measure custom performance
  measure(name: string, startMark?: string, endMark?: string): PerformanceEntry | null {
    try {
      if (startMark && endMark) {
        return performance.measure(name, startMark, endMark);
      }
      return performance.measure(name);
    } catch (error) {
      console.warn(`Failed to measure ${name}:`, error);
      return null;
    }
  }

  // Mark performance points
  mark(name: string): PerformanceEntry | null {
    try {
      return performance.mark(name);
    } catch (error) {
      console.warn(`Failed to mark ${name}:`, error);
      return null;
    }
  }

  // Get Core Web Vitals
  getCoreWebVitals(): Record<string, number> {
    const vitals: Record<string, number> = {};

    // Largest Contentful Paint
    const lcpEntries = this.getMetrics('largest-contentful-paint');
    if (lcpEntries.length > 0) {
      const lastEntry = lcpEntries[lcpEntries.length - 1];
      if (lastEntry) {
        vitals.LCP = lastEntry.startTime;
      }
    }

    // First Input Delay
    const fidEntries = this.getMetrics('first-input');
    if (fidEntries.length > 0) {
      const firstEntry = fidEntries[0];
      if (firstEntry) {
        vitals.FID = (firstEntry as any).processingStart - firstEntry.startTime;
      }
    }

    // Cumulative Layout Shift
    const clsEntries = this.getMetrics('layout-shift');
    vitals.CLS = clsEntries.reduce((sum, entry) => {
      if (!(entry as any).hadRecentInput) {
        sum += (entry as any).value;
      }
      return sum;
    }, 0);

    return vitals;
  }

  // Cleanup observers
  disconnect(): void {
    this.observers.forEach((observer) => {
      observer.disconnect();
    });
    this.observers.clear();
  }
}

// React Performance Hooks
export const usePerformanceMonitor = () => {
  const monitor = useMemo(() => PerformanceMonitor.getInstance(), []);

  useEffect(() => {
    monitor.startMonitoring('navigation');
    monitor.startMonitoring('paint');
    monitor.startMonitoring('measure');

    return () => {
      monitor.disconnect();
    };
  }, [monitor]);

  return monitor;
};

// Hook for measuring component render time
export const useRenderTime = (componentName: string) => {
  const renderStartRef = useRef<number>(0);
  const monitor = PerformanceMonitor.getInstance();

  useEffect(() => {
    renderStartRef.current = performance.now();
    monitor.mark(`${componentName}-render-start`);

    return () => {
      const renderTime = performance.now() - renderStartRef.current;
      monitor.mark(`${componentName}-render-end`);
      monitor.measure(
        `${componentName}-render`,
        `${componentName}-render-start`,
        `${componentName}-render-end`
      );

      if (import.meta.env.DEV && renderTime > 16) {
        console.warn(`${componentName} rendered in ${renderTime.toFixed(2)}ms (>16ms)`);
      }
    };
  });
};

// Hook for debounced values with performance tracking
export const useDebouncedValue = <T>(value: T, delay: number = 300): T => {
  const [debouncedValue, setDebouncedValue] = useState(value);
  const timeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      startTransition(() => {
        setDebouncedValue(value);
      });
    }, delay);

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [value, delay]);

  return debouncedValue;
};

// Hook for throttled callbacks
export const useThrottledCallback = <T extends (...args: any[]) => any>(
  callback: T,
  delay: number = 100
): T => {
  const lastCallRef = useRef<number>(0);
  const timeoutRef = useRef<NodeJS.Timeout>();

  return useCallback(
    ((...args: Parameters<T>) => {
      const now = Date.now();
      
      if (now - lastCallRef.current >= delay) {
        lastCallRef.current = now;
        callback(...args);
      } else {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        
        timeoutRef.current = setTimeout(() => {
          lastCallRef.current = Date.now();
          callback(...args);
        }, delay - (now - lastCallRef.current));
      }
    }) as T,
    [callback, delay]
  );
};

// Memory usage monitoring
export const useMemoryMonitoring = (interval: number = 5000) => {
  const [memoryInfo, setMemoryInfo] = useState<any>(null);

  useEffect(() => {
    if (!('memory' in performance)) {
      return;
    }

    const updateMemoryInfo = () => {
      const memory = (performance as any).memory;
      setMemoryInfo({
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit,
        usedPercentage: (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100,
      });
    };

    updateMemoryInfo();
    const intervalId = setInterval(updateMemoryInfo, interval);

    return () => clearInterval(intervalId);
  }, [interval]);

  return memoryInfo;
};

// Bundle size optimization utilities
export const bundleOptimization = {
  // Preload critical resources
  preloadResource: (href: string, as: 'script' | 'style' | 'font' | 'image' = 'script') => {
    const link = document.createElement('link');
    link.rel = 'preload';
    link.href = href;
    link.as = as;
    if (as === 'font') {
      link.crossOrigin = 'anonymous';
    }
    document.head.appendChild(link);
  },

  // Prefetch resources for future navigation
  prefetchResource: (href: string) => {
    const link = document.createElement('link');
    link.rel = 'prefetch';
    link.href = href;
    document.head.appendChild(link);
  },

  // DNS prefetch for external domains
  dnsPrefetch: (domain: string) => {
    const link = document.createElement('link');
    link.rel = 'dns-prefetch';
    link.href = domain;
    document.head.appendChild(link);
  },

  // Preconnect to external domains
  preconnect: (domain: string, crossOrigin: boolean = false) => {
    const link = document.createElement('link');
    link.rel = 'preconnect';
    link.href = domain;
    if (crossOrigin) {
      link.crossOrigin = 'anonymous';
    }
    document.head.appendChild(link);
  },
};

// React 18 specific performance utilities
export const react18Performance = {
  // Batch multiple state updates
  batchUpdates: (updates: Array<() => void>) => {
    startTransition(() => {
      updates.forEach(update => update());
    });
  },

  // Prioritize urgent updates
  urgentUpdate: (update: () => void) => {
    // Regular state update - will be processed immediately
    update();
  },

  // Defer non-urgent updates
  deferredUpdate: (update: () => void) => {
    startTransition(update);
  },

  // Schedule updates for idle time
  scheduleIdleUpdate: (update: () => void) => {
    if ('requestIdleCallback' in window) {
      (window as any).requestIdleCallback(update);
    } else {
      setTimeout(update, 0);
    }
  },
};

// Web Vitals reporting
export const reportWebVitals = (onPerfEntry?: (entry: any) => void) => {
  if (onPerfEntry && onPerfEntry instanceof Function) {
    import('web-vitals').then((webVitals) => {
      if (webVitals.onCLS) webVitals.onCLS(onPerfEntry);
      if (webVitals.onINP) webVitals.onINP(onPerfEntry);
      if (webVitals.onFCP) webVitals.onFCP(onPerfEntry);
      if (webVitals.onLCP) webVitals.onLCP(onPerfEntry);
      if (webVitals.onTTFB) webVitals.onTTFB(onPerfEntry);
    }).catch(console.warn);
  }
};

// Performance budget checker
export class PerformanceBudget {
  private budgets: Map<string, number> = new Map([
    ['LCP', 2500], // 2.5s
    ['FID', 100],  // 100ms
    ['CLS', 0.1],  // 0.1
    ['FCP', 1800], // 1.8s
    ['TTFB', 800], // 800ms
  ]);

  setBudget(metric: string, value: number): void {
    this.budgets.set(metric, value);
  }

  checkBudget(metric: string, value: number): boolean {
    const budget = this.budgets.get(metric);
    return budget ? value <= budget : true;
  }

  validateAllMetrics(metrics: Record<string, number>): Record<string, boolean> {
    const results: Record<string, boolean> = {};
    
    Object.entries(metrics).forEach(([metric, value]) => {
      results[metric] = this.checkBudget(metric, value);
    });

    return results;
  }
}