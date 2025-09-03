import React from 'react';
import { Report } from '../types/type';

interface ReportListItemProps {
  report: Report;
  onSelect: (report: Report) => void;
}

const ReportListItem: React.FC<ReportListItemProps> = ({ report, onSelect }) => {
  const handleClick = () => {
    onSelect(report);
  };

  // Generate preview text from content or description
  const getPreviewText = () => {
    if (report.content) {
      return report.content.length > 100 
        ? report.content.substring(0, 100) + '...' 
        : report.content;
    }
    if (report.description) {
      return report.description.length > 100 
        ? report.description.substring(0, 100) + '...' 
        : report.description;
    }
    return '好的,以下是根据您提供的资料整理的详细时间线和人物列表: 详细时间线说明: 本时间线...';
  };

  return (
    <div 
      className="mb-4 p-4 bg-gray-100 rounded-lg cursor-pointer hover:bg-gray-200 transition-colors"
      onClick={handleClick}
    >
      <div className="flex items-start space-x-3">
        {/* Three dots icon */}
        <div className="flex flex-col space-y-1 mt-1">
          <div className="w-1 h-1 bg-gray-600 rounded-full"></div>
          <div className="w-1 h-1 bg-gray-600 rounded-full"></div>
          <div className="w-1 h-1 bg-gray-600 rounded-full"></div>
        </div>
        
        <div className="flex-1 min-w-0">
          {/* Title */}
          <h3 className="font-bold text-gray-900 mb-2">
            {report.title || report.article_title || '大模型与生成式AI研究进展'}
          </h3>
          
          {/* Preview text */}
          <p className="text-sm text-gray-700 leading-relaxed">
            {getPreviewText()}
          </p>
        </div>
      </div>
    </div>
  );
};

export default ReportListItem; 