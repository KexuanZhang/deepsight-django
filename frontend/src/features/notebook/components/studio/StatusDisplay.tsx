// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on displaying generation status

import React from 'react';
import { 
  CheckCircle, 
  AlertCircle, 
  X, 
  Loader2 
} from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import { GenerationState } from './types';

// ====== OPEN/CLOSED PRINCIPLE (OCP) ======
// Status configurations that can be extended without modifying the component
const STATUS_CONFIGS = {
  [GenerationState.GENERATING]: {
    icon: Loader2,
    iconProps: { className: "h-5 w-5 animate-spin text-blue-600" },
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    getText: (title?: string) => title || 'Generating'
  },
  [GenerationState.COMPLETED]: {
    icon: CheckCircle,
    iconProps: { className: "h-5 w-5 text-green-600" },
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    getText: () => 'Ready'
  },
  [GenerationState.FAILED]: {
    icon: AlertCircle,
    iconProps: { className: "h-5 w-5 text-red-600" },
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    getText: () => 'Failed'
  },
  [GenerationState.CANCELLED]: {
    icon: X,
    iconProps: { className: "h-5 w-5 text-amber-600" },
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    getText: () => 'Cancelled'
  }
};

interface StatusDisplayProps {
  state: GenerationState;
  title?: string;
  progress?: string;
  error?: string;
  onCancel?: () => void;
  showCancel?: boolean;
}

// ====== LISKOV SUBSTITUTION PRINCIPLE (LSP) ======
// Consistent interface that can be used in any status context
const StatusDisplay: React.FC<StatusDisplayProps> = ({ 
  state,
  title,
  progress,
  error,
  onCancel,
  showCancel = false
}) => {
  // Truncate long progress messages
  const formatProgress = (progress?: string): string => {
    if (!progress) return '';
    return progress.length > 60 ? progress.substring(0, 57) + '...' : progress;
  };

  // Get configuration for current state
  const config = STATUS_CONFIGS[state as keyof typeof STATUS_CONFIGS] || STATUS_CONFIGS[GenerationState.COMPLETED];
  const IconComponent = config.icon;
  const displayText = config.getText(title);
  const formattedProgress = formatProgress(progress);

  // Map specific progress messages to a deterministic progress percentage
  const getProgressPercentage = (msg?: string): number => {
    if (!msg || typeof msg !== 'string') return 0;
    const lower = msg.toLowerCase();
    
    // Extract percentage from progress message if it contains (XX%)
    const percentageMatch = msg.match(/\((\d+)%\)/);
    if (percentageMatch && percentageMatch[1]) {
      return parseInt(percentageMatch[1]);
    }
    
    // Report generation stages
    if (lower.includes('run_knowledge_curation_module')) return 20;
    if (lower.includes('run_outline_generation_module')) return 40;
    if (lower.includes('run_article_generation_module')) return 60;
    if (lower.includes('run_article_polishing_module')) return 80;
    
    // Podcast generation stages
    if (lower.includes('starting podcast generation')) return 10;
    if (lower.includes('gathering content from source files')) return 20;
    if (lower.includes('generating podcast conversation')) return 40;
    if (lower.includes('conversation script and title generated')) return 70;
    if (lower.includes('generating podcast audio')) return 80;
    if (lower.includes('audio file uploaded successfully')) return 95;
    
    // Completion states
    if (lower.includes('succeeded') || lower.includes('completed successfully')) return 100;
    if (lower.includes('cancelled')) return 0;
    
    return 0; // Unknown stage
  };

  const progressPercentage = getProgressPercentage(progress);
  
  // Debug logging
  if (progress) {
    console.log('StatusDisplay - Progress:', progress, 'Percentage:', progressPercentage);
  }

  return (
    <div className={`rounded-xl p-4 border ${config.borderColor} ${config.bgColor}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <IconComponent {...config.iconProps} />
          <div>
            <p className={`font-medium ${config.color}`}>{displayText}</p>
            {formattedProgress && (
              <p className="text-sm text-gray-600 mt-1">{formattedProgress}</p>
            )}
            {error && state !== GenerationState.CANCELLED && (
              <p className="text-sm text-red-600 mt-1">{error}</p>
            )}
          </div>
        </div>
        
        {showCancel && state === GenerationState.GENERATING && (
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md border border-red-300 text-red-600 bg-white hover:bg-red-50 hover:border-red-400 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            <X className="mr-1 h-4 w-4" />
            Cancel
          </button>
        )}
      </div>
      
      {state === GenerationState.GENERATING && (
        <div className="mt-3">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`bg-blue-600 h-2 rounded-full transition-all duration-500 ${progressPercentage === 0 ? 'animate-pulse' : ''}`}
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default React.memo(StatusDisplay); // Performance optimization