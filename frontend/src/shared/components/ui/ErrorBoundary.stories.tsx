import type { Meta, StoryObj } from '@storybook/react';
import { ErrorBoundary, ErrorFallbackProps } from './ErrorBoundary';

const ThrowError = ({ shouldThrow = false }: { shouldThrow?: boolean }) => {
  if (shouldThrow) {
    throw new Error('This is a test error for Storybook demonstration');
  }
  return <div className="p-4 bg-green-100 rounded">Component rendered successfully!</div>;
};

const CustomErrorFallback = ({ error, retry }: ErrorFallbackProps) => (
  <div className="p-6 bg-red-50 border-l-4 border-red-500 rounded">
    <h3 className="text-lg font-semibold text-red-800 mb-2">Custom Error Handler</h3>
    <p className="text-red-700 mb-4">{error.message}</p>
    <button
      onClick={retry}
      className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
    >
      Retry with Custom Handler
    </button>
  </div>
);

const meta: Meta<typeof ErrorBoundary> = {
  title: 'Components/ErrorBoundary',
  component: ErrorBoundary,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: `
The ErrorBoundary component provides comprehensive error handling for React components.
It catches JavaScript errors anywhere in the child component tree, logs them, and displays a fallback UI.

## Features
- **Multiple Error Levels**: Component, section, and page-level error boundaries
- **Custom Fallback Components**: Support for custom error UI
- **Developer Information**: Shows detailed error info in development mode
- **Error Recovery**: Retry functionality to recover from errors
- **Error Reporting**: Optional callback for error logging/monitoring

## Usage
Wrap components that might throw errors to provide graceful error handling and better user experience.
        `,
      },
    },
  },
  argTypes: {
    level: {
      control: 'select',
      options: ['component', 'section', 'page'],
      description: 'The scope level of the error boundary',
    },
    fallback: {
      control: false,
      description: 'Custom fallback component to render when an error occurs',
    },
    onError: {
      action: 'error-occurred',
      description: 'Callback function called when an error occurs',
    },
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    level: 'component',
  },
  render: (args) => (
    <ErrorBoundary {...args}>
      <ThrowError shouldThrow={false} />
    </ErrorBoundary>
  ),
};

export const ComponentLevel: Story = {
  args: {
    level: 'component',
  },
  render: (args) => (
    <ErrorBoundary {...args}>
      <ThrowError shouldThrow={true} />
    </ErrorBoundary>
  ),
};

export const SectionLevel: Story = {
  args: {
    level: 'section',
  },
  render: (args) => (
    <ErrorBoundary {...args}>
      <ThrowError shouldThrow={true} />
    </ErrorBoundary>
  ),
};

export const PageLevel: Story = {
  args: {
    level: 'page',
  },
  render: (args) => (
    <ErrorBoundary {...args}>
      <ThrowError shouldThrow={true} />
    </ErrorBoundary>
  ),
};

export const CustomFallback: Story = {
  args: {
    level: 'component',
    fallback: CustomErrorFallback,
  },
  render: (args) => (
    <ErrorBoundary {...args}>
      <ThrowError shouldThrow={true} />
    </ErrorBoundary>
  ),
};

export const WithErrorCallback: Story = {
  args: {
    level: 'component',
    onError: (error: Error, errorInfo: React.ErrorInfo) => {
      console.log('Error caught by boundary:', error);
      console.log('Error info:', errorInfo);
    },
  },
  render: (args) => (
    <ErrorBoundary {...args}>
      <ThrowError shouldThrow={true} />
    </ErrorBoundary>
  ),
};

export const NestedErrorBoundaries: Story = {
  render: () => (
    <ErrorBoundary level="page">
      <div className="p-6 space-y-4">
        <h2 className="text-xl font-semibold">Page with nested error boundaries</h2>
        
        <ErrorBoundary level="section">
          <div className="p-4 bg-blue-50 rounded">
            <h3 className="font-medium mb-2">Section 1 - Working</h3>
            <ThrowError shouldThrow={false} />
          </div>
        </ErrorBoundary>

        <ErrorBoundary level="section">
          <div className="p-4 bg-red-50 rounded">
            <h3 className="font-medium mb-2">Section 2 - With Error</h3>
            <ThrowError shouldThrow={true} />
          </div>
        </ErrorBoundary>

        <ErrorBoundary level="section">
          <div className="p-4 bg-green-50 rounded">
            <h3 className="font-medium mb-2">Section 3 - Working</h3>
            <ThrowError shouldThrow={false} />
          </div>
        </ErrorBoundary>
      </div>
    </ErrorBoundary>
  ),
};

export const DevelopmentMode: Story = {
  parameters: {
    docs: {
      description: {
        story: 'In development mode, the ErrorBoundary shows additional debugging information including error stack traces and component stack traces.',
      },
    },
  },
  args: {
    level: 'component',
  },
  render: (args) => (
    <ErrorBoundary {...args}>
      <ThrowError shouldThrow={true} />
    </ErrorBoundary>
  ),
};