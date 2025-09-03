/**
 * Custom Jest/Vitest matchers for enhanced testing
 */

import { expect, vi } from 'vitest';

// Extend expect interface
declare module 'vitest' {
  interface Assertion<T = any> {
    toBeLoading(): T;
    toHaveError(expectedError?: string): T;
    toBeVisible(): T;
    toHaveBeenCalledWithApiEndpoint(endpoint: string): T;
    toMatchNotebookStructure(): T;
    toMatchSourceStructure(): T;
  }

  interface AsymmetricMatchersContaining {
    toBeLoading(): any;
    toHaveError(expectedError?: string): any;
    toBeVisible(): any;
    toHaveBeenCalledWithApiEndpoint(endpoint: string): any;
    toMatchNotebookStructure(): any;
    toMatchSourceStructure(): any;
  }
}

// Custom matchers
expect.extend({
  toBeLoading(received) {
    const pass = received && (
      received.loading === true ||
      received.isLoading === true ||
      received.status === 'loading' ||
      received.state === 'loading'
    );

    if (pass) {
      return {
        message: () => `expected ${received} not to be loading`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be loading`,
        pass: false,
      };
    }
  },

  toHaveError(received, expectedError) {
    const hasError = received && (
      received.error !== null ||
      received.hasError === true ||
      received.status === 'error' ||
      received.state === 'error'
    );

    const errorMatches = expectedError ? 
      (received.error && received.error.includes(expectedError)) ||
      (received.message && received.message.includes(expectedError)) :
      true;

    const pass = hasError && errorMatches;

    if (pass) {
      return {
        message: () => expectedError ? 
          `expected ${received} not to have error "${expectedError}"` :
          `expected ${received} not to have any error`,
        pass: true,
      };
    } else {
      return {
        message: () => expectedError ? 
          `expected ${received} to have error "${expectedError}"` :
          `expected ${received} to have an error`,
        pass: false,
      };
    }
  },

  toBeVisible(received) {
    // For DOM elements
    if (received && received.style) {
      const pass = received.style.display !== 'none' && 
                   received.style.visibility !== 'hidden' &&
                   received.style.opacity !== '0';
      
      return {
        message: () => pass ? 
          `expected element not to be visible` :
          `expected element to be visible`,
        pass,
      };
    }

    // For React Testing Library queries
    if (received && typeof received.isVisible === 'function') {
      const pass = received.isVisible();
      return {
        message: () => pass ?
          `expected element not to be visible` :
          `expected element to be visible`,
        pass,
      };
    }

    return {
      message: () => `expected element to be visible but could not determine visibility`,
      pass: false,
    };
  },

  toHaveBeenCalledWithApiEndpoint(received, endpoint) {
    if (!received || typeof received.mock === 'undefined') {
      return {
        message: () => `expected ${received} to be a mock function`,
        pass: false,
      };
    }

    const calls = received.mock.calls;
    const pass = calls.some((call: any[]) => 
      call.some((arg: any) => 
        typeof arg === 'string' && arg.includes(endpoint)
      )
    );

    return {
      message: () => pass ?
        `expected mock not to have been called with API endpoint "${endpoint}"` :
        `expected mock to have been called with API endpoint "${endpoint}"`,
      pass,
    };
  },

  toMatchNotebookStructure(received) {
    const requiredFields = ['id', 'name', 'created_at'];
    const optionalFields = ['description', 'updated_at', 'sources'];
    
    const hasRequiredFields = requiredFields.every(field => 
      received && typeof received[field] !== 'undefined'
    );

    const pass = hasRequiredFields && typeof received === 'object';

    return {
      message: () => pass ?
        `expected object not to match notebook structure` :
        `expected object to match notebook structure (requires: ${requiredFields.join(', ')})`,
      pass,
    };
  },

  toMatchSourceStructure(received) {
    const requiredFields = ['id', 'notebook_id', 'filename'];
    const optionalFields = ['ext', 'size', 'metadata', 'selected', 'created_at'];
    
    const hasRequiredFields = requiredFields.every(field => 
      received && typeof received[field] !== 'undefined'
    );

    const pass = hasRequiredFields && typeof received === 'object';

    return {
      message: () => pass ?
        `expected object not to match source structure` :
        `expected object to match source structure (requires: ${requiredFields.join(', ')})`,
      pass,
    };
  },
});

// Helper functions for common test patterns
export const waitForLoadingToFinish = async () => {
  const { waitFor } = await import('@testing-library/react');
  await waitFor(() => {
    const loadingElements = document.querySelectorAll('[data-loading="true"], .loading, [aria-busy="true"]');
    expect(loadingElements).toHaveLength(0);
  });
};

export const expectLoadingState = (element: any) => {
  expect(element).toBeLoading();
};

export const expectErrorState = (element: any, error?: string) => {
  expect(element).toHaveError(error);
};

export const mockConsoleError = () => {
  const originalError = console.error;
  const mockError = vi.fn();
  console.error = mockError;
  
  return {
    mockError,
    restore: () => {
      console.error = originalError;
    },
  };
};

export const mockConsoleWarn = () => {
  const originalWarn = console.warn;
  const mockWarn = vi.fn();
  console.warn = mockWarn;
  
  return {
    mockWarn,
    restore: () => {
      console.warn = originalWarn;
    },
  };
};