/**
 * Global UI hooks for managing application-wide UI state
 * Uses optimized Redux store for global state only
 */

import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '../store';
import {
  setTheme,
  toggleTheme,
  toggleSidebar,
  setSidebarCollapsed,
  addNotification,
  removeNotification,
  clearAllNotifications,
  openModal,
  closeModal,
  openDeleteConfirmation,
  closeDeleteConfirmation,
  setGlobalLoading,
  toggleFeature,
  setFeature,
  selectTheme,
  selectSidebarCollapsed,
  selectNotifications,
  selectModals,
  selectGlobalLoading,
  selectFeatures,
} from '../store/slices/uiSlice';
import type { ThemeMode, Toast } from "@/shared/types/global";

// Theme management
export const useTheme = () => {
  const dispatch = useAppDispatch();
  const theme = useAppSelector(selectTheme);

  const updateTheme = useCallback((newTheme: ThemeMode) => {
    dispatch(setTheme(newTheme));
    
    // Apply theme to document
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    
    if (newTheme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      root.classList.add(systemTheme);
    } else {
      root.classList.add(newTheme);
    }
  }, [dispatch]);

  const toggle = useCallback(() => {
    dispatch(toggleTheme());
  }, [dispatch]);

  return {
    theme,
    setTheme: updateTheme,
    toggleTheme: toggle,
  };
};

// Sidebar management
export const useSidebar = () => {
  const dispatch = useAppDispatch();
  const isCollapsed = useAppSelector(selectSidebarCollapsed);

  const toggle = useCallback(() => {
    dispatch(toggleSidebar());
  }, [dispatch]);

  const setCollapsed = useCallback((collapsed: boolean) => {
    dispatch(setSidebarCollapsed(collapsed));
  }, [dispatch]);

  return {
    isCollapsed,
    toggle,
    setCollapsed,
  };
};

// Notification management
export const useNotifications = () => {
  const dispatch = useAppDispatch();
  const notifications = useAppSelector(selectNotifications);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    dispatch(addNotification(toast));
    
    // Auto-remove after duration
    if (toast.duration !== 0) {
      setTimeout(() => {
        // Find the toast that was just added and remove it
        const addedToast = notifications[notifications.length - 1];
        if (addedToast) {
          dispatch(removeNotification(addedToast.id));
        }
      }, toast.duration || 5000);
    }
  }, [dispatch, notifications]);

  const removeToast = useCallback((id: string) => {
    dispatch(removeNotification(id));
  }, [dispatch]);

  const clearAll = useCallback(() => {
    dispatch(clearAllNotifications());
  }, [dispatch]);

  // Convenience methods for different toast types
  const showSuccess = useCallback((title: string, message?: string) => {
    addToast({ type: 'success', title, message });
  }, [addToast]);

  const showError = useCallback((title: string, message?: string) => {
    addToast({ type: 'error', title, message });
  }, [addToast]);

  const showWarning = useCallback((title: string, message?: string) => {
    addToast({ type: 'warning', title, message });
  }, [addToast]);

  const showInfo = useCallback((title: string, message?: string) => {
    addToast({ type: 'info', title, message });
  }, [addToast]);

  return {
    notifications,
    addToast,
    removeToast,
    clearAll,
    showSuccess,
    showError,
    showWarning,
    showInfo,
  };
};

// Modal management
export const useModals = () => {
  const dispatch = useAppDispatch();
  const modals = useAppSelector(selectModals);

  const openNotebookModal = useCallback(() => {
    dispatch(openModal('createNotebook'));
  }, [dispatch]);

  const closeNotebookModal = useCallback(() => {
    dispatch(closeModal('createNotebook'));
  }, [dispatch]);

  const openGlobalSearch = useCallback(() => {
    dispatch(openModal('globalSearch'));
  }, [dispatch]);

  const closeGlobalSearch = useCallback(() => {
    dispatch(closeModal('globalSearch'));
  }, [dispatch]);

  const openDelete = useCallback((
    title: string, 
    message: string, 
    onConfirm: () => void
  ) => {
    dispatch(openDeleteConfirmation({ title, message, onConfirm }));
  }, [dispatch]);

  const closeDelete = useCallback(() => {
    dispatch(closeDeleteConfirmation());
  }, [dispatch]);

  return {
    modals,
    notebook: {
      isOpen: modals.createNotebook,
      open: openNotebookModal,
      close: closeNotebookModal,
    },
    search: {
      isOpen: modals.globalSearch,
      open: openGlobalSearch,
      close: closeGlobalSearch,
    },
    delete: {
      isOpen: modals.deleteConfirmation.isOpen,
      title: modals.deleteConfirmation.title,
      message: modals.deleteConfirmation.message,
      open: openDelete,
      close: closeDelete,
    },
  };
};

// Global loading management
export const useGlobalLoading = () => {
  const dispatch = useAppDispatch();
  const loading = useAppSelector(selectGlobalLoading);

  const setInitializing = useCallback((isLoading: boolean) => {
    dispatch(setGlobalLoading({ key: 'isInitializing', loading: isLoading }));
  }, [dispatch]);

  const setSyncing = useCallback((isLoading: boolean) => {
    dispatch(setGlobalLoading({ key: 'isSyncing', loading: isLoading }));
  }, [dispatch]);

  return {
    ...loading,
    setInitializing,
    setSyncing,
  };
};

// Feature flag management
export const useFeatureFlags = () => {
  const dispatch = useAppDispatch();
  const features = useAppSelector(selectFeatures);

  const toggleBeta = useCallback(() => {
    dispatch(toggleFeature('enableBetaFeatures'));
  }, [dispatch]);

  const toggleAdvancedSearch = useCallback(() => {
    dispatch(toggleFeature('enableAdvancedSearch'));
  }, [dispatch]);

  const toggleOffline = useCallback(() => {
    dispatch(toggleFeature('enableOfflineMode'));
  }, [dispatch]);

  const setFeatureEnabled = useCallback((
    feature: keyof typeof features, 
    enabled: boolean
  ) => {
    dispatch(setFeature({ feature, enabled }));
  }, [dispatch, features]);

  return {
    features,
    toggleBeta,
    toggleAdvancedSearch,
    toggleOffline,
    setFeatureEnabled,
  };
};

// Combined hook for all global UI state
export const useGlobalUI = () => {
  const theme = useTheme();
  const sidebar = useSidebar();
  const notifications = useNotifications();
  const modals = useModals();
  const loading = useGlobalLoading();
  const featureFlags = useFeatureFlags();

  return {
    theme,
    sidebar,
    notifications,
    modals,
    loading,
    featureFlags,
  };
};