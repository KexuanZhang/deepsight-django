// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on podcast generation configuration

import React, { useState } from 'react';
import { 
  Play, 
  Loader2,
  MessageSquare
} from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import StatusDisplay from './StatusDisplay';
import { GenerationState } from './types';
import { COLORS } from "@/features/notebook/config/uiConfig";

// TypeScript interfaces
interface PodcastConfig {
  title?: string;
  description?: string;
  topic?: string;
  expert_names?: {
    host?: string;
    expert1?: string;
    expert2?: string;
  };
}

interface FileItem {
  id: string;
  name: string;
  type: string;
  size?: number;
  url?: string;
}

interface PodcastGenerationFormProps {
  // Configuration props
  config: PodcastConfig;
  onConfigChange: (config: Partial<PodcastConfig>) => void;
  
  // Generation state props
  generationState: {
    state: GenerationState;
    progress?: string;
    error?: string;
  };
  onGenerate: (configOverrides?: Partial<PodcastConfig>) => void;
  onCancel: () => void;
  
  // File selection props
  selectedFiles: FileItem[];
  selectedSources: any[];
  
  // Modal props
  onOpenModal: (modalType: string, data: React.ReactNode) => void;
  onCloseModal: (modalType: string) => void;
}

// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Focused props interface for podcast configuration
const PodcastGenerationForm: React.FC<PodcastGenerationFormProps> = ({
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
  
  // Modal props
  onOpenModal,
  onCloseModal,

}) => {
  // ====== SINGLE RESPONSIBILITY: Validation logic ======
  const hasSelectedFiles = selectedFiles.length > 0;
  const canGenerate = hasSelectedFiles && generationState.state !== GenerationState.GENERATING;

  return (
    <>
      <div className="bg-white rounded-2xl border border-gray-200">
        {/* ====== SINGLE RESPONSIBILITY: Card content ====== */}
        <div className="p-5">
          {/* Status display */}
          {(generationState.state !== GenerationState.IDLE) && (
            <div className="mb-4">
              <StatusDisplay
                state={generationState.state}
                title="Generating Panel Discussion"
                progress={generationState.progress}
                error={generationState.error}
                showCancel={true}
                onCancel={onCancel}
              />
            </div>
          )}

          {/* Card header with icon and info */}
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center border-2 border-gray-300">
              <MessageSquare className="h-5 w-5 text-gray-700" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Deep Dive Conversation</h3>
              <p className="text-sm text-gray-600">One host with two guests</p>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center space-x-3">
            <div className="flex-1">
              <Button
                variant="outline"
                className="w-full px-6 py-2 border-gray-300 text-gray-700 hover:bg-gray-50 rounded-full transition-colors"
                onClick={() => {
                  // Import CustomizeModal component dynamically
                  import('./CustomizeModal').then(({ default: CustomizeModal }) => {
                    const customizeContent = (
                      <CustomizeModal
                        isOpen={true}
                        onClose={() => onCloseModal('customizePodcast')}
                        config={config}
                        onConfigChange={onConfigChange}
                        type="podcast"
                        selectedFiles={selectedFiles}
                        onGenerate={(configOverrides) => onGenerate(configOverrides)}
                      />
                    );
                    onOpenModal('customizePodcast', customizeContent);
                  });
                }}
              >
                Customize
              </Button>
            </div>
            <div className="flex-1 relative group">
              <Button
                className={`w-full px-6 py-2 rounded-full transition-colors text-sm ${
                  !canGenerate
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : `${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]} text-white`
                }`}
                onClick={() => onGenerate()}
                disabled={!canGenerate}
              >
                {generationState.state === GenerationState.GENERATING ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Generate
                  </>
                )}
              </Button>
              {!canGenerate && (
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 whitespace-nowrap z-10">
                  Select at least one source to generate
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

    </>
  );
};

export default React.memo(PodcastGenerationForm); // Performance optimization