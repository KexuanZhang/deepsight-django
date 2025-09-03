/**
 * Modern Notebook Grid Component using new architecture
 */

import React, { useMemo, useState, Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Grid, List } from 'lucide-react';
import { useNotebooks, useCreateNotebook } from "@/shared/queries/notebooks";
import { ErrorBoundary } from "@/shared/components/ui/ErrorBoundary";
import { LoadingSpinner, NotebookGridSkeleton } from "@/shared/components/ui/LoadingSpinner";
import { Button } from "@/shared/components/ui/button";
import { DataTable } from "@/shared/components/ui/DataTable";
import { useDeferredSearch, useSmartLoading } from "@/shared/hooks/useConcurrentFeatures";
import type { ColumnDef } from '@tanstack/react-table';
import type { Notebook } from "@/shared/api";
import { cn } from "@/shared/utils/utils";

interface NotebookGridProps {
  className?: string;
}

export const NotebookGrid: React.FC<NotebookGridProps> = ({ className }) => {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  
  // Use React 18 concurrent features for search
  const {
    query: searchQuery,
    deferredQuery,
    isPending: isSearchPending,
    updateQuery: handleSearchChange,
    clearQuery: clearSearch,
    isStale: isSearchStale,
  } = useDeferredSearch();

  // Queries with deferred search
  const {
    data: notebooksResponse,
    isLoading,
    error,
    refetch,
  } = useNotebooks({
    search: deferredQuery, // Use deferred query for server requests
    ordering: '-updated_at',
  });

  // Smart loading to prevent flickering
  const { shouldShowLoading } = useSmartLoading(isLoading, 300);

  const createNotebook = useCreateNotebook();

  // Memoized notebooks data
  const notebooks = useMemo(() => {
    if (!notebooksResponse) return [];
    return Array.isArray(notebooksResponse) ? notebooksResponse : (notebooksResponse as any)?.data || [];
  }, [notebooksResponse]);

  // Handle create notebook
  const handleCreateNotebook = async () => {
    try {
      const newNotebook = await createNotebook.mutateAsync({
        name: `Notebook ${new Date().toLocaleDateString()}`,
        description: 'New notebook',
      }) as Notebook;
      navigate(`/notebook/${newNotebook.id}`);
    } catch (error) {
      console.error('Failed to create notebook:', error);
    }
  };

  // Handle notebook click
  const handleNotebookClick = (notebook: Notebook) => {
    navigate(`/notebook/${notebook.id}`);
  };

  // Table columns definition
  const columns = useMemo<ColumnDef<Notebook>[]>(() => [
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span className="font-medium text-gray-900">{row.original.name}</span>
          {row.original.description && (
            <span className="text-sm text-gray-500 mt-1">
              {row.original.description}
            </span>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'sourceCount',
      header: 'Sources',
      cell: ({ row }) => (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          {row.original.sourceCount} sources
        </span>
      ),
    },
    {
      accessorKey: 'itemCount',
      header: 'Items',
      cell: ({ row }) => (
        <span className="text-sm text-gray-600">
          {row.original.itemCount} items
        </span>
      ),
    },
    {
      accessorKey: 'updatedAt',
      header: 'Last Updated',
      cell: ({ row }) => (
        <span className="text-sm text-gray-500">
          {new Date(row.original.updatedAt).toLocaleDateString()}
        </span>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <span
          className={cn(
            'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
            row.original.isProcessing
              ? 'bg-yellow-100 text-yellow-800'
              : 'bg-green-100 text-green-800'
          )}
        >
          {row.original.isProcessing ? 'Processing' : 'Ready'}
        </span>
      ),
    },
  ], []);

  // Grid view component
  const GridView: React.FC = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {notebooks.map((notebook: Notebook) => (
        <div
          key={notebook.id}
          className="group bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-all cursor-pointer"
          onClick={() => handleNotebookClick(notebook)}
        >
          <div className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-semibold text-gray-900 truncate group-hover:text-blue-600 transition-colors">
                  {notebook.name}
                </h3>
                {notebook.description && (
                  <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                    {notebook.description}
                  </p>
                )}
              </div>
              <div
                className={cn(
                  'ml-3 flex-shrink-0 w-2 h-2 rounded-full',
                  notebook.isProcessing ? 'bg-yellow-400' : 'bg-green-400'
                )}
              />
            </div>
            
            <div className="mt-4 flex items-center justify-between text-sm text-gray-500">
              <div className="flex items-center space-x-4">
                <span>{notebook.sourceCount} sources</span>
                <span>{notebook.itemCount} items</span>
              </div>
              <span>
                {new Date(notebook.updatedAt).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 mb-4">Failed to load notebooks</p>
        <Button onClick={() => refetch()} variant="outline">
          Try Again
        </Button>
      </div>
    );
  }

  return (
    <ErrorBoundary level="section">
      <div className={cn('space-y-6', className)}>
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Notebooks</h1>
            <p className="text-gray-600 mt-1">
              Manage your research notebooks and knowledge base
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <Button
              onClick={handleCreateNotebook}
              disabled={createNotebook.isPending}
              className="inline-flex items-center"
            >
              {createNotebook.isPending ? (
                <LoadingSpinner size="sm" color="white" className="mr-2" />
              ) : (
                <Plus className="w-4 h-4 mr-2" />
              )}
              New Notebook
            </Button>
          </div>
        </div>

        {/* Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="relative max-w-md w-full">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search notebooks..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className={cn(
                "w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all",
                isSearchStale && "bg-yellow-50 border-yellow-200"
              )}
            />
            {(isSearchPending || isSearchStale) && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                <LoadingSpinner size="sm" />
              </div>
            )}
          </div>

          <div className="flex items-center border border-gray-300 rounded-lg p-1">
            <Button
              variant={viewMode === 'grid' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('grid')}
              className="rounded-md"
            >
              <Grid className="w-4 h-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('list')}
              className="rounded-md"
            >
              <List className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Loading State with smart loading */}
        {shouldShowLoading && (
          <NotebookGridSkeleton count={8} />
        )}

        {/* Content */}
        {!shouldShowLoading && (
          <Suspense fallback={<NotebookGridSkeleton count={8} />}>
            {notebooks.length === 0 ? (
              <div className="text-center py-12">
                <div className="max-w-md mx-auto">
                  <div className="w-12 h-12 mx-auto mb-4 text-gray-400">
                    <Plus className="w-full h-full" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    No notebooks yet
                  </h3>
                  <p className="text-gray-500 mb-6">
                    Get started by creating your first notebook to organize your research and knowledge.
                  </p>
                  <Button onClick={handleCreateNotebook}>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Your First Notebook
                  </Button>
                </div>
              </div>
            ) : viewMode === 'grid' ? (
              <GridView />
            ) : (
              <DataTable
                columns={columns}
                data={notebooks}
                loading={isLoading}
                error={error}
                onRowClick={handleNotebookClick}
                globalFilter={searchQuery}
                onGlobalFilterChange={handleSearchChange}
                emptyMessage="No notebooks found"
                className="mt-6"
              />
            )}
          </Suspense>
        )}
      </div>
    </ErrorBoundary>
  );
};