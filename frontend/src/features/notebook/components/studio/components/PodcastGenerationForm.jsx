// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on podcast generation configuration

import React from 'react';
import { 
  Play, 
  ChevronDown, 
  ChevronUp, 
  Info,
  AlertCircle,
  Loader2
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
  
  // UI state props
  isCollapsed,
  onToggleCollapse,
  
  // File selection props
  selectedFiles,
  selectedSources
}) => {
  // ====== SINGLE RESPONSIBILITY: Validation logic ======
  const hasSelectedFiles = selectedFiles.length > 0;
  const canGenerate = hasSelectedFiles && generationState.state !== GenerationState.GENERATING;

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm hover:shadow-md transition-all duration-200">
      {/* ====== SINGLE RESPONSIBILITY: Header rendering ====== */}
      <div 
        className="px-6 py-4 bg-gradient-to-r from-orange-50 to-amber-50 border-b border-orange-100 cursor-pointer hover:from-orange-100 hover:to-amber-100 transition-all duration-200 min-h-[72px]"
        onClick={onToggleCollapse}
      >
        <div className="flex items-center justify-between h-full">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-amber-500 rounded-lg flex items-center justify-center shadow-sm">
              <Play className="h-4 w-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Generate Panel Discussion</h3>
              <p className="text-xs text-gray-600">Create engaging AI-powered conversations</p>
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
              title="Generating Panel Discussion"
              progress={generationState.progress}
              error={generationState.error}
              showCancel={true}
              onCancel={onCancel}
            />
          )}

          {/* Panel discussion title input */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Panel Discussion Title
            </label>
            <input
              type="text"
              placeholder="Enter panel discussion title..."
              className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              value={config.title || ""}
              onChange={(e) => onConfigChange({ title: e.target.value })}
            />
          </div>

          {/* Description input */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Description (Optional)</label>
            <textarea
              placeholder="Enter panel discussion description..."
              className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              rows={3}
              value={config.description || ""}
              onChange={(e) => onConfigChange({ description: e.target.value })}
            />
          </div>

          {/* Information panel */}
          <div className="bg-blue-50 p-3 rounded-lg">
            <p className="text-sm text-blue-700 flex items-center">
              <Info className="h-4 w-4 mr-2" />
              Select files from the Sources panel to generate a panel discussion between three experts: 杨飞飞 (host), 奥立昆, and 李特曼.
            </p>
          </div>

          {/* File selection warning */}
          {!hasSelectedFiles && (
            <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg">
              <p className="text-sm text-yellow-800 flex items-center font-medium">
                <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
                {selectedSources.length === 0 
                  ? "Please select at least one file from the Sources panel to generate a panel discussion."
                  : "Selected files are not ready for generation."
                }
              </p>
              <p className="text-xs text-yellow-700 mt-2 ml-6">
                {selectedSources.length === 0 
                  ? "Go to the Sources panel → Upload files or select existing files → Return here to generate"
                  : `You have ${selectedSources.length} file(s) selected, but they need to be fully parsed and completed before generation. Check the Sources panel for file status.`
                }
              </p>
              {selectedSources.length > 0 && (
                <div className="mt-2 ml-6">
                  <p className="text-xs text-yellow-700 font-medium">Selected files need to finish processing before generation.</p>
                </div>
              )}
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
            title={!hasSelectedFiles ? "Please select files from the Sources panel first" : "Generate panel discussion from selected files"}
          >
            {generationState.state === GenerationState.GENERATING ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating Panel Discussion...
              </>
            ) : !hasSelectedFiles ? (
              <>
                <AlertCircle className="mr-2 h-4 w-4" />
                Select Files to Generate
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Generate Panel Discussion
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
};

export default React.memo(PodcastGenerationForm); // Performance optimization