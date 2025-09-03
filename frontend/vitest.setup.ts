/**
 * Vitest global setup and configuration
 */

import '@testing-library/jest-dom';
import { beforeAll, afterEach, afterAll, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import { server } from './src/test-utils/test-server';
import './src/test-utils/custom-matchers';

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock requestIdleCallback
global.requestIdleCallback = vi.fn((cb) => setTimeout(cb, 0));
global.cancelIdleCallback = vi.fn();

// Mock crypto.randomUUID
Object.defineProperty(global.crypto, 'randomUUID', {
  value: vi.fn(() => 'mocked-uuid-' + Math.random().toString(36).substring(2)),
});

// Mock performance.now
Object.defineProperty(performance, 'now', {
  value: vi.fn(() => Date.now()),
});

// Mock performance.mark and performance.measure
Object.defineProperty(performance, 'mark', {
  value: vi.fn(),
});

Object.defineProperty(performance, 'measure', {
  value: vi.fn(),
});

// Mock PerformanceObserver
global.PerformanceObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock fetch if not available
if (!global.fetch) {
  global.fetch = vi.fn();
}

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
global.localStorage = localStorageMock;

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
global.sessionStorage = sessionStorageMock;

// Mock console methods in test environment
const originalConsole = { ...console };
global.console = {
  ...originalConsole,
  error: vi.fn(originalConsole.error),
  warn: vi.fn(originalConsole.warn),
  info: vi.fn(originalConsole.info),
  debug: vi.fn(originalConsole.debug),
};

// Setup MSW server
beforeAll(() => {
  server.listen({
    onUnhandledRequest: 'error',
  });
});

// Cleanup after each test
afterEach(() => {
  cleanup();
  server.resetHandlers();
  vi.clearAllMocks();
  
  // Clear localStorage and sessionStorage
  localStorageMock.clear();
  sessionStorageMock.clear();
});

// Clean up after all tests
afterAll(() => {
  server.close();
});

// Enhanced error handling for tests
process.on('unhandledRejection', (reason) => {
  console.error('Unhandled Rejection in tests:', reason);
});

// Global test utilities
global.testUtils = {
  server,
  mockLocalStorage: localStorageMock,
  mockSessionStorage: sessionStorageMock,
};