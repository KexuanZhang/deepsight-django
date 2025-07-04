// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Custom hook focused solely on data fetching and caching

import { useState, useEffect, useCallback } from 'react';

export const useStudioData = (notebookId, studioService) => {
  const [reports, setReports] = useState([]);
  const [podcasts, setPodcasts] = useState([]);
  const [availableModels, setAvailableModels] = useState(null);
  const [loading, setLoading] = useState({
    reports: false,
    podcasts: false,
    models: false
  });
  const [errors, setErrors] = useState({
    reports: null,
    podcasts: null,
    models: null
  });

  // Single responsibility: Load reports
  const loadReports = useCallback(async () => {
    if (!notebookId) return;
    
    setLoading(prev => ({ ...prev, reports: true }));
    setErrors(prev => ({ ...prev, reports: null }));
    
    try {
      const data = await studioService.loadReports(notebookId);
      // Filter to only show completed reports
      const completedReports = data.filter(report => report.status === 'completed');
      setReports(completedReports);
    } catch (error) {
      setErrors(prev => ({ ...prev, reports: error.message }));
    } finally {
      setLoading(prev => ({ ...prev, reports: false }));
    }
  }, [notebookId, studioService]);

  // Single responsibility: Load podcasts  
  const loadPodcasts = useCallback(async () => {
    if (!notebookId) return;
    
    setLoading(prev => ({ ...prev, podcasts: true }));
    setErrors(prev => ({ ...prev, podcasts: null }));
    
    try {
      const data = await studioService.loadPodcasts(notebookId);
      // Filter to only show completed podcasts
      const completedPodcasts = data.filter(podcast => podcast.status === 'completed');
      setPodcasts(completedPodcasts);
    } catch (error) {
      setErrors(prev => ({ ...prev, podcasts: error.message }));
    } finally {
      setLoading(prev => ({ ...prev, podcasts: false }));
    }
  }, [notebookId, studioService]);

  // Single responsibility: Load available models
  const loadModels = useCallback(async () => {
    setLoading(prev => ({ ...prev, models: true }));
    setErrors(prev => ({ ...prev, models: null }));
    
    try {
      const data = await studioService.getAvailableModels();
      setAvailableModels(data);
    } catch (error) {
      setErrors(prev => ({ ...prev, models: error.message }));
    } finally {
      setLoading(prev => ({ ...prev, models: false }));
    }
  }, [studioService]);

  // Initialize data loading
  useEffect(() => {
    loadReports();
    loadPodcasts();
    loadModels();
  }, [loadReports, loadPodcasts, loadModels]);

  // Single responsibility: Add new report to state
  const addReport = useCallback((newReport) => {
    setReports(prev => [newReport, ...prev]);
  }, []);

  // Single responsibility: Add new podcast to state
  const addPodcast = useCallback((newPodcast) => {
    setPodcasts(prev => [newPodcast, ...prev]);
  }, []);

  // Single responsibility: Remove report from state
  const removeReport = useCallback((reportId) => {
    setReports(prev => prev.filter(report => report.id !== reportId));
  }, []);

  // Single responsibility: Remove podcast from state
  const removePodcast = useCallback((podcastId) => {
    setPodcasts(prev => prev.filter(podcast => podcast.id !== podcastId));
  }, []);

  return {
    // Data
    reports,
    podcasts, 
    availableModels,
    
    // Loading states
    loading,
    errors,
    
    // Actions
    loadReports,
    loadPodcasts,
    loadModels,
    addReport,
    addPodcast,
    removeReport,
    removePodcast
  };
};