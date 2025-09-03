import React from 'react';
import { Report, ReportListProps } from '../types/type';
import ReportCard from './ReportCard';

const ReportList: React.FC<ReportListProps> = ({
  reports,
  isLoading,
  onSelectReport,
  onDownloadReport,
  onDeleteReport,
  onEditReport,
  selectedReportId,
  viewMode
}) => {
  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-gray-200 rounded"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (viewMode === 'grid') {
    return (
      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {reports.map((report) => (
            <ReportCard
              key={report.id}
              report={report}
              onSelect={onSelectReport}
              onDownload={onDownloadReport}
              onDelete={onDeleteReport}
              onEdit={onEditReport}
              isSelected={selectedReportId === report.id}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-hidden">
      <div className="min-w-full divide-y divide-gray-200">
        {reports.map((report) => (
          <div
            key={report.id}
            className={`p-6 hover:bg-gray-50 cursor-pointer ${
              selectedReportId === report.id ? 'bg-blue-50' : ''
            }`}
            onClick={() => onSelectReport(report)}
          >
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    <div className="h-10 w-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {report.title || report.article_title || 'Untitled Report'}
                    </p>
                    <p className="text-sm text-gray-500 truncate">
                      {report.topic || 'No topic specified'}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                {/* Status Badge */}
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  report.status === 'completed' ? 'bg-green-100 text-green-800' :
                  report.status === 'failed' ? 'bg-red-100 text-red-800' :
                  report.status === 'running' ? 'bg-blue-100 text-blue-800' :
                  report.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {report.status}
                </span>
                
                {/* Date */}
                <span className="text-sm text-gray-500">
                  {new Date(report.created_at).toLocaleDateString()}
                </span>
                
                {/* Actions */}
                <div className="flex items-center space-x-1">
                  {report.status === 'completed' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDownloadReport(report);
                      }}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Download"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </button>
                  )}
                  
                  {onEditReport && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onEditReport(report);
                      }}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Edit"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                  )}
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteReport(report);
                    }}
                    className="p-1 text-gray-400 hover:text-red-600"
                    title="Delete"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
            
            {/* Progress for running reports */}
            {report.status === 'running' && report.progress && (
              <div className="mt-3">
                <div className="flex items-center space-x-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: "60%" }}></div>
                  </div>
                  <span className="text-xs text-gray-500">{report.progress}</span>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ReportList; 