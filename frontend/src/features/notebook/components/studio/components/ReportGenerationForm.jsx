// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on report generation configuration

import React, { useState } from 'react';
import { 
  FileText, 
  Settings,
  Info,
  AlertCircle,
  HelpCircle
} from 'lucide-react';
import { Button } from '@/common/components/ui/button';
import { COLORS } from '../../../config/uiConfig';
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
  
  // File selection props
  selectedFiles,
  

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
  
  // Tooltip state
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className="bg-transparent">
      {/* ====== SINGLE RESPONSIBILITY: Header rendering ====== */}
      <div className="px-6 py-4 bg-white/95 backdrop-blur-sm border-b border-gray-200/60">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-gradient-to-br from-red-500 to-red-600 rounded-lg flex items-center justify-center shadow-sm">
            <FileText className="h-4 w-4 text-white" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900">Generate Research Report</h3>
            <p className="text-xs text-gray-600">Comprehensive AI-powered research analysis</p>
          </div>
        </div>
      </div>

      {/* ====== SINGLE RESPONSIBILITY: Form content rendering ====== */}
      <div className="px-6 py-6 space-y-6">
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

          {/* Research topic input and action buttons */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <label className="block text-sm font-semibold text-gray-800">
                Research Topic
              </label>
              <div className="relative">
                <div 
                  className="flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 hover:bg-gray-200 transition-all duration-200 cursor-help"
                  onMouseEnter={() => setShowTooltip(true)}
                  onMouseLeave={() => setShowTooltip(false)}
                >
                  <HelpCircle className="h-3 w-3 text-gray-500" />
                </div>
                {showTooltip && (
                  <div className="absolute bottom-full mb-2 left-0 z-10">
                    <div className="bg-gray-900 text-white text-xs rounded-lg py-2 px-3 whitespace-nowrap shadow-xl">
                      Enter a research topic or select files from Sources
                      <div className="absolute top-full left-3 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                    </div>
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="flex-1 relative">
                <input
                  type="text"
                  placeholder="Enter research topic (e.g., 'AI in healthcare')"
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-red-500 shadow-sm transition-all duration-200 bg-white"
                  value={config.topic || ''}
                  onChange={(e) => onConfigChange({ topic: e.target.value })}
                />

              </div>
              <Button
                className={`font-medium px-4 py-2.5 rounded-lg transition-all duration-200 shadow-sm hover:shadow-md flex-shrink-0 text-sm ${
                  !canGenerate
                    ? 'bg-gray-300 hover:bg-gray-400 text-gray-500 cursor-not-allowed'
                    : 'bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white hover:scale-105'
                }`}
                onClick={onGenerate}
                disabled={!canGenerate}
              >
                <FileText className="mr-1.5 h-3.5 w-3.5" />
                Generate
              </Button>
            </div>
          </div>
        </div>
    </div>
  );
};

export default React.memo(ReportGenerationForm); // Performance optimization