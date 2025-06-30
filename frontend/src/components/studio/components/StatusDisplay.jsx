// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on displaying generation status

import React from 'react';
import { 
  CheckCircle, 
  AlertCircle, 
  X, 
  Loader2 
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GenerationState } from '../types';

// ====== OPEN/CLOSED PRINCIPLE (OCP) ======
// Status configurations that can be extended without modifying the component
const STATUS_CONFIGS = {
  [GenerationState.GENERATING]: {
    icon: Loader2,
    iconProps: { className: "h-5 w-5 animate-spin text-blue-600" },
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    getText: (title) => title
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

// ====== LISKOV SUBSTITUTION PRINCIPLE (LSP) ======
// Consistent interface that can be used in any status context
const StatusDisplay = ({ 
  state,
  title,
  progress,
  error,
  onCancel,
  showCancel = false
}) => {
  // Truncate long progress messages
  const formatProgress = (progress) => {
    if (!progress) return '';
    return progress.length > 60 ? progress.substring(0, 57) + '...' : progress;
  };

  // Get configuration for current state
  const config = STATUS_CONFIGS[state] || STATUS_CONFIGS[GenerationState.COMPLETED];
  const IconComponent = config.icon;
  const displayText = config.getText(title);
  const formattedProgress = formatProgress(progress);

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
          <Button
            variant="outline"
            size="sm"
            onClick={onCancel}
            className="text-red-600 border-red-300 hover:bg-red-50 hover:border-red-400"
          >
            <X className="mr-1 h-4 w-4" />
            Cancel
          </Button>
        )}
      </div>
      
      {state === GenerationState.GENERATING && (
        <div className="mt-3">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full animate-pulse transition-all duration-500" 
              style={{ width: '65%' }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default React.memo(StatusDisplay); // Performance optimization