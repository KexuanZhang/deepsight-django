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
  
  // Additional handlers
  onShowAdvancedSettings
}) => {
  // ====== SINGLE RESPONSIBILITY: Validation logic ======
  const hasSelectedFiles = selectedFiles.length > 0;
  const canGenerate = hasSelectedFiles && generationState.state !== GenerationState.GENERATING;
  
  // Tooltip state
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className="bg-transparent">
      {/* ====== SINGLE RESPONSIBILITY: Header rendering ====== */}
      <div className="px-6 py-4 bg-orange-50/80 backdrop-blur-sm border-b border-orange-100/50">
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
      <div className="px-6 py-4 bg-orange-50/30 backdrop-blur-sm space-y-4">
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

          {/* Panel Topic input */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="block text-sm font-medium text-gray-700">
                Panel Topic
              </label>
            </div>
            <input
              type="text"
              placeholder="Enter panel discussion topic (e.g., 'Future of AI Technology')"
              className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent shadow-sm"
              value={config.topic || ''}
              onChange={(e) => onConfigChange({ topic: e.target.value })}
            />
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-between space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={onShowAdvancedSettings}
              className="text-sm text-gray-500 hover:text-gray-700 flex items-center hover:bg-gray-100/50 px-3 py-2 rounded-lg"
            >
              <Settings className="h-4 w-4 mr-2" />
              Advanced Settings
            </Button>
            
            <div className="flex items-center space-x-2">
              <Button
                className={`font-medium px-5 py-2.5 rounded-lg transition-all duration-200 shadow-sm ${
                  !canGenerate
                    ? 'bg-gray-400 hover:bg-gray-500 text-white cursor-not-allowed'
                    : 'bg-orange-600 hover:bg-orange-700 text-white hover:shadow-md'
                }`}
                onClick={onGenerate}
                disabled={!canGenerate}
              >
                {generationState.state === GenerationState.GENERATING ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : !hasSelectedFiles ? (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Generate Podcast
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Generate Podcast
                  </>
                )}
              </Button>
              <div className="relative">
                <div 
                  className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors cursor-help"
                  onMouseEnter={() => setShowTooltip(true)}
                  onMouseLeave={() => setShowTooltip(false)}
                >
                  <HelpCircle className="h-4 w-4 text-gray-500" />
                </div>
                {showTooltip && (
                  <div className="absolute bottom-full mb-2 right-0 z-10">
                    <div className="bg-gray-900 text-white text-xs rounded-lg py-2 px-3 whitespace-nowrap shadow-lg">
                      Please select at least one file from the Sources panel to generate a panel discussion.
                      <div className="absolute top-full right-6 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
    </div>
  );
};

export default React.memo(PodcastGenerationForm); // Performance optimization