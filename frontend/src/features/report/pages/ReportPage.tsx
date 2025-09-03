import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import type { AppDispatch } from '@/app/store';
import { 
  fetchReports, 
  selectFilteredReports, 
  selectReportLoading, 
  selectReportError,
  selectViewMode,
  selectSortOrder,
  selectSearchTerm,
  selectFilters,
  selectReportStats,
  setSearchTerm,
  setSortOrder,
  setViewMode,
  setFilters,
  clearError
} from "@/features/report/reportSlice";
import ReportList from "@/features/report/components/ReportList";
import ReportFilters from "@/features/report/components/ReportFilters";
import ReportStats from "@/features/report/components/ReportStats";
import ReportDetail from "@/features/report/components/ReportDetail";
import { Report } from "@/features/report/types/type";

const ReportPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const reports = useSelector(selectFilteredReports);
  const isLoading = useSelector(selectReportLoading);
  const error = useSelector(selectReportError);
  const viewMode = useSelector(selectViewMode);
  const sortOrder = useSelector(selectSortOrder);
  const searchTerm = useSelector(selectSearchTerm);
  const filters = useSelector(selectFilters);
  const stats = useSelector(selectReportStats);

  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  useEffect(() => {
    dispatch(fetchReports(filters));
  }, [dispatch, filters]);

  useEffect(() => {
    if (error) {
      // Auto-clear error after 5 seconds
      const timer = setTimeout(() => {
        dispatch(clearError());
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, dispatch]);

  const handleSelectReport = (report: Report) => {
    setSelectedReport(report);
    setShowDetail(true);
  };

  const handleBackToList = () => {
    setShowDetail(false);
    setSelectedReport(null);
  };

  const handleSearchChange = (term: string) => {
    dispatch(setSearchTerm(term));
  };

  const handleSortChange = (order: 'recent' | 'oldest' | 'title') => {
    dispatch(setSortOrder(order));
  };

  const handleViewModeChange = (mode: 'grid' | 'list') => {
    dispatch(setViewMode(mode));
  };

  const handleFiltersChange = (newFilters: any) => {
    dispatch(setFilters(newFilters));
  };

  const handleDownloadReport = (report: Report) => {
    // This would be implemented with the download action
    console.log('Downloading report:', report.id);
  };

  const handleDeleteReport = (report: Report) => {
    // This would be implemented with the delete action
    console.log('Deleting report:', report.id);
  };

  const handleEditReport = (report: Report) => {
    // This would navigate to edit mode
    console.log('Editing report:', report.id);
  };

  if (showDetail && selectedReport) {
    return (
      <ReportDetail
        report={selectedReport}
        isLoading={isLoading}
        onDownload={handleDownloadReport}
        onDelete={handleDeleteReport}
        onEdit={handleEditReport}
        onBack={handleBackToList}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Research Reports</h1>
          <p className="mt-2 text-gray-600">
            Generate and manage your research reports
          </p>
        </div>

        {/* Stats */}
        <div className="mb-6">
          <ReportStats stats={stats} />
        </div>

        {/* Filters and Controls */}
        <div className="mb-6 bg-white rounded-lg shadow p-6">
          <ReportFilters
            filters={filters}
            onFiltersChange={handleFiltersChange}
            stats={stats}
          />
          
          {/* Search and View Controls */}
          <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex-1 max-w-md">
              <input
                type="text"
                placeholder="Search reports..."
                value={searchTerm}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div className="flex items-center gap-4">
              {/* Sort Order */}
              <select
                value={sortOrder}
                onChange={(e) => handleSortChange(e.target.value as 'recent' | 'oldest' | 'title')}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="recent">Most Recent</option>
                <option value="oldest">Oldest First</option>
                <option value="title">Title A-Z</option>
              </select>

              {/* View Mode */}
              <div className="flex border border-gray-300 rounded-md">
                <button
                  onClick={() => handleViewModeChange('grid')}
                  className={`px-3 py-2 ${
                    viewMode === 'grid' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  } rounded-l-md`}
                >
                  Grid
                </button>
                <button
                  onClick={() => handleViewModeChange('list')}
                  className={`px-3 py-2 ${
                    viewMode === 'list' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  } rounded-r-md`}
                >
                  List
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Reports List */}
        <div className="bg-white rounded-lg shadow">
          <ReportList
            reports={reports}
            isLoading={isLoading}
            onSelectReport={handleSelectReport}
            onDownloadReport={handleDownloadReport}
            onDeleteReport={handleDeleteReport}
            onEditReport={handleEditReport}
            selectedReportId={selectedReport?.id}
            viewMode={viewMode}
          />
        </div>

        {/* Empty State */}
        {!isLoading && reports.length === 0 && (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No reports found</h3>
            <p className="mt-1 text-sm text-gray-500">
              {searchTerm || Object.keys(filters).length > 0 
                ? 'Try adjusting your search or filters.'
                : 'Get started by creating your first research report.'
              }
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;