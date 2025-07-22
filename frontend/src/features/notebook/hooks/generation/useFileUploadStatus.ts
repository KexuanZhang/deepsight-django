import { useState, useCallback } from 'react';

export const useFileUploadStatus = () => {
  const [activeUploads, setActiveUploads] = useState<Set<string>>(new Set());

  const startTracking = useCallback((uploadFileId: string) => {
    console.log(`Starting simple upload tracking for: ${uploadFileId}`);
    setActiveUploads(prev => new Set(prev).add(uploadFileId));
  }, []);

  const stopTracking = useCallback((uploadFileId: string) => {
    console.log(`Stopping upload tracking for: ${uploadFileId}`);
    setActiveUploads(prev => {
      const newSet = new Set(prev);
      newSet.delete(uploadFileId);
      return newSet;
    });
  }, []);

  const stopAllTracking = useCallback(() => {
    console.log('Stopping all upload tracking');
    setActiveUploads(new Set());
  }, []);

  return {
    activeUploads: Array.from(activeUploads),
    startTracking,
    stopTracking,
    stopAllTracking,
    isTracking: (uploadFileId: string) => activeUploads.has(uploadFileId)
  };
};