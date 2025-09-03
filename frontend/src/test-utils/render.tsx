/**
 * Custom render utility for testing with providers
 */

import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { configureStore } from '@reduxjs/toolkit';
import { createTestQueryClient } from "@/shared/queries/client";
// import { rootReducer, type RootState } from '@/app/rootReducer';

// Temporary minimal store for testing - replace when rootReducer is available
const mockReducer = (state = {}, action: any) => state;
type RootState = any; // Replace with actual RootState type when available

// This type interface extends the default options for render from RTL,
// as well as allows the user to specify other things such as initialState,
// store, and queryClient.
interface ExtendedRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  preloadedState?: any; // Replace with PreloadedState<RootState> when available
  store?: ReturnType<typeof configureStore>;
  queryClient?: QueryClient;
  routerProps?: {
    initialEntries?: string[];
    initialIndex?: number;
  };
}

export function renderWithProviders(
  ui: ReactElement,
  {
    preloadedState = {},
    // Automatically create a store instance if no store was passed in
    store = configureStore({
      reducer: mockReducer, // Replace with rootReducer when available
      preloadedState,
    }),
    queryClient = createTestQueryClient(),
    routerProps = {},
    ...renderOptions
  }: ExtendedRenderOptions = {}
) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter {...routerProps}>
            {children}
          </BrowserRouter>
        </QueryClientProvider>
      </Provider>
    );
  }

  // Return an object with the store and all of RTL's query functions
  return {
    store,
    queryClient,
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  };
}

// Mock utilities for testing
export const createMockNotebook = (overrides = {}) => ({
  id: 'test-notebook-1',
  name: 'Test Notebook',
  description: 'A test notebook',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
  sourceCount: 5,
  itemCount: 10,
  isProcessing: false,
  ...overrides,
});

export const createMockNotebooks = (count: number = 3) => {
  return Array.from({ length: count }, (_, index) =>
    createMockNotebook({
      id: `test-notebook-${index + 1}`,
      name: `Test Notebook ${index + 1}`,
      description: `Test notebook description ${index + 1}`,
    })
  );
};

export const createMockSource = (overrides = {}) => ({
  id: 'test-source-1',
  name: 'Test Source',
  sourceType: 'file' as const,
  status: 'completed' as const,
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
  metadata: {},
  ...overrides,
});

export const createMockSources = (count: number = 3) => {
  return Array.from({ length: count }, (_, index) =>
    createMockSource({
      id: `test-source-${index + 1}`,
      name: `Test Source ${index + 1}`,
    })
  );
};

export const createMockApiResponse = <T,>(data: T, meta = {}) => ({
  data,
  meta: {
    pagination: {
      count: Array.isArray(data) ? data.length : 1,
      page: 1,
      pages: 1,
      pageSize: 20,
      hasNext: false,
      hasPrevious: false,
    },
    ...meta,
  },
});

// Re-export everything
export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';