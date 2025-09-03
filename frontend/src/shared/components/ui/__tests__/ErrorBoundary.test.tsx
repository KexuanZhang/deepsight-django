/**
 * @vitest-environment jsdom
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { ErrorBoundary } from '../ErrorBoundary';

const ThrowError = ({ shouldThrow = false }: { shouldThrow?: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>No error</div>;
};

const mockOnError = vi.fn();

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary level="component">
        <div>Test content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('renders error UI when child component throws', () => {
    render(
      <ErrorBoundary level="component">
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Error occurred')).toBeInTheDocument();
    expect(screen.getByText('Test error message')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('calls onError prop when error occurs', () => {
    render(
      <ErrorBoundary level="component" onError={mockOnError}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(mockOnError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String),
      })
    );
  });

  it('renders different UI based on level prop', () => {
    const { rerender } = render(
      <ErrorBoundary level="page">
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    rerender(
      <ErrorBoundary level="section">
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Error occurred')).toBeInTheDocument();
  });

  it('resets error state when retry button is clicked', async () => {
    const user = userEvent.setup();
    
    const { rerender } = render(
      <ErrorBoundary level="component">
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Error occurred')).toBeInTheDocument();

    const retryButton = screen.getByRole('button', { name: /try again/i });
    await user.click(retryButton);

    // Re-render with no error
    rerender(
      <ErrorBoundary level="component">
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText('No error')).toBeInTheDocument();
    expect(screen.queryByText('Error occurred')).not.toBeInTheDocument();
  });

  it('shows developer information in development mode', () => {
    // Mock development environment
    vi.stubEnv('DEV', true);

    render(
      <ErrorBoundary level="component">
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Developer Information')).toBeInTheDocument();
  });

  it('uses custom fallback component when provided', () => {
    const CustomFallback = ({ error, retry }: any) => (
      <div>
        <span>Custom error: {error.message}</span>
        <button onClick={retry}>Custom retry</button>
      </div>
    );

    render(
      <ErrorBoundary level="component" fallback={CustomFallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom error: Test error message')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /custom retry/i })).toBeInTheDocument();
  });

  it('handles multiple consecutive errors', () => {
    const { rerender } = render(
      <ErrorBoundary level="component">
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Test error message')).toBeInTheDocument();

    // Simulate another error
    rerender(
      <ErrorBoundary level="component">
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Test error message')).toBeInTheDocument();
    expect(mockOnError).toHaveBeenCalledTimes(1); // Should be called for each mount
  });

  it('provides correct styling classes for different levels', () => {
    const { rerender, container } = render(
      <ErrorBoundary level="page">
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(container.querySelector('.min-h-screen')).toBeInTheDocument();

    rerender(
      <ErrorBoundary level="section">
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(container.querySelector('.py-16')).toBeInTheDocument();

    rerender(
      <ErrorBoundary level="component">
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(container.querySelector('.p-6')).toBeInTheDocument();
  });
});