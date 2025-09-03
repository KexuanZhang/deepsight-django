import React from 'react';
import { PodcastFilters as PodcastFiltersType, PodcastStats } from '../types/type';

interface PodcastFiltersProps {
  filters: PodcastFiltersType;
  onFiltersChange: (filters: PodcastFiltersType) => void;
  stats?: PodcastStats;
}

const PodcastFilters: React.FC<PodcastFiltersProps> = ({
  filters,
  onFiltersChange,
  stats
}) => {
  const handleFilterChange = (key: keyof PodcastFiltersType, value: any) => {
    onFiltersChange({
      ...filters,
      [key]: value
    });
  };

  const clearFilters = () => {
    onFiltersChange({});
  };

  const hasActiveFilters = Object.keys(filters).some(key => filters[key as keyof PodcastFiltersType]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Filters</h3>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-sm text-purple-600 hover:text-purple-800"
          >
            Clear all filters
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Status Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Status
          </label>
          <select
            value={filters.status || ''}
            onChange={(e) => handleFilterChange('status', e.target.value || undefined)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="generating">Generating</option>
            <option value="pending">Pending</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        {/* Date Range Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Date Range
          </label>
          <div className="flex space-x-2">
            <input
              type="date"
              value={filters.date_range?.start || ''}
              onChange={(e) => handleFilterChange('date_range', {
                ...filters.date_range,
                start: e.target.value
              })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <input
              type="date"
              value={filters.date_range?.end || ''}
              onChange={(e) => handleFilterChange('date_range', {
                ...filters.date_range,
                end: e.target.value
              })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
        </div>
      </div>

      {/* Quick Filter Buttons */}
      {stats && (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => handleFilterChange('status', 'completed')}
            className={`px-3 py-1 rounded-full text-xs font-medium ${
              filters.status === 'completed'
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Completed ({stats.completed})
          </button>
          <button
            onClick={() => handleFilterChange('status', 'generating')}
            className={`px-3 py-1 rounded-full text-xs font-medium ${
              filters.status === 'generating'
                ? 'bg-blue-100 text-blue-800'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Generating ({stats.generating})
          </button>
          <button
            onClick={() => handleFilterChange('status', 'failed')}
            className={`px-3 py-1 rounded-full text-xs font-medium ${
              filters.status === 'failed'
                ? 'bg-red-100 text-red-800'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Failed ({stats.failed})
          </button>
          <button
            onClick={() => handleFilterChange('status', 'pending')}
            className={`px-3 py-1 rounded-full text-xs font-medium ${
              filters.status === 'pending'
                ? 'bg-yellow-100 text-yellow-800'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Pending ({stats.pending})
          </button>
        </div>
      )}
    </div>
  );
};

export default PodcastFilters; 