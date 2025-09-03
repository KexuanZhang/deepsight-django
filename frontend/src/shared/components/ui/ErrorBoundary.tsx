/**
 * Error Boundary Component with enhanced error handling
 */

import React, { ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: React.ComponentType<ErrorFallbackProps>;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  level?: 'page' | 'section' | 'component';
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export interface ErrorFallbackProps {
  error: Error;
  errorInfo: ErrorInfo | null;
  retry: () => void;
  level?: 'page' | 'section' | 'component';
}

const DefaultErrorFallback: React.FC<ErrorFallbackProps> = ({ 
  error, 
  errorInfo, 
  retry, 
  level = 'component' 
}) => {
  const isDevMode = import.meta.env.DEV;
  
  const containerClasses = {
    page: 'min-h-screen flex items-center justify-center bg-gray-50',
    section: 'py-16 px-4 text-center bg-gray-50 rounded-lg',
    component: 'p-6 text-center bg-red-50 border border-red-200 rounded-md'
  };

  const iconSizes = {
    page: 'w-16 h-16',
    section: 'w-12 h-12',
    component: 'w-8 h-8'
  };

  const textSizes = {
    page: 'text-xl',
    section: 'text-lg',
    component: 'text-base'
  };

  return (
    <div className={containerClasses[level]}>
      <div className="max-w-md mx-auto">
        <div className="flex justify-center mb-4">
          <AlertTriangle className={`${iconSizes[level]} text-red-500`} />
        </div>
        
        <h3 className={`${textSizes[level]} font-semibold text-gray-900 mb-2`}>
          {level === 'page' ? 'Something went wrong' : 'Error occurred'}
        </h3>
        
        <p className="text-gray-600 mb-4">
          {error.message || 'An unexpected error occurred. Please try again.'}
        </p>
        
        <button
          onClick={retry}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Try Again
        </button>
        
        {isDevMode && errorInfo && (
          <details className="mt-6 text-left">
            <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700">
              Developer Information
            </summary>
            <div className="mt-2 p-3 bg-gray-100 rounded text-xs font-mono text-gray-800 overflow-auto max-h-40">
              <div className="mb-2">
                <strong>Error:</strong> {error.name}: {error.message}
              </div>
              {error.stack && (
                <div className="mb-2">
                  <strong>Stack:</strong>
                  <pre className="whitespace-pre-wrap">{error.stack}</pre>
                </div>
              )}
              {errorInfo.componentStack && (
                <div>
                  <strong>Component Stack:</strong>
                  <pre className="whitespace-pre-wrap">{errorInfo.componentStack}</pre>
                </div>
              )}
            </div>
          </details>
        )}
      </div>
    </div>
  );
};

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      errorInfo,
    });

    // Call the onError callback if provided
    this.props.onError?.(error, errorInfo);

    // Log to external error reporting service in production
    if (import.meta.env.PROD) {
      // TODO: Integrate with error reporting service (e.g., Sentry)
      console.error('Production error:', {
        error: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
      });
    }
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  override render() {
    if (this.state.hasError && this.state.error) {
      const FallbackComponent = this.props.fallback || DefaultErrorFallback;
      
      return (
        <FallbackComponent
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          retry={this.handleRetry}
          level={this.props.level || 'component'}
        />
      );
    }

    return this.props.children;
  }
}

// HOC for wrapping components with error boundary
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${
    Component.displayName || Component.name || 'Component'
  })`;

  return WrappedComponent;
}

// Hook for imperative error handling
export const useErrorBoundary = () => {
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    if (error) {
      throw error;
    }
  }, [error]);

  const captureError = React.useCallback((error: Error | string) => {
    const errorObj = typeof error === 'string' ? new Error(error) : error;
    setError(errorObj);
  }, []);

  return { captureError };
};