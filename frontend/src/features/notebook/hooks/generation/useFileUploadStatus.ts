import { useState, useCallback, useRef } from 'react';
import { config } from "@/config";

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

  // Simple notebook tracking without SSE
  const [notebookId, setNotebookId] = useState<string | null>(null);

  const stopAllTracking = useCallback(() => {
    setTrackedUploads(new Map());
  }, []);

  return {
    startTracking,
    stopTracking,
    stopAllTracking,
    setNotebookId,
    setOnAnyFileComplete
  };
};