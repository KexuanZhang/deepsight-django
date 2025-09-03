/**
 * Notebook-scoped context for feature-specific state management
 * Separates local notebook state from global application state
 */

import React, { createContext, useContext, useState, useMemo, useCallback } from 'react';
import { useNotebook, useNotebookStats } from "@/shared/queries/notebooks";
import type { ViewMode, SortConfig } from "@/shared/types/global";

interface NotebookContextValue {
  // Core notebook data (from server state)
  notebookId: string;
  notebook?: any; // Replace with actual Notebook type
  stats?: any; // Replace with actual NotebookStats type
  
  // Local UI state (client state)
  selectedSources: string[];
  setSelectedSources: (sources: string[] | ((prev: string[]) => string[])) => void;
  
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  
  sortConfig: SortConfig;
  setSortConfig: (config: SortConfig) => void;
  
  // UI state
  activePanel: 'chat' | 'sources' | 'studio' | 'knowledge';
  setActivePanel: (panel: 'chat' | 'sources' | 'studio' | 'knowledge') => void;
  
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  
  // Selection state
  isMultiSelectMode: boolean;
  toggleMultiSelectMode: () => void;
  clearSelection: () => void;
  toggleSourceSelection: (sourceId: string) => void;
  selectAllSources: () => void;
  
  // Actions
  refreshNotebook: () => void;
  
  // Loading and error states
  isLoading: boolean;
  error: Error | null;
}

const NotebookContext = createContext<NotebookContextValue | undefined>(undefined);

interface NotebookProviderProps {
  notebookId: string;
  children: React.ReactNode;
}

export const NotebookProvider: React.FC<NotebookProviderProps> = ({
  notebookId,
  children,
}) => {
  // Server state (managed by TanStack Query)
  const {
    data: notebook,
    isLoading: isNotebookLoading,
    error: notebookError,
    refetch: refetchNotebook,
  } = useNotebook(notebookId);

  const {
    data: stats,
    isLoading: isStatsLoading,
    error: statsError,
  } = useNotebookStats(notebookId);

  // Client state (local to this feature)
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: 'updatedAt',
    order: 'desc',
  });
  const [activePanel, setActivePanel] = useState<'chat' | 'sources' | 'studio' | 'knowledge'>('chat');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMultiSelectMode, setIsMultiSelectMode] = useState(false);

  // Derived state
  const isLoading = isNotebookLoading || isStatsLoading;
  const error = notebookError || statsError;

  // Actions
  const toggleMultiSelectMode = useCallback(() => {
    setIsMultiSelectMode((prev) => !prev);
    if (isMultiSelectMode) {
      setSelectedSources([]);
    }
  }, [isMultiSelectMode]);

  const clearSelection = useCallback(() => {
    setSelectedSources([]);
    setIsMultiSelectMode(false);
  }, []);

  const toggleSourceSelection = useCallback((sourceId: string) => {
    setSelectedSources((prev) => {
      if (prev.includes(sourceId)) {
        return prev.filter((id) => id !== sourceId);
      }
      return [...prev, sourceId];
    });
  }, []);

  const selectAllSources = useCallback(() => {
    // This would need to be implemented based on available sources
    // For now, just a placeholder
    console.log('Select all sources not implemented yet');
  }, []);

  const refreshNotebook = useCallback(() => {
    refetchNotebook();
  }, [refetchNotebook]);

  // Memoized context value
  const contextValue = useMemo(
    (): NotebookContextValue => ({
      // Server state
      notebookId,
      notebook,
      stats,
      
      // Client state
      selectedSources,
      setSelectedSources,
      viewMode,
      setViewMode,
      searchQuery,
      setSearchQuery,
      sortConfig,
      setSortConfig,
      activePanel,
      setActivePanel,
      sidebarOpen,
      setSidebarOpen,
      
      // Selection state
      isMultiSelectMode,
      toggleMultiSelectMode,
      clearSelection,
      toggleSourceSelection,
      selectAllSources,
      
      // Actions
      refreshNotebook,
      
      // Loading and error states
      isLoading,
      error,
    }),
    [
      notebookId,
      notebook,
      stats,
      selectedSources,
      viewMode,
      searchQuery,
      sortConfig,
      activePanel,
      sidebarOpen,
      isMultiSelectMode,
      toggleMultiSelectMode,
      clearSelection,
      toggleSourceSelection,
      selectAllSources,
      refreshNotebook,
      isLoading,
      error,
    ]
  );

  return (
    <NotebookContext.Provider value={contextValue}>
      {children}
    </NotebookContext.Provider>
  );
};

// Custom hook to use notebook context
export const useNotebookContext = (): NotebookContextValue => {
  const context = useContext(NotebookContext);
  if (context === undefined) {
    throw new Error('useNotebookContext must be used within a NotebookProvider');
  }
  return context;
};

// Convenience hooks for specific parts of the context
export const useNotebookSelection = () => {
  const {
    selectedSources,
    setSelectedSources,
    isMultiSelectMode,
    toggleMultiSelectMode,
    clearSelection,
    toggleSourceSelection,
    selectAllSources,
  } = useNotebookContext();

  return {
    selectedSources,
    setSelectedSources,
    isMultiSelectMode,
    toggleMultiSelectMode,
    clearSelection,
    toggleSourceSelection,
    selectAllSources,
  };
};

export const useNotebookView = () => {
  const {
    viewMode,
    setViewMode,
    searchQuery,
    setSearchQuery,
    sortConfig,
    setSortConfig,
    activePanel,
    setActivePanel,
    sidebarOpen,
    setSidebarOpen,
  } = useNotebookContext();

  return {
    viewMode,
    setViewMode,
    searchQuery,
    setSearchQuery,
    sortConfig,
    setSortConfig,
    activePanel,
    setActivePanel,
    sidebarOpen,
    setSidebarOpen,
  };
};

export const useNotebookData = () => {
  const {
    notebookId,
    notebook,
    stats,
    isLoading,
    error,
    refreshNotebook,
  } = useNotebookContext();

  return {
    notebookId,
    notebook,
    stats,
    isLoading,
    error,
    refreshNotebook,
  };
};