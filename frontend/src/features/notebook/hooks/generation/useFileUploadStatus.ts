import { useState, useEffect, useRef, useCallback } from 'react';
import apiService from '@/common/utils/api';

export interface FileUploadStatus {
  uploadFileId: string;
  status: string;
  progress?: string;
  error?: string;
  fileId?: string;
  metadata?: any;
}

export const useFileUploadStatus = (
  notebookId: string,
  onStatusUpdate: (status: FileUploadStatus) => void,
  onComplete: (fileId: string, uploadFileId: string) => void,
  onError: (error: string, uploadFileId: string) => void
) => {
  const [activeUploads, setActiveUploads] = useState<Set<string>>(new Set());
  const sseConnectionsRef = useRef<Map<string, EventSource>>(new Map());
  
  // Store callbacks in refs to avoid recreating connections when they change
  const onStatusUpdateRef = useRef(onStatusUpdate);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  // Update refs when props change
  useEffect(() => {
    onStatusUpdateRef.current = onStatusUpdate;
  }, [onStatusUpdate]);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const startTracking = useCallback((uploadFileId: string) => {
    if (!uploadFileId || !notebookId) {
      console.warn('Missing uploadFileId or notebookId for file upload tracking');
      return;
    }

    // Don't start tracking if already tracking this upload
    if (sseConnectionsRef.current.has(uploadFileId)) {
      console.log(`Already tracking upload: ${uploadFileId}`);
      return;
    }

    console.log(`Starting file upload status tracking for: ${uploadFileId}`);

    setActiveUploads(prev => new Set(prev).add(uploadFileId));

    try {
      const eventSource = apiService.createStatusStream(
        uploadFileId,
        notebookId,
        (data) => {
          console.log(`File upload status update for ${uploadFileId}:`, data);
          
          const statusUpdate: FileUploadStatus = {
            uploadFileId,
            status: data.parsing_status || data.status || 'processing',
            progress: data.progress,
            error: data.error_message || data.error,
            fileId: data.file_id,
            metadata: data
          };

          // Notify parent component of status update
          if (onStatusUpdateRef.current) {
            onStatusUpdateRef.current(statusUpdate);
          }

          // Handle completion
          if (data.parsing_status === 'completed' || data.status === 'completed') {
            console.log(`File upload completed for ${uploadFileId}, file_id: ${data.file_id}`);
            
            if (onCompleteRef.current && data.file_id) {
              onCompleteRef.current(data.file_id, uploadFileId);
            }
            
            stopTracking(uploadFileId);
          }
          
          // Handle errors
          else if (data.parsing_status === 'failed' || data.status === 'failed' || data.error || data.error_message) {
            console.log(`File upload failed for ${uploadFileId}:`, data.error_message || data.error);
            
            if (onErrorRef.current) {
              onErrorRef.current(data.error_message || data.error || 'Upload failed', uploadFileId);
            }
            
            stopTracking(uploadFileId);
          }
        },
        (error) => {
          console.error(`SSE error for upload ${uploadFileId}:`, error);
          
          if (onErrorRef.current) {
            onErrorRef.current('Connection error during upload', uploadFileId);
          }
          
          stopTracking(uploadFileId);
        },
        () => {
          console.log(`SSE connection closed for upload: ${uploadFileId}`);
          stopTracking(uploadFileId);
        }
      );

      sseConnectionsRef.current.set(uploadFileId, eventSource);
      
    } catch (error) {
      console.error(`Failed to start tracking upload ${uploadFileId}:`, error);
      setActiveUploads(prev => {
        const newSet = new Set(prev);
        newSet.delete(uploadFileId);
        return newSet;
      });
      
      if (onErrorRef.current) {
        onErrorRef.current('Failed to start status tracking', uploadFileId);
      }
    }
  }, [notebookId]);

  const stopTracking = useCallback((uploadFileId: string) => {
    console.log(`Stopping file upload tracking for: ${uploadFileId}`);
    
    const eventSource = sseConnectionsRef.current.get(uploadFileId);
    if (eventSource) {
      eventSource.close();
      sseConnectionsRef.current.delete(uploadFileId);
    }
    
    setActiveUploads(prev => {
      const newSet = new Set(prev);
      newSet.delete(uploadFileId);
      return newSet;
    });
  }, []);

  const stopAllTracking = useCallback(() => {
    console.log('Stopping all file upload tracking');
    
    sseConnectionsRef.current.forEach((eventSource, uploadFileId) => {
      eventSource.close();
    });
    
    sseConnectionsRef.current.clear();
    setActiveUploads(new Set());
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopAllTracking();
    };
  }, [stopAllTracking]);

  return {
    activeUploads: Array.from(activeUploads),
    startTracking,
    stopTracking,
    stopAllTracking,
    isTracking: (uploadFileId: string) => activeUploads.has(uploadFileId)
  };
};