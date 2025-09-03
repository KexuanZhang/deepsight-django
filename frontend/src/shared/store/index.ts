/**
 * Optimized Redux store - Only for global UI state
 * Server state is managed by TanStack Query
 */

import { configureStore, combineReducers } from '@reduxjs/toolkit';
import { persistStore, persistReducer } from 'redux-persist';
import storage from "redux-persist/lib/storage";
import uiReducer from './slices/uiSlice';

// Persist configuration for UI state
const uiPersistConfig = {
  key: 'ui',
  storage,
  whitelist: ['theme', 'sidebarCollapsed', 'features'], // Only persist these UI preferences
};

// Root reducer - minimal, focused on UI state only
const rootReducer = combineReducers({
  ui: persistReducer(uiPersistConfig, uiReducer),
});

// Store configuration
export const store = configureStore({
  reducer: rootReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [
          'persist/PERSIST',
          'persist/REHYDRATE',
          'persist/PAUSE',
          'persist/PURGE',
          'persist/REGISTER',
          'ui/openDeleteConfirmation', // This action contains a function
        ],
        ignoredPaths: ['ui.modals.deleteConfirmation.onConfirm'],
      },
    }),
  devTools: import.meta.env.DEV,
});

export const persistor = persistStore(store);

// Types
export type RootState = ReturnType<typeof rootReducer>;
export type AppDispatch = typeof store.dispatch;

// Typed hooks for use throughout app
import { useDispatch, useSelector } from 'react-redux';
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector = <T>(selector: (state: RootState) => T): T =>
  useSelector(selector);

// Store setup function for testing
export const setupStore = (preloadedState?: Partial<RootState>) => {
  return configureStore({
    reducer: rootReducer,
    preloadedState: preloadedState || undefined,
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: false, // Disable in tests
      }),
  });
};

export type AppStore = ReturnType<typeof setupStore>;