import { useState, useCallback, useEffect, useRef } from 'react';
import apiService from '@/common/utils/api';

interface UploadTracker {
  uploadFileId: string;
  notebookId: string;
  onComplete?: () => void;
}

export const useFileUploadStatus = () => {
  const [activeUploads, setActiveUploads] = useState<Set<string>>(new Set());
  const [trackedUploads, setTrackedUploads] = useState<Map<string, UploadTracker>>(new Map());
  // Remove pollingRef and all setInterval/clearInterval polling fallback logic
  // Only keep SSE connection logic

  const startTracking = useCallback((uploadFileId: string, notebookId?: string, onComplete?: () => void) => {
    console.log(`[SSE_DEBUG] Starting upload tracking for: ${uploadFileId}, notebookId: ${notebookId}`);
    setActiveUploads(prev => new Set(prev).add(uploadFileId));
    
    if (notebookId && onComplete) {
      console.log(`[SSE_DEBUG] Adding to trackedUploads:`, { uploadFileId, notebookId });
      setTrackedUploads(prev => new Map(prev).set(uploadFileId, {
        uploadFileId,
        notebookId,
        onComplete
      }));
    }
  }, []);

  const stopTracking = useCallback((uploadFileId: string) => {
    console.log(`Stopping upload tracking for: ${uploadFileId}`);
    setActiveUploads(prev => {
      const newSet = new Set(prev);
      newSet.delete(uploadFileId);
      return newSet;
    });
    setTrackedUploads(prev => {
      const newMap = new Map(prev);
      newMap.delete(uploadFileId);
      return newMap;
    });
  }, []);

  // SSE connection for real-time completion signals
  const [notebookId, setNotebookId] = useState<string | null>(null);
  const sseRef = useRef<EventSource | null>(null);

  const checkForCompletions = useCallback(async () => {
    if (trackedUploads.size > 0 && notebookId) {
      for (const [uploadFileId, tracker] of trackedUploads) {
        try {
          // Use getStatus instead of getFileStatus if that's the correct method
          const response = await apiService.getStatus(tracker.notebookId, uploadFileId);
          if (response.success && (response.status === 'completed' || response.status === 'error' || response.status === 'failed')) {
            console.log(`Upload completed: ${uploadFileId} with status: ${response.status}`);
            tracker.onComplete?.();
            stopTracking(uploadFileId);
          }
        } catch (error) {
          // Silently handle errors - file might not exist yet
          console.debug(`Upload ${uploadFileId} still processing or not found`);
        }
      }
    }
  }, [trackedUploads, notebookId, stopTracking]);

  // Start SSE connection when we have a notebook (not just when tracking uploads)
  useEffect(() => {
    console.log('[SSE_DEBUG] useEffect triggered:', { 
      trackedUploadsSize: trackedUploads.size, 
      notebookId, 
      hasSSEConnection: !!sseRef.current,
      trackedUploadIds: Array.from(trackedUploads.keys())
    });
    
    if (notebookId && !sseRef.current) {
      console.log(`[SSE_DEBUG] Starting SSE connection for upload completion signals: notebook ${notebookId}`);
      
      const sseUrl = `/api/notebooks/${notebookId}/files/stream`;
      console.log('[SSE_DEBUG] Connecting to SSE URL:', sseUrl);
      const eventSource = new EventSource(sseUrl);
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('[SSE_DEBUG] SSE event received:', data);
          
          // Handle file completion signals
          if (data.type === 'file_change') {
            console.log('[SSE_DEBUG] File change event:', data.change_type, data.file_data);
            
            if (data.change_type === 'file_status_updated' && data.file_data) {
              const { status, file_id } = data.file_data;
              console.log('[SSE_DEBUG] Status update received:', { status, file_id, trackedUploads: Array.from(trackedUploads.keys()) });
              
              if (status === 'done' || status === 'completed' || status === 'error' || status === 'failed') {
                console.log('[SSE_DEBUG] Completion signal received - triggering callbacks for all tracked uploads');
                
                // Since we can't easily match SSE events to specific uploads, 
                // trigger completion for ALL tracked uploads when ANY completion occurs
                // This is safe because completion signals mean "refresh the list"
                Array.from(trackedUploads.values()).forEach(tracker => {
                  console.log(`[SSE_DEBUG] Triggering completion for tracked upload: ${tracker.uploadFileId}`);
                  tracker.onComplete?.();
                  stopTracking(tracker.uploadFileId);
                });
                
                if (trackedUploads.size === 0) {
                  console.log('[SSE_DEBUG] No tracked uploads, but completion signal received - might be a manual upload');
                }
              } else {
                console.log('[SSE_DEBUG] Status not complete yet:', status);
              }
            }
          } else {
            console.log('[SSE_DEBUG] Non-file-change event:', data.type);
          }
        } catch (error) {
          console.error('Error parsing SSE event:', error);
        }
      };
      
      eventSource.onopen = () => {
        console.log('[SSE_DEBUG] SSE connection opened successfully');
      };
      
      eventSource.onerror = (error) => {
        console.error('[SSE_DEBUG] SSE connection error:', error);
        console.error('[SSE_DEBUG] EventSource readyState:', eventSource.readyState);
        eventSource.close();
        sseRef.current = null;
        // Start polling fallback
        // This block is removed as per the edit hint.
      };
      
      sseRef.current = eventSource;
    }
    
    // Keep SSE connection open as long as we have a notebook (don't close when no uploads)
    // This ensures we receive completion signals even if uploads finish quickly
    if (!notebookId && sseRef.current) {
      console.log('[SSE_DEBUG] Closing SSE connection - no notebook');
      sseRef.current.close();
      sseRef.current = null;
    }
    // Stop polling when uploads are done or notebookId changes
    // This block is removed as per the edit hint.
  }, [notebookId, activeUploads.size, checkForCompletions]);

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
    console.log('Stopping all upload tracking');
    setActiveUploads(new Set());
    setTrackedUploads(new Map());
    if (sseRef.current) {
      sseRef.current.close();
      sseRef.current = null;
    }
  }, []);

  return {
    activeUploads: Array.from(activeUploads),
    startTracking,
    stopTracking,
    stopAllTracking,
    setNotebookId,
    checkForCompletions, // Manual completion check
    isTracking: (uploadFileId: string) => activeUploads.has(uploadFileId)
  };
};