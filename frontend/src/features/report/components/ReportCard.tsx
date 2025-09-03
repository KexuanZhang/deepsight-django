import React from "react";
import { Report, ReportCardProps } from "../types/type";

export default function ReportCard({ 
  report, 
  onSelect, 
  onDownload, 
  onDelete, 
  onEdit, 
  isSelected 
}: ReportCardProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelect(report);
  };

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDownload(report);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(report);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onEdit) onEdit(report);
  };

  return (
    <div 
      className={`border rounded-lg overflow-hidden shadow hover:shadow-lg transition-shadow cursor-pointer ${
        isSelected ? 'ring-2 ring-blue-500' : ''
      }`}
      onClick={handleClick}
    >
      {/* Cover Image or Placeholder */}
      <div className="h-40 bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <svg className="h-16 w-16 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
      
      <div className="p-4">
        {/* Title */}
        <h3 className="font-semibold mb-2 text-gray-900 line-clamp-2">
          {report.title || report.article_title || 'Untitled Report'}
        </h3>
        
        {/* Topic */}
        <p className="text-gray-500 text-sm mb-2">
          {report.topic || 'No topic specified'}
        </p>
        
        {/* Status Badge */}
        <div className="flex items-center justify-between mb-3">
          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
            report.status === 'completed' ? 'bg-green-100 text-green-800' :
            report.status === 'failed' ? 'bg-red-100 text-red-800' :
            report.status === 'running' ? 'bg-blue-100 text-blue-800' :
            report.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {report.status}
          </span>
          
          <span className="text-xs text-gray-500">
            {new Date(report.created_at).toLocaleDateString()}
          </span>
        </div>
        
        {/* Actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {report.status === 'completed' && (
              <button
                onClick={handleDownload}
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                title="Download Report"
              >
                Download
              </button>
            )}
            
            {onEdit && (
              <button
                onClick={handleEdit}
                className="text-gray-600 hover:text-gray-800 text-sm"
                title="Edit Report"
              >
                Edit
              </button>
            )}
          </div>
          
          <button
            onClick={handleDelete}
            className="text-red-600 hover:text-red-800 text-sm"
            title="Delete Report"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
