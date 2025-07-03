// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Custom hook focused solely on generation state management

import { useState, useCallback } from 'react';
import { GenerationState } from '@/features/notebook/components/studio/types';

export const useGenerationState = (initialConfig = {}) => {
  const [state, setState] = useState(GenerationState.IDLE);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState(null);
  const [config, setConfig] = useState(initialConfig);
  const [currentJobId, setCurrentJobId] = useState(null);

  // Single responsibility: Start generation
  const startGeneration = useCallback((jobId) => {
    setState(GenerationState.GENERATING);
    setProgress('');
    setError(null);
    setCurrentJobId(jobId);
  }, []);

  // Single responsibility: Update progress
  const updateProgress = useCallback((progressMessage) => {
    setProgress(progressMessage);
  }, []);

  // Single responsibility: Complete generation
  const completeGeneration = useCallback(() => {
    setState(GenerationState.COMPLETED);
    setProgress('');
    setCurrentJobId(null);
  }, []);

  // Single responsibility: Fail generation  
  const failGeneration = useCallback((errorMessage) => {
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
  const updateConfig = useCallback((updates) => {
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