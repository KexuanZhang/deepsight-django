// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on displaying report list

import React from 'react';
import { 
  FileText,
  ChevronDown, 
  ChevronUp,
  ExternalLink,
  Edit,
  Trash2,
  Clock
} from 'lucide-react';
import { COLORS } from '@/features/notebook/config/uiConfig';
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";

interface Report {
  id?: string;
  title?: string;
  article_title?: string;
  topic?: string;
  status?: string;
  created_at?: string;
  [key: string]: any;
}

interface ReportFileItemProps {
  report: Report;
  onSelect: (report: Report) => void;
  onDownload: (report: Report) => void;
  onEdit: (report: Report) => void;
  onDelete: (report: Report) => void;
}

// ====== SINGLE RESPONSIBILITY: Individual report file item ======
const ReportFileItem = React.memo<ReportFileItemProps>(({ 
  report, 
  onSelect, 
  onDownload, 
  onEdit, 
  onDelete 
}) => {
  const formatDate = (dateString?: string): string => {
    if (!dateString) return '';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return '';
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="text-xs">Ready</Badge>;
      case 'generating':
        return <Badge variant="secondary" className="text-xs">Generating</Badge>;
      case 'failed':
        return <Badge variant="destructive" className="text-xs">Failed</Badge>;
      default:
        return <Badge variant="outline" className="text-xs">Unknown</Badge>;
    }
  };

  return (
    <div className={`p-4 ${COLORS.panels.commonBackground}/60 backdrop-blur-sm hover:${COLORS.panels.commonBackground}/80 transition-colors cursor-pointer border-b border-gray-100/50 last:border-b-0`}>
      <div className="flex items-start justify-between">
        <div 
          className="flex-1 min-w-0" 
          onClick={() => onSelect(report)}
        >
          <div className="flex items-center space-x-2 mb-2">
            <FileText className="h-4 w-4 text-blue-600 flex-shrink-0" />
            <h4 className="font-medium text-gray-900 truncate">
              {report.title || report.article_title || 'Untitled Report'}
            </h4>
            {getStatusBadge(report.status)}
          </div>
          
          {report.topic && (
            <p className="text-sm text-gray-600 mb-2 line-clamp-2">
              Topic: {report.topic}
            </p>
          )}
          
          <div className="flex items-center text-xs text-gray-500">
            <Clock className="h-3 w-3 mr-1" />
            {formatDate(report.created_at)}
          </div>
        </div>
        
        <div className="flex items-center space-x-1 ml-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onDownload(report);
            }}
            className="h-8 w-8 p-0"
            title="Open PDF"
          >
            <ExternalLink className="h-4 w-4" />
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onEdit(report);
            }}
            className="h-8 w-8 p-0"
            title="Edit report"
          >
            <Edit className="h-4 w-4" />
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(report);
            }}
            className="h-8 w-8 p-0 text-red-600 hover:text-red-700"
            title="Delete report"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
});

ReportFileItem.displayName = 'ReportFileItem';

interface ReportListSectionProps {
  reports: Report[];
  loading: boolean;
  error?: string;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onSelectReport: (report: Report) => void;
  onDownloadReport: (report: Report) => void;
  onEditReport: (report: Report) => void;
  onDeleteReport: (report: Report) => void;
}

// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Focused props interface for report list display
const ReportListSection: React.FC<ReportListSectionProps> = ({
  reports,
  loading,
  error,
  isCollapsed,
  onToggleCollapse,
  onSelectReport,
  onDownloadReport,
  onEditReport,
  onDeleteReport
}) => {
  const reportCount = reports.length;

  return (
    <div className="bg-transparent">
      {/* ====== SINGLE RESPONSIBILITY: Header rendering ====== */}
      <div 
        className={`px-6 py-5 ${COLORS.panels.commonBackground}/80 backdrop-blur-sm cursor-pointer hover:${COLORS.panels.commonBackground}/90 transition-all duration-200 border-b border-gray-100/50`}
        onClick={onToggleCollapse}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-red-500 to-red-600 rounded-lg flex items-center justify-center shadow-sm">
              <FileText className="h-4 w-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">
                Research Reports
                {reportCount > 0 && (
                  <span className="ml-2 text-sm font-normal text-gray-600">
                    ({reportCount})
                  </span>
                )}
              </h3>
              <p className="text-xs text-gray-600">Generated research reports</p>
            </div>
          </div>
          {isCollapsed ? 
            <ChevronDown className="h-4 w-4 text-gray-500" /> : 
            <ChevronUp className="h-4 w-4 text-gray-500" />
          }
        </div>
      </div>

      {/* ====== SINGLE RESPONSIBILITY: Content rendering ====== */}
      {!isCollapsed && (
        <div className="p-6">
          {loading && (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
              <p className="text-sm text-gray-500 mt-2">Loading reports...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {!loading && !error && reportCount === 0 && (
            <div className="text-center py-8">
              <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-gray-900 mb-2">No reports yet</h4>
              <p className="text-sm text-gray-500">
                Generate your first research report using the form above.
              </p>
            </div>
          )}

          {!loading && !error && reportCount > 0 && (
            <div className="space-y-3">
              {reports.map((report, index) => (
                <ReportFileItem
                  key={report.id || report.job_id || `report-${index}`}
                  report={report}
                  onSelect={onSelectReport}
                  onDownload={onDownloadReport}
                  onEdit={onEditReport}
                  onDelete={onDeleteReport}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default React.memo(ReportListSection); // Performance optimization