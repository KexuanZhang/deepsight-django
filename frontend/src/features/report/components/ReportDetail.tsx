import React, { useEffect, useState } from 'react';
import { Report, ReportDetailProps, ReportContent } from '../types/type';
import { ReportService } from '../services/ReportService';

const ReportDetail: React.FC<ReportDetailProps> = ({
  report,
  content,
  isLoading,
  onDownload,
  onDelete,
  onEdit,
  onBack
}) => {
  const [reportContent, setReportContent] = useState<ReportContent | null>(content || null);
  const [isLoadingContent, setIsLoadingContent] = useState(!content);

  useEffect(() => {
    if (!content && report.status === 'completed') {
      const loadContent = async () => {
        try {
          setIsLoadingContent(true);
          const reportService = new ReportService();
          const content = await reportService.getReportContent(report.id);
          setReportContent(content);
        } catch (error) {
          console.error('Failed to load report content:', error);
        } finally {
          setIsLoadingContent(false);
        }
      };
      loadContent();
    }
  }, [report.id, report.status, content]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100';
      case 'failed': return 'text-red-600 bg-red-100';
      case 'running': return 'text-blue-600 bg-blue-100';
      case 'pending': return 'text-yellow-600 bg-yellow-100';
      case 'cancelled': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={onBack}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  {report.title || report.article_title || 'Untitled Report'}
                </h1>
                <p className="text-gray-600 mt-1">
                  Created on {formatDate(report.created_at)}
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(report.status)}`}>
                {report.status}
              </span>
              
              {report.status === 'completed' && (
                <button
                  onClick={() => onDownload(report)}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                  <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download
                </button>
              )}
              
              {onEdit && (
                <button
                  onClick={() => onEdit(report)}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  Edit
                </button>
              )}
              
              <button
                onClick={() => onDelete(report)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
              >
                <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete
              </button>
            </div>
          </div>
        </div>

        {/* Report Metadata */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Report Details</h2>
          </div>
          <div className="px-6 py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-sm font-medium text-gray-500">Topic</h3>
                <p className="mt-1 text-sm text-gray-900">{report.topic || "No topic specified"}</p>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500">Model Provider</h3>
                <p className="mt-1 text-sm text-gray-900">{report.model_provider || "Not specified"}</p>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500">Retriever</h3>
                <p className="mt-1 text-sm text-gray-900">{report.retriever || "Not specified"}</p>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500">Prompt Type</h3>
                <p className="mt-1 text-sm text-gray-900">{report.prompt_type || "Not specified"}</p>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500">Created</h3>
                <p className="mt-1 text-sm text-gray-900">{formatDate(report.created_at)}</p>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500">Last Updated</h3>
                <p className="mt-1 text-sm text-gray-900">{formatDate(report.updated_at)}</p>
              </div>
            </div>
            
            {report.progress && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-gray-500">Progress</h3>
                <p className="mt-1 text-sm text-gray-900">{report.progress}</p>
              </div>
            )}
            
            {report.error_message && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-red-500">Error</h3>
                <p className="mt-1 text-sm text-red-600">{report.error_message}</p>
              </div>
            )}
          </div>
        </div>

        {/* Report Content */}
        {report.status === 'completed' && (
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Report Content</h2>
            </div>
            <div className="px-6 py-4">
              {isLoadingContent ? (
                <div className="animate-pulse space-y-4">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                  <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                </div>
              ) : reportContent ? (
                <div className="prose max-w-none">
                  {reportContent.markdown_content ? (
                    <div 
                      className="markdown-content"
                      dangerouslySetInnerHTML={{ __html: reportContent.markdown_content }}
                    />
                  ) : (
                    <pre className="whitespace-pre-wrap text-sm text-gray-900">
                      {reportContent.content}
                    </pre>
                  )}
                </div>
              ) : (
                <p className="text-gray-500">No content available</p>
              )}
            </div>
          </div>
        )}

        {/* Processing Logs */}
        {report.processing_logs && report.processing_logs.length > 0 && (
          <div className="bg-white rounded-lg shadow mt-6">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Processing Logs</h2>
            </div>
            <div className="px-6 py-4">
              <div className="space-y-2">
                {report.processing_logs.map((log, index) => (
                  <div key={index} className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                    {log}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportDetail; 