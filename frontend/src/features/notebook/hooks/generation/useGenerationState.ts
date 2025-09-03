// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Custom hook focused solely on generation state management

import { useState, useCallback } from 'react';
import { GenerationState } from "@/features/notebook/components/studio/types";

export const useGenerationState = (initialConfig: Record<string, any> = {}) => {
  const [state, setState] = useState(GenerationState.IDLE);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState(initialConfig);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

  // Single responsibility: Start generation
  const startGeneration = useCallback((jobId: string) => {
    setState(GenerationState.GENERATING);
    setProgress('Starting generation...');
    setError(null);
    setCurrentJobId(jobId);
  }, []);

  // Single responsibility: Update progress
  const updateProgress = useCallback((progressMessage: string) => {
    setProgress(progressMessage);
  }, []);

  // Single responsibility: Complete generation
  const completeGeneration = useCallback(() => {
    setState(GenerationState.COMPLETED);
    setProgress('');
    setCurrentJobId(null);
  }, []);

  // Single responsibility: Fail generation  
  const failGeneration = useCallback((errorMessage: string) => {
    setState(GenerationState.FAILED);
    setError(errorMessage);
    setProgress('');
    setCurrentJobId(null);
  }, []);

  // Single responsibility: Cancel generation
  const cancelGeneration = useCallback(() => {
    setState(GenerationState.CANCELLED);
    setError('Cancelled by user');
    setProgress('');
    setCurrentJobId(null);
  }, []);

  // Single responsibility: Reset state
  const resetState = useCallback(() => {
    setState(GenerationState.IDLE);
    setProgress('');
    setError(null);
    setCurrentJobId(null);
  }, []);

  // Single responsibility: Update configuration
  const updateConfig = useCallback((updates: Record<string, any>) => {
    setConfig(prev => ({ ...prev, ...updates }));
  }, []);

  return {
    // State
    state,
    progress,
    error,
    config,
    currentJobId,
    
    // Computed state
    isGenerating: state === GenerationState.GENERATING,
    isCompleted: state === GenerationState.COMPLETED,
    isFailed: state === GenerationState.FAILED,
    isCancelled: state === GenerationState.CANCELLED,
    isIdle: state === GenerationState.IDLE,
    
    // Actions
    startGeneration,
    updateProgress,
    completeGeneration,
    failGeneration,
    cancelGeneration,
    resetState,
    updateConfig
  };
};