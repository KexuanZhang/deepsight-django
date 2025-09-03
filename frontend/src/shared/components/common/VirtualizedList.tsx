/**
 * Virtualized List Component for handling large datasets efficiently
 * Uses windowing technique to render only visible items
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { cn } from "@/shared/utils/utils";

export interface VirtualizedListProps<T> {
  items: T[];
  itemHeight: number;
  containerHeight: number;
  renderItem: (item: T, index: number, style: React.CSSProperties) => React.ReactNode;
  className?: string;
  overscan?: number;
  onScroll?: (scrollTop: number) => void;
  loading?: boolean;
  LoadingComponent?: React.ComponentType;
  EmptyComponent?: React.ComponentType;
}

interface VisibleRange {
  start: number;
  end: number;
}

export function VirtualizedList<T>({
  items,
  itemHeight,
  containerHeight,
  renderItem,
  className,
  overscan = 5,
  onScroll,
  loading = false,
  LoadingComponent,
  EmptyComponent,
}: VirtualizedListProps<T>) {
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // Calculate which items should be visible
  const visibleRange = useMemo((): VisibleRange => {
    if (items.length === 0) {
      return { start: 0, end: 0 };
    }

    const start = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const visibleCount = Math.ceil(containerHeight / itemHeight);
    const end = Math.min(items.length, start + visibleCount + overscan * 2);

    return { start, end };
  }, [scrollTop, itemHeight, containerHeight, items.length, overscan]);

  // Handle scroll events
  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const newScrollTop = event.currentTarget.scrollTop;
    setScrollTop(newScrollTop);
    onScroll?.(newScrollTop);
  }, [onScroll]);

  // Calculate total height and offset
  const totalHeight = items.length * itemHeight;
  const offsetY = visibleRange.start * itemHeight;

  // Generate visible items with positioning
  const visibleItems = useMemo(() => {
    return items.slice(visibleRange.start, visibleRange.end).map((item, index) => {
      const actualIndex = visibleRange.start + index;
      const style: React.CSSProperties = {
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: itemHeight,
        transform: `translateY(${actualIndex * itemHeight}px)`,
      };

      return {
        item,
        index: actualIndex,
        style,
        key: actualIndex,
      };
    });
  }, [items, visibleRange, itemHeight]);

  // Loading state
  if (loading && LoadingComponent) {
    return (
      <div className={cn('relative overflow-hidden', className)} style={{ height: containerHeight }}>
        <LoadingComponent />
      </div>
    );
  }

  // Empty state
  if (items.length === 0 && EmptyComponent) {
    return (
      <div className={cn('relative overflow-hidden', className)} style={{ height: containerHeight }}>
        <EmptyComponent />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn('relative overflow-auto', className)}
      style={{ height: containerHeight }}
      onScroll={handleScroll}
    >
      {/* Total height container */}
      <div style={{ height: totalHeight, position: 'relative' }}>
        {/* Visible items container */}
        <div
          style={{
            position: 'relative',
            height: (visibleRange.end - visibleRange.start) * itemHeight,
            transform: `translateY(${offsetY}px)`,
          }}
        >
          {visibleItems.map(({ item, index, style, key }) =>
            <div key={key} style={style}>
              {renderItem(item, index, style)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Hook for virtualized list state management
export const useVirtualizedList = <T,>(
  items: T[],
  itemHeight: number,
  containerHeight: number
) => {
  const [scrollTop, setScrollTop] = useState(0);

  const scrollToIndex = useCallback((index: number, behavior: 'auto' | 'smooth' = 'auto') => {
    const targetScrollTop = index * itemHeight;
    setScrollTop(targetScrollTop);
    
    // If we have a container ref, scroll it directly
    return targetScrollTop;
  }, [itemHeight]);

  const scrollToTop = useCallback((behavior: 'auto' | 'smooth' = 'smooth') => {
    setScrollTop(0);
    return 0;
  }, []);

  const scrollToBottom = useCallback((behavior: 'auto' | 'smooth' = 'smooth') => {
    const targetScrollTop = Math.max(0, items.length * itemHeight - containerHeight);
    setScrollTop(targetScrollTop);
    return targetScrollTop;
  }, [items.length, itemHeight, containerHeight]);

  return {
    scrollTop,
    scrollToIndex,
    scrollToTop,
    scrollToBottom,
    setScrollTop,
  };
};

// Virtualized Grid Component for 2D layouts
interface VirtualizedGridProps<T> {
  items: T[];
  itemWidth: number;
  itemHeight: number;
  containerWidth: number;
  containerHeight: number;
  columnsCount?: number;
  renderItem: (item: T, index: number, style: React.CSSProperties) => React.ReactNode;
  className?: string;
  gap?: number;
}

export function VirtualizedGrid<T>({
  items,
  itemWidth,
  itemHeight,
  containerWidth,
  containerHeight,
  columnsCount,
  renderItem,
  className,
  gap = 0,
}: VirtualizedGridProps<T>) {
  const [scrollTop, setScrollTop] = useState(0);
  
  // Calculate columns based on container width or use provided count
  const columns = columnsCount || Math.floor((containerWidth + gap) / (itemWidth + gap));
  const rows = Math.ceil(items.length / columns);

  // Calculate visible range
  const rowHeight = itemHeight + gap;
  const startRow = Math.max(0, Math.floor(scrollTop / rowHeight) - 1);
  const visibleRows = Math.ceil(containerHeight / rowHeight) + 2;
  const endRow = Math.min(rows, startRow + visibleRows);

  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(event.currentTarget.scrollTop);
  }, []);

  const visibleItems = useMemo(() => {
    const visible = [];
    
    for (let row = startRow; row < endRow; row++) {
      for (let col = 0; col < columns; col++) {
        const index = row * columns + col;
        
        if (index >= items.length) break;
        
        const x = col * (itemWidth + gap);
        const y = row * (itemHeight + gap);
        
        const style: React.CSSProperties = {
          position: 'absolute',
          left: x,
          top: y,
          width: itemWidth,
          height: itemHeight,
        };

        const item = items[index];
        if (item) {
          visible.push({
            item,
          index,
          style,
          key: index,
          });
        }
      }
    }
    
    return visible;
  }, [items, startRow, endRow, columns, itemWidth, itemHeight, gap]);

  const totalHeight = rows * rowHeight;

  return (
    <div
      className={cn('relative overflow-auto', className)}
      style={{ width: containerWidth, height: containerHeight }}
      onScroll={handleScroll}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        {visibleItems.map(({ item, index, style, key }) => (
          <div key={key} style={style}>
            {renderItem(item, index, style)}
          </div>
        ))}
      </div>
    </div>
  );
}