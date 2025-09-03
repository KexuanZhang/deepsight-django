/**
 * Optimized UI slice - Only for global UI state
 * Server state is handled by TanStack Query
 */

import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { ThemeMode, Toast } from "@/shared/types/global";

interface UiState {
  // Theme and appearance
  theme: ThemeMode;
  sidebarCollapsed: boolean;
  
  // Global UI state
  notifications: Toast[];
  
  // Modal state - only for global modals
  modals: {
    createNotebook: boolean;
    deleteConfirmation: {
      isOpen: boolean;
      title?: string;
      message?: string;
      onConfirm?: () => void;
    };
    globalSearch: boolean;
  };
  
  // Loading states for global operations
  globalLoading: {
    isInitializing: boolean;
    isSyncing: boolean;
  };
  
  // Feature flags (client-side)
  features: {
    enableBetaFeatures: boolean;
    enableAdvancedSearch: boolean;
    enableOfflineMode: boolean;
  };
}

const initialState: UiState = {
  theme: 'system',
  sidebarCollapsed: false,
  
  notifications: [],
  
  modals: {
    createNotebook: false,
    deleteConfirmation: {
      isOpen: false,
    },
    globalSearch: false,
  },
  
  globalLoading: {
    isInitializing: false,
    isSyncing: false,
  },
  
  features: {
    enableBetaFeatures: false,
    enableAdvancedSearch: true,
    enableOfflineMode: false,
  },
};

export const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    // Theme actions
    setTheme: (state, action: PayloadAction<ThemeMode>) => {
      state.theme = action.payload;
    },
    
    toggleTheme: (state) => {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
    },
    
    // Sidebar actions
    toggleSidebar: (state) => {
      state.sidebarCollapsed = !state.sidebarCollapsed;
    },
    
    setSidebarCollapsed: (state, action: PayloadAction<boolean>) => {
      state.sidebarCollapsed = action.payload;
    },
    
    // Notification actions
    addNotification: (state, action: PayloadAction<Omit<Toast, 'id'>>) => {
      const notification: Toast = {
        ...action.payload,
        id: Date.now().toString(),
      };
      state.notifications.push(notification);
    },
    
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(
        (notification) => notification.id !== action.payload
      );
    },
    
    clearAllNotifications: (state) => {
      state.notifications = [];
    },
    
    // Modal actions
    openModal: (state, action: PayloadAction<keyof UiState['modals']>) => {
      const modalKey = action.payload;
      if (modalKey === 'deleteConfirmation') {
        // Handle delete confirmation separately as it has a complex structure
        return;
      }
      (state.modals[modalKey] as boolean) = true;
    },
    
    closeModal: (state, action: PayloadAction<keyof UiState['modals']>) => {
      const modalKey = action.payload;
      if (modalKey === 'deleteConfirmation') {
        state.modals.deleteConfirmation = { isOpen: false };
        return;
      }
      (state.modals[modalKey] as boolean) = false;
    },
    
    openDeleteConfirmation: (
      state,
      action: PayloadAction<{
        title: string;
        message: string;
        onConfirm: () => void;
      }>
    ) => {
      state.modals.deleteConfirmation = {
        isOpen: true,
        ...action.payload,
      };
    },
    
    closeDeleteConfirmation: (state) => {
      state.modals.deleteConfirmation = { isOpen: false };
    },
    
    // Global loading actions
    setGlobalLoading: (
      state,
      action: PayloadAction<{ key: keyof UiState['globalLoading']; loading: boolean }>
    ) => {
      const { key, loading } = action.payload;
      state.globalLoading[key] = loading;
    },
    
    // Feature flag actions
    toggleFeature: (
      state,
      action: PayloadAction<keyof UiState['features']>
    ) => {
      const feature = action.payload;
      state.features[feature] = !state.features[feature];
    },
    
    setFeature: (
      state,
      action: PayloadAction<{
        feature: keyof UiState['features'];
        enabled: boolean;
      }>
    ) => {
      const { feature, enabled } = action.payload;
      state.features[feature] = enabled;
    },
  },
});

export const {
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
} = uiSlice.actions;

export default uiSlice.reducer;

// Selectors
export const selectTheme = (state: { ui: UiState }) => state.ui.theme;
export const selectSidebarCollapsed = (state: { ui: UiState }) => state.ui.sidebarCollapsed;
export const selectNotifications = (state: { ui: UiState }) => state.ui.notifications;
export const selectModals = (state: { ui: UiState }) => state.ui.modals;
export const selectGlobalLoading = (state: { ui: UiState }) => state.ui.globalLoading;
export const selectFeatures = (state: { ui: UiState }) => state.ui.features;