// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on report generation configuration

import React from 'react';
import { 
  FileText, 
  ChevronDown, 
  ChevronUp, 
  Settings,
  Info,
  AlertCircle
} from 'lucide-react';
import { Button } from '@/common/components/ui/button';
import StatusDisplay from './StatusDisplay';
import { GenerationState } from '../types';

// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Focused props interface for report configuration
const ReportGenerationForm = ({
  // Configuration props
  config,
  onConfigChange,
  availableModels,
  
  // Generation state props
  generationState,
  onGenerate,
  onCancel,
  
  // UI state props
  isCollapsed,
  onToggleCollapse,
  
  // File selection props
  selectedFiles,
  
  // Additional handlers
  onShowCustomize
}) => {
  // ====== SINGLE RESPONSIBILITY: Validation logic ======
  const hasValidInput = () => {
    const hasTopic = config.topic?.trim();
    const hasFiles = selectedFiles.length > 0;
    return hasTopic || hasFiles;
  };

  // ====== SINGLE RESPONSIBILITY: Model name formatting ======
  const formatModelName = (value) => {
    return value.charAt(0).toUpperCase() + value.slice(1);
  };

  const canGenerate = hasValidInput() && generationState.state !== GenerationState.GENERATING;

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm hover:shadow-md transition-all duration-200">
      {/* ====== SINGLE RESPONSIBILITY: Header rendering ====== */}
      <div 
        className="px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-100 cursor-pointer hover:from-blue-100 hover:to-indigo-100 transition-all duration-200 min-h-[72px]"
        onClick={onToggleCollapse}
      >
        <div className="flex items-center justify-between h-full">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-sm">
              <FileText className="h-4 w-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Generate Research Report</h3>
              <p className="text-xs text-gray-600">Comprehensive AI-powered research analysis</p>
            </div>
          </div>
          {isCollapsed ? 
            <ChevronDown className="h-4 w-4 text-gray-500" /> : 
            <ChevronUp className="h-4 w-4 text-gray-500" />
          }
        </div>
      </div>

      {/* ====== SINGLE RESPONSIBILITY: Form content rendering ====== */}
      {!isCollapsed && (
        <div className="p-6 space-y-5">
          {/* Status display */}
          {(generationState.state !== GenerationState.IDLE) && (
            <StatusDisplay
              state={generationState.state}
              title="Generating Research Report"
              progress={generationState.progress}
              error={generationState.error}
              showCancel={true}
              onCancel={onCancel}
            />
          )}

          {/* Research topic input */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Research Topic
            </label>
            <input
              type="text"
              placeholder="Enter research topic (e.g., 'AI in healthcare')"
              className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={config.topic || ''}
              onChange={(e) => onConfigChange({ topic: e.target.value })}
            />
            <p className="text-xs text-gray-500 flex items-center">
              <Info className="h-3 w-3 mr-1" />
              You can also upload PDF, transcript, or paper files in the Sources panel for analysis.
            </p>
          </div>

          {/* Report title input */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Report Title</label>
            <input
              type="text"
              placeholder="Enter report title..."
              className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={config.article_title || ''}
              onChange={(e) => onConfigChange({ article_title: e.target.value })}
            />
          </div>

          {/* Model and retriever selection */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">AI Model</label>
              <select
                className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={config.model_provider || ''}
                onChange={(e) => onConfigChange({ model_provider: e.target.value })}
              >
                {(availableModels?.model_providers || []).map(provider => (
                  <option key={provider} value={provider}>
                    {formatModelName(provider)}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">Search Engine</label>
              <select
                className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={config.retriever || ''}
                onChange={(e) => onConfigChange({ retriever: e.target.value })}
              >
                {(availableModels?.retrievers || []).map(retriever => (
                  <option key={retriever} value={retriever}>
                    {formatModelName(retriever)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Advanced settings button */}
          <div className="flex justify-center">
            <Button
              variant="outline"
              size="sm"
              onClick={onShowCustomize}
              className="text-sm border-blue-200 text-blue-700 hover:bg-blue-50 hover:border-blue-300 transition-all duration-200"
            >
              <Settings className="mr-2 h-4 w-4" />
              Advanced Settings
            </Button>
          </div>

          {/* Validation warning */}
          {!hasValidInput() && (
            <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg">
              <p className="text-sm text-yellow-800 flex items-center font-medium">
                <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
                Please enter a research topic or select files from the Sources panel.
              </p>
            </div>
          )}

          {/* Generate button */}
          <Button
            className={`w-full font-medium py-3 transition-all duration-200 ${
              !canGenerate
                ? 'bg-gray-400 hover:bg-gray-500 text-white cursor-not-allowed'
                : 'bg-gray-900 hover:bg-gray-800 text-white'
            }`}
            onClick={onGenerate}
            disabled={!canGenerate}
            title={!hasValidInput() ? "Please enter a topic or select files first" : "Generate research report"}
          >
            <FileText className="mr-2 h-4 w-4" />
            Generate Report
          </Button>
        </div>
      )}
    </div>
  );
};

export default React.memo(ReportGenerationForm); // Performance optimization