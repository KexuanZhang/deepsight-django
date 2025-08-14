// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Custom hook focused solely on data fetching and caching

import { useState, useEffect, useCallback } from 'react';

export const useStudioData = (notebookId: string, studioService: any) => {
  const [reports, setReports] = useState<any[]>([]);
  const [podcasts, setPodcasts] = useState<any[]>([]);
  const [availableModels, setAvailableModels] = useState<any>(null);
  const [loading, setLoading] = useState({
    reports: false,
    podcasts: false,
    models: false
  });
  const [errors, setErrors] = useState<{
    reports: string | null;
    podcasts: string | null;
    models: string | null;
  }>({
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
      const response = await studioService.listReportJobs(notebookId);
      const data = response.jobs;
      // Filter to only show completed reports
      const completedReports = data.filter((report: any) => report.status === 'completed');
      setReports(completedReports);
    } catch (error) {
      setErrors(prev => ({ ...prev, reports: error instanceof Error ? error.message : 'Unknown error' }));
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
      const response = await studioService.listPodcastJobs(notebookId);
      const data = response.jobs;
      // Filter to only show completed podcasts
      const completedPodcasts = data.filter((podcast: any) => podcast.status === 'completed');
      setPodcasts(completedPodcasts);
    } catch (error) {
      setErrors(prev => ({ ...prev, podcasts: error instanceof Error ? error.message : 'Unknown error' }));
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
      setErrors(prev => ({ ...prev, models: error instanceof Error ? error.message : 'Unknown error' }));
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
  const addReport = useCallback((newReport: any) => {
    setReports(prev => [newReport, ...prev]);
  }, []);

  // Single responsibility: Add new podcast to state
  const addPodcast = useCallback((newPodcast: any) => {
    setPodcasts(prev => [newPodcast, ...prev]);
  }, []);

  // Single responsibility: Remove report from state
  const removeReport = useCallback((reportId: string) => {
    setReports(prev => prev.filter((report: any) => 
      report.id !== reportId && report.job_id !== reportId
    ));
  }, []);

  // Single responsibility: Remove podcast from state
  const removePodcast = useCallback((podcastId: string) => {
    setPodcasts(prev => prev.filter((podcast: any) => 
      podcast.id !== podcastId && podcast.job_id !== podcastId
    ));
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