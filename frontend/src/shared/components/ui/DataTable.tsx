/**
 * Enhanced Data Table Component with modern patterns
 */

import { useMemo } from 'react';
import { 
  flexRender,
  getCoreRowModel,
  useReactTable,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
  type PaginationState,
  type OnChangeFn,
} from '@tanstack/react-table';
import { ChevronDown, ChevronUp, ChevronsUpDown, Search } from 'lucide-react';
import { cn } from "@/shared/utils/utils";
import { LoadingSpinner, Skeleton } from './LoadingSpinner';
import { Button } from "@/shared/components/ui/button";

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  loading?: boolean;
  error?: Error | null;
  
  // Pagination
  pagination?: PaginationState;
  onPaginationChange?: OnChangeFn<PaginationState>;
  pageCount?: number;
  
  // Sorting
  sorting?: SortingState;
  onSortingChange?: OnChangeFn<SortingState>;
  
  // Filtering
  globalFilter?: string;
  onGlobalFilterChange?: (value: string) => void;
  columnFilters?: ColumnFiltersState;
  onColumnFiltersChange?: OnChangeFn<ColumnFiltersState>;
  
  // Selection
  rowSelection?: Record<string, boolean>;
  onRowSelectionChange?: OnChangeFn<Record<string, boolean>>;
  
  // UI customization
  className?: string;
  showGlobalFilter?: boolean;
  showPagination?: boolean;
  emptyMessage?: string;
  
  // Row actions
  onRowClick?: (row: TData) => void;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  loading = false,
  error = null,
  pagination,
  onPaginationChange,
  pageCount,
  sorting,
  onSortingChange,
  globalFilter = '',
  onGlobalFilterChange,
  columnFilters,
  onColumnFiltersChange,
  rowSelection,
  onRowSelectionChange,
  className,
  showGlobalFilter = true,
  showPagination = true,
  emptyMessage = 'No data available',
  onRowClick,
}: DataTableProps<TData, TValue>) {
  
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    
    // Controlled state
    state: {
      sorting: sorting || [],
      globalFilter,
      columnFilters: columnFilters || [],
      pagination: pagination || { pageIndex: 0, pageSize: 10 },
      rowSelection: rowSelection || {},
    },
    
    // Event handlers
    onSortingChange,
    onGlobalFilterChange,
    onColumnFiltersChange,
    onPaginationChange,
    onRowSelectionChange,
    
    // Server-side pagination
    pageCount,
    manualPagination: !!pageCount,
    manualSorting: !!onSortingChange,
    manualFiltering: !!onGlobalFilterChange,
    
    // Enable features
    enableRowSelection: !!rowSelection,
    enableMultiRowSelection: true,
    enableSorting: true,
    enableColumnFilters: true,
    enableGlobalFilter: true,
  });

  const TableSkeleton = useMemo(() => {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, rowIndex) => (
          <div key={rowIndex} className="flex space-x-4">
            {columns.map((_, colIndex) => (
              <Skeleton key={colIndex} variant="rectangular" height={40} className="flex-1" />
            ))}
          </div>
        ))}
      </div>
    );
  }, [columns]);

  if (error) {
    return (
      <div className="text-center py-8 text-red-600">
        <p>Error loading data: {error.message}</p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Global Filter */}
      {showGlobalFilter && onGlobalFilterChange && (
        <div className="flex items-center space-x-2 max-w-sm">
          <Search className="w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search..."
            value={globalFilter}
            onChange={(e) => onGlobalFilterChange(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      )}

      {/* Table */}
      <div className="relative overflow-hidden border rounded-lg">
        {loading && (
          <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-10">
            <LoadingSpinner size="lg" />
          </div>
        )}
        
        <table className="w-full">
          <thead className="bg-gray-50">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const sortDirection = header.column.getIsSorted();
                  
                  return (
                    <th
                      key={header.id}
                      className={cn(
                        'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider',
                        canSort && 'cursor-pointer hover:bg-gray-100 transition-colors'
                      )}
                      onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                    >
                      <div className="flex items-center space-x-1">
                        <span>
                          {header.isPlaceholder
                            ? null
                            : flexRender(header.column.columnDef.header, header.getContext())
                          }
                        </span>
                        {canSort && (
                          <span className="text-gray-400">
                            {sortDirection === false ? (
                              <ChevronDown className="w-4 h-4" />
                            ) : sortDirection === 'asc' ? (
                              <ChevronUp className="w-4 h-4" />
                            ) : (
                              <ChevronsUpDown className="w-4 h-4" />
                            )}
                          </span>
                        )}
                      </div>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={columns.length} className="p-6">
                  {TableSkeleton}
                </td>
              </tr>
            ) : table.getRowModel().rows.length > 0 ? (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className={cn(
                    'hover:bg-gray-50 transition-colors',
                    row.getIsSelected() && 'bg-blue-50',
                    onRowClick && 'cursor-pointer'
                  )}
                  onClick={() => onRowClick?.(row.original)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-6 py-8 text-center text-gray-500"
                >
                  {emptyMessage}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {showPagination && (
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <p className="text-sm text-gray-700">
              Showing{' '}
              <span className="font-medium">
                {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1}
              </span>{' '}
              to{' '}
              <span className="font-medium">
                {Math.min(
                  (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
                  table.getPrePaginationRowModel().rows.length
                )}
              </span>{' '}
              of{' '}
              <span className="font-medium">
                {table.getPrePaginationRowModel().rows.length}
              </span>{' '}
              results
            </p>
          </div>
          
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              Previous
            </Button>
            
            <div className="flex items-center space-x-1">
              {Array.from({ length: Math.min(5, table.getPageCount()) }, (_, i) => {
                const pageIndex = table.getState().pagination.pageIndex;
                const pageCount = table.getPageCount();
                
                let page: number;
                if (pageCount <= 5) {
                  page = i;
                } else if (pageIndex < 3) {
                  page = i;
                } else if (pageIndex > pageCount - 4) {
                  page = pageCount - 5 + i;
                } else {
                  page = pageIndex - 2 + i;
                }
                
                return (
                  <Button
                    key={page}
                    variant={pageIndex === page ? "default" : "outline"}
                    size="sm"
                    onClick={() => table.setPageIndex(page)}
                    className="w-8 h-8 p-0"
                  >
                    {page + 1}
                  </Button>
                );
              })}
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}