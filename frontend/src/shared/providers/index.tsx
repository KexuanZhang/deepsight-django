/**
 * Combined providers for the application with optimized state management
 */

import React from 'react';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { store, persistor } from '../store';
import { QueryProvider } from './QueryProvider';
import { LoadingSpinner } from "@/shared/components/ui/LoadingSpinner";

interface AppProvidersProps {
  children: React.ReactNode;
}

export const AppProviders: React.FC<AppProvidersProps> = ({ children }) => {
  return (
    <Provider store={store}>
      <PersistGate 
        loading={
          <div className="min-h-screen flex items-center justify-center">
            <LoadingSpinner size="xl" />
          </div>
        } 
        persistor={persistor}
      >
        <QueryProvider>
          {children}
        </QueryProvider>
      </PersistGate>
    </Provider>
  );
};

// Individual provider exports
export { QueryProvider } from './QueryProvider';
export { NotebookProvider, useNotebookContext } from "@/features/notebook/contexts/NotebookContext";