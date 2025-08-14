import { useState, useCallback, useEffect, useRef } from 'react';
import { config } from '@/config';

interface UploadTracker {
  uploadFileId: string;
  notebookId: string;
  onComplete?: () => void;
}

export const useFileUploadStatus = () => {
  const [trackedUploads, setTrackedUploads] = useState<Map<string, UploadTracker>>(new Map());

  // Optional callback invoked when any file completes (even if not actively tracked)
  const onAnyFileCompleteRef = useRef<(() => void) | null>(null);
  const setOnAnyFileComplete = useCallback((cb?: () => void) => {
    onAnyFileCompleteRef.current = cb || null;
  }, []);

  const startTracking = useCallback((uploadFileId: string, notebookId?: string, onComplete?: () => void) => {
    if (notebookId && onComplete) {
      setTrackedUploads(prev => new Map(prev).set(uploadFileId, {
        uploadFileId,
        notebookId,
        onComplete
      }));
    }
  }, []);

  const stopTracking = useCallback((uploadFileId: string) => {
    setTrackedUploads(prev => {
      const newMap = new Map(prev);
      newMap.delete(uploadFileId);
      return newMap;
    });
  }, []);

  // SSE connection for real-time completion signals
  const [notebookId, setNotebookId] = useState<string | null>(null);
  const sseRef = useRef<EventSource | null>(null);

  // Start SSE connection when we have a notebook
  useEffect(() => {
    if (notebookId && !sseRef.current) {
      const sseUrl = `${config.API_BASE_URL}/notebooks/${notebookId}/files/stream`;
      const eventSource = new EventSource(sseUrl, {
        withCredentials: true // Include cookies for session authentication
      });
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'file_change' && data.change_type === 'file_status_updated' && data.file_data) {
            const { status, file_id } = data.file_data;
            
            if (status === 'done' || status === 'completed' || status === 'error' || status === 'failed') {
              const tracker = trackedUploads.get(file_id);
              if (tracker) {
                tracker.onComplete?.();
                stopTracking(file_id);
              } else {
                // Trigger general refresh for events like caption generation completion
                onAnyFileCompleteRef.current?.();
              }
            }
          }
        } catch (error) {
          console.error('Error parsing SSE event:', error);
        }
      };
      
      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        eventSource.close();
        sseRef.current = null;
      };
      
      sseRef.current = eventSource;
    }
    
    if (!notebookId && sseRef.current) {
      sseRef.current.close();
      sseRef.current = null;
    }
  }, [notebookId, stopTracking]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (sseRef.current) {
        sseRef.current.close();
      }
      // This block is removed as per the edit hint.
    };
  }, []);

  const stopAllTracking = useCallback(() => {
    setTrackedUploads(new Map());
    if (sseRef.current) {
      sseRef.current.close();
      sseRef.current = null;
    }
  }, []);

  return {
    startTracking,
    stopTracking,
    stopAllTracking,
    setNotebookId,
    setOnAnyFileComplete
  };
};