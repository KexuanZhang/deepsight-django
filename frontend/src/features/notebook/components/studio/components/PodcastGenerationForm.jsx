// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on podcast generation configuration

import React, { useState } from 'react';
import { 
  Play, 
  Settings,
  Info,
  AlertCircle,
  Loader2,
  HelpCircle
} from 'lucide-react';
import { Button } from '@/common/components/ui/button';
import { COLORS } from '../../../config/uiConfig';
import StatusDisplay from './StatusDisplay';
import { GenerationState } from '../types';

// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Focused props interface for podcast configuration
const PodcastGenerationForm = ({
  // Configuration props
  config,
  onConfigChange,
  
  // Generation state props
  generationState,
  onGenerate,
  onCancel,
  
  // File selection props
  selectedFiles,
  selectedSources,
  

}) => {
  // ====== SINGLE RESPONSIBILITY: Validation logic ======
  const hasSelectedFiles = selectedFiles.length > 0;
  const canGenerate = hasSelectedFiles && generationState.state !== GenerationState.GENERATING;
  
  // Tooltip state
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className="bg-transparent">
      {/* ====== SINGLE RESPONSIBILITY: Header rendering ====== */}
      <div className="px-6 py-4 bg-white/95 backdrop-blur-sm border-b border-gray-200/60">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg flex items-center justify-center shadow-sm">
            <Play className="h-4 w-4 text-white" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900">Generate Panel Discussion</h3>
            <p className="text-xs text-gray-600">Create engaging AI-powered conversations</p>
          </div>
        </div>
      </div>
      
      {/* ====== SINGLE RESPONSIBILITY: Form content rendering ====== */}
      <div className="px-6 py-6 space-y-6">
          {/* Status display */}
          {(generationState.state !== GenerationState.IDLE) && (
            <StatusDisplay
              state={generationState.state}
              title="Generating Panel Discussion"
              progress={generationState.progress}
              error={generationState.error}
              showCancel={true}
              onCancel={onCancel}
            />
          )}

          {/* Panel Topic input and action buttons */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <label className="block text-sm font-semibold text-gray-800">
                Panel Topic
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
                      Select files from Sources to generate discussion
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
                  placeholder="Enter panel discussion topic (e.g., 'Future of AI Technology')"
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-orange-500 shadow-sm transition-all duration-200 bg-white"
                  value={config.topic || ''}
                  onChange={(e) => onConfigChange({ topic: e.target.value })}
                />

              </div>
              <Button
                className={`font-medium px-4 py-2.5 rounded-lg transition-all duration-200 shadow-sm hover:shadow-md flex-shrink-0 text-sm ${
                  !canGenerate
                    ? 'bg-gray-300 hover:bg-gray-400 text-gray-500 cursor-not-allowed'
                    : 'bg-gradient-to-r from-orange-600 to-orange-700 hover:from-orange-700 hover:to-orange-800 text-white hover:scale-105'
                }`}
                onClick={onGenerate}
                disabled={!canGenerate}
              >
                {generationState.state === GenerationState.GENERATING ? (
                  <>
                    <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Play className="mr-1.5 h-3.5 w-3.5" />
                    Generate
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
    </div>
  );
};

export default React.memo(PodcastGenerationForm); // Performance optimization