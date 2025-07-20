import { useState, useEffect, useCallback, useRef } from 'react';

interface FileReference {
  file_id?: string;
  file?: string;
  [key: string]: any;
}

interface SourcesListRef {
  current: {
    getSelectedFiles?: () => FileReference[];
    getSelectedSources?: () => any[];
  } | null;
}

export const useFileSelection = (sourcesListRef: SourcesListRef) => {
  const [selectedFiles, setSelectedFiles] = useState<FileReference[]>([]);
  const [selectedSources, setSelectedSources] = useState<any[]>([]);
  const hasFilesRef = useRef(false);

  const updateSelectedFiles = useCallback(() => {
    if (sourcesListRef?.current) {
      const newSelectedFiles = sourcesListRef.current.getSelectedFiles?.() || [];
      const newSelectedSources = sourcesListRef.current.getSelectedSources?.() || [];
      
      setSelectedFiles(newSelectedFiles);
      setSelectedSources(newSelectedSources);
      hasFilesRef.current = newSelectedFiles.length > 0;
    }
  }, [sourcesListRef]);

  const hasSelectedFiles = useCallback(() => {
    return hasFilesRef.current;
  }, []);

  const getCurrentSelectedFiles = useCallback(() => {
    return sourcesListRef?.current?.getSelectedFiles?.() || [];
  }, [sourcesListRef]);

  // Optimized polling for file selection changes with mutation observer fallback
  useEffect(() => {
    if (!sourcesListRef?.current) {
      console.debug('sourcesListRef not available, skipping file selection monitoring');
      return;
    }

    let lastSelectedIds = '';
    let observer: MutationObserver | undefined;
    
    const checkForChanges = () => {
      try {
        // Additional null check inside the function
        if (!sourcesListRef?.current?.getSelectedFiles) {
          return;
        }
        
        const currentFiles = sourcesListRef.current.getSelectedFiles() || [];
        const currentIds = currentFiles.map((f: FileReference) => f.file_id || f.file).join(',');
        
        if (currentIds !== lastSelectedIds) {
          lastSelectedIds = currentIds;
          updateSelectedFiles();
        }
      } catch (error) {
        console.warn('Error checking file selection changes:', error);
      }
    };

    // Initial check
    checkForChanges();

    // Try to observe DOM changes for immediate updates
    if (typeof MutationObserver !== 'undefined' && sourcesListRef?.current) {
      observer = new MutationObserver(() => {
        checkForChanges();
      });
      
      try {
        // Double-check the ref is still valid
        if (sourcesListRef.current && sourcesListRef.current instanceof Node) {
          observer.observe(sourcesListRef.current, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['class', 'data-selected']
          });
        }
      } catch (error) {
        console.warn('Could not set up MutationObserver:', error);
      }
    }

    // Fallback polling for browsers without MutationObserver or as backup
    const interval = setInterval(checkForChanges, 150);
    
    return () => {
      clearInterval(interval);
      if (observer) {
        observer.disconnect();
      }
    };
  }, [sourcesListRef, updateSelectedFiles]);

  return {
    selectedFiles,
    selectedSources,
    hasSelectedFiles,
    getCurrentSelectedFiles,
    updateSelectedFiles
  };
};