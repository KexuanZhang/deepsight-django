/**
 * Enhanced Loading Spinner Components
 */

import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from "@/shared/utils/utils";

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  color?: 'primary' | 'secondary' | 'white' | 'gray';
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
  xl: 'w-12 h-12'
};

const colorClasses = {
  primary: 'text-blue-600',
  secondary: 'text-gray-600',
  white: 'text-white',
  gray: 'text-gray-400'
};

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  className,
  color = 'primary'
}) => {
  return (
    <Loader2 
      className={cn(
        'animate-spin',
        sizeClasses[size],
        colorClasses[color],
        className
      )}
    />
  );
};

interface LoadingOverlayProps {
  isVisible: boolean;
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  isVisible,
  message = 'Loading...',
  size = 'lg',
  className
}) => {
  if (!isVisible) return null;

  return (
    <div 
      className={cn(
        'absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-50',
        className
      )}
    >
      <div className="flex flex-col items-center space-y-3">
        <LoadingSpinner size={size} />
        {message && (
          <p className="text-sm text-gray-600 font-medium">{message}</p>
        )}
      </div>
    </div>
  );
};

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'rectangular' | 'circular' | 'rounded';
  width?: string | number;
  height?: string | number;
  lines?: number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = 'rectangular',
  width,
  height,
  lines = 1
}) => {
  const variantClasses = {
    text: 'h-4 rounded',
    rectangular: 'rounded',
    circular: 'rounded-full',
    rounded: 'rounded-lg'
  };

  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === 'number' ? `${width}px` : width;
  if (height) style.height = typeof height === 'number' ? `${height}px` : height;

  if (variant === 'text' && lines > 1) {
    return (
      <div className={cn('space-y-2', className)}>
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            className={cn(
              'bg-gray-200 animate-pulse',
              variantClasses[variant],
              index === lines - 1 && 'w-3/4' // Last line is shorter
            )}
            style={index === lines - 1 ? { ...style, width: undefined } : style}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'bg-gray-200 animate-pulse',
        variantClasses[variant],
        className
      )}
      style={style}
    />
  );
};

interface PageLoadingProps {
  message?: string;
}

export const PageLoading: React.FC<PageLoadingProps> = ({
  message = 'Loading page...'
}) => {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex flex-col items-center space-y-4">
        <LoadingSpinner size="xl" />
        <p className="text-lg text-gray-600">{message}</p>
      </div>
    </div>
  );
};

interface InlineLoadingProps {
  message?: string;
  size?: 'sm' | 'md';
  className?: string;
}

export const InlineLoading: React.FC<InlineLoadingProps> = ({
  message,
  size = 'sm',
  className
}) => {
  return (
    <div className={cn('flex items-center space-x-2', className)}>
      <LoadingSpinner size={size} />
      {message && (
        <span className="text-sm text-gray-600">{message}</span>
      )}
    </div>
  );
};

// Skeleton components for specific use cases
export const NotebookSkeleton: React.FC = () => {
  return (
    <div className="p-4 border rounded-lg">
      <Skeleton variant="text" height={24} className="mb-2" />
      <Skeleton variant="text" height={16} lines={2} className="mb-4" />
      <div className="flex justify-between items-center">
        <Skeleton variant="rectangular" width={60} height={20} />
        <Skeleton variant="rectangular" width={80} height={32} />
      </div>
    </div>
  );
};

export const NotebookGridSkeleton: React.FC<{ count?: number }> = ({ 
  count = 6 
}) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {Array.from({ length: count }).map((_, index) => (
        <NotebookSkeleton key={index} />
      ))}
    </div>
  );
};

export const ChatSkeleton: React.FC = () => {
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, index) => (
        <div key={index} className="flex space-x-3">
          <Skeleton variant="circular" width={32} height={32} />
          <div className="flex-1 space-y-2">
            <Skeleton variant="text" height={16} />
            <Skeleton variant="text" height={16} lines={2} />
          </div>
        </div>
      ))}
    </div>
  );
};