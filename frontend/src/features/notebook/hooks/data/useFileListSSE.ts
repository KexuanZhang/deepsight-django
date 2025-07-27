import { useEffect, useRef, useCallback } from 'react';
import apiService from '@/common/utils/api';

interface FileChangeEvent {
  type: 'initial' | 'file_change' | 'heartbeat' | 'error' | 'close';
  change_type?: 'file_added' | 'file_updated' | 'file_removed' | 'file_status_updated';
  files?: any[];
  timestamp: number;
  file_data?: {
    file_id: string;
    title: string;
    status?: string;
  };
  message?: string;
}

interface UseFileListSSEOptions {
  onFileListUpdate?: (files: any[]) => void;
  onFileChange?: (event: FileChangeEvent) => void;
  onError?: (error: string) => void;
  enabled?: boolean;
}

export const useFileListSSE = (notebookId: string, options: UseFileListSSEOptions = {}) => {
  const eventSourceRef = useRef<EventSource | null>(null);
  const { onFileListUpdate, onFileChange, onError, enabled = true } = options;

  const connect = useCallback(() => {
    if (!enabled || !notebookId || eventSourceRef.current) {
      return;
    }

    try {
      const eventSource = apiService.createFileListEventSource(notebookId);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        try {
          const data: FileChangeEvent = JSON.parse(event.data);
          
          // Handle different event types
          switch (data.type) {
            case 'initial':
              if (data.files && onFileListUpdate) {
                onFileListUpdate(data.files);
              }
              break;
              
            case 'file_change':
              if (data.files && onFileListUpdate) {
                onFileListUpdate(data.files);
              }
              if (onFileChange) {
                onFileChange(data);
              }
              break;
              
            case 'heartbeat':
              // Keep connection alive - no action needed
              console.debug('SSE heartbeat received');
              break;
              
            case 'error':
              console.error('SSE error event:', data.message);
              if (onError) {
                onError(data.message || 'SSE error occurred');
              }
              break;
              
            case 'close':
              console.log('SSE stream closed by server');
              disconnect();
              break;
              
            default:
              console.debug('Unknown SSE event type:', data.type);
          }
        } catch (parseError) {
          console.error('Error parsing SSE event data:', parseError);
          if (onError) {
            onError('Failed to parse server event data');
          }
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        if (onError) {
          onError('Real-time connection error. Falling back to manual refresh.');
        }
        
        // Close the connection immediately on error to prevent thread buildup
        disconnect();
        
        // Only attempt to reconnect once after a longer delay
        setTimeout(() => {
          if (enabled && notebookId && !eventSourceRef.current) {
            connect();
          }
        }, 10000); // 10 second delay instead of 5
      };

      eventSource.onopen = () => {
        console.log('SSE connection established for notebook:', notebookId);
      };

    } catch (error) {
      console.error('Failed to establish SSE connection:', error);
      if (onError) {
        onError('Failed to establish real-time connection');
      }
    }
  }, [notebookId, enabled, onFileListUpdate, onFileChange, onError]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      console.log('SSE connection closed');
    }
  }, []);

  // Connect when enabled
  useEffect(() => {
    if (enabled && notebookId) {
      connect();
    } else {
      disconnect();
    }

    return disconnect;
  }, [connect, disconnect, enabled, notebookId]);

  // Cleanup on unmount
  useEffect(() => {
    return disconnect;
  }, [disconnect]);

  return {
    isConnected: eventSourceRef.current?.readyState === EventSource.OPEN,
    connect,
    disconnect
  };
};