/**
 * Notebook Detail Page - Example of modern state management patterns
 * Demonstrates server state, client state, and React 18 concurrent features
 */

import React, { Suspense } from 'react';
import { useNotebookContext } from '../contexts/NotebookContext';
import { useParams } from 'react-router-dom';
import { ErrorBoundary } from "@/shared/components/ui/ErrorBoundary";
import { NotebookProvider } from '../contexts/NotebookContext';
import { PageLoading } from "@/shared/components/ui/LoadingSpinner";

// Lazy load components for better performance
const NotebookHeader = React.lazy(() => 
  import('../components/layout/NotebookHeader')
);

const NotebookLayout = React.lazy(() => 
  import('../components/layout/NotebookLayout')
);

const ChatPanel = React.lazy(() => 
  import('../components/panels/ChatPanel')
);

const SourcesPanel = React.lazy(() => 
  import('../components/panels/SourcesPanel')
);

const StudioPanel = React.lazy(() => 
  import('../components/panels/StudioPanel')
);

interface NotebookDetailPageProps {
  className?: string;
}

export const NotebookDetailPage: React.FC<NotebookDetailPageProps> = ({ className }) => {
  const { notebookId } = useParams<{ notebookId: string }>();

  if (!notebookId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Notebook Not Found
          </h2>
          <p className="text-gray-600">
            The requested notebook could not be found.
          </p>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary level="page">
      {/* 
        NotebookProvider provides:
        1. Server state via TanStack Query (notebook data, stats)
        2. Client state via React Context (UI state, selections)
        3. Feature-scoped state management
      */}
      <NotebookProvider notebookId={notebookId}>
        <div className="min-h-screen bg-gray-50">
          <Suspense fallback={<PageLoading message="Loading notebook..." />}>
            <NotebookHeader onMenuToggle={() => console.log('Menu toggled')} />
            
            <NotebookPanels />
          </Suspense>
        </div>
      </NotebookProvider>
    </ErrorBoundary>
  );
};

// Separate component for panels to optimize suspense boundaries
const NotebookPanels: React.FC = () => {
  const { notebookId } = useNotebookContext();
  const sourcesListRef = React.useRef(null);
  
  const handleSelectionChange = (selection: any) => {
    console.log('Selection changed:', selection);
  };
  
  const handleOpenModal = (modalType: string, data?: any) => {
    console.log('Open modal:', modalType, data);
  };
  
  const handleCloseModal = (modalType: string) => {
    console.log('Close modal:', modalType);
  };
  
  return (
    <ErrorBoundary level="section">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
        {/* Chat Panel - Primary interaction */}
        <div className="lg:col-span-2">
          <Suspense fallback={<div className="h-96 bg-white rounded-lg animate-pulse" />}>
            <ChatPanel 
              notebookId={notebookId} 
              sourcesListRef={sourcesListRef}
              onSelectionChange={handleSelectionChange}
            />
          </Suspense>
        </div>
        
        {/* Side Panels */}
        <div className="space-y-6">
          <Suspense fallback={<div className="h-64 bg-white rounded-lg animate-pulse" />}>
            <SourcesPanel 
              notebookId={notebookId}
              onSelectionChange={() => handleSelectionChange({})}
              onOpenModal={handleOpenModal}
              onCloseModal={handleCloseModal}
            />
          </Suspense>
          
          <Suspense fallback={<div className="h-64 bg-white rounded-lg animate-pulse" />}>
            <StudioPanel 
              notebookId={notebookId}
              sourcesListRef={sourcesListRef}
              onSelectionChange={handleSelectionChange}
              onOpenModal={handleOpenModal}
              onCloseModal={handleCloseModal}
            />
          </Suspense>
        </div>
      </div>
    </ErrorBoundary>
  );
};