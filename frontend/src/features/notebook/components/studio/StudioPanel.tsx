// ====== SOLID PRINCIPLES REFACTORED STUDIO PANEL ======
// This component demonstrates all 5 SOLID principles in action

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { RefreshCw, Maximize2, Minimize2, Settings, FileText, Play, Palette, ChevronDown, Trash2, Edit, Download, Save, X, Eye } from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import { useToast } from "@/shared/components/ui/use-toast";

// ====== DEPENDENCY INVERSION PRINCIPLE (DIP) ======
// Import service abstractions, not concrete implementations
import { jobStorage } from "@/features/notebook/utils/jobStorage";
import studioService from "@/features/notebook/services/StudioService";

// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Import focused custom hooks for specific concerns
import { config } from "@/config";
import { PANEL_HEADERS } from "@/features/notebook/config/uiConfig";
import { useStudioData, useGenerationState, useJobStatus } from "@/features/notebook/hooks";

// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Import focused UI components
import ReportGenerationForm from './ReportGenerationForm';
import PodcastGenerationForm from './PodcastGenerationForm';
import PodcastAudioPlayer from './PodcastAudioPlayer';
import FileViewer from './FileViewer';

// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Import type definitions and prop creators
import { 
  StudioPanelProps,
  FileItem,
  SourceItem,
  ReportItem,
  PodcastItem,
  GenerationStateHook
} from './types';

// ====== DEPENDENCY INVERSION PRINCIPLE (DIP) ======
// Service instances - can be injected for testing

// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Main container component focused on orchestration and state coordination
const StudioPanel: React.FC<StudioPanelProps> = ({ 
  notebookId, 
  sourcesListRef, 
  onSelectionChange,
  onOpenModal,
  onCloseModal,
  onToggleExpand,
  isStudioExpanded
}) => {
  const { toast } = useToast();

  // ====== SINGLE RESPONSIBILITY: UI State Management ======
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [selectedFileContent, setSelectedFileContent] = useState<string>('');
  const [viewMode, setViewMode] = useState<'preview' | 'edit'>('preview');
  const [isReportPreview, setIsReportPreview] = useState<boolean>(false);
  const [isPreviewingEdits, setIsPreviewingEdits] = useState<boolean>(false);
  const [expandedPodcasts, setExpandedPodcasts] = useState<Set<string>>(new Set());


  // ====== SINGLE RESPONSIBILITY: File Selection State ======
  const [selectedFiles, setSelectedFiles] = useState<FileItem[]>([]);
  const [selectedSources, setSelectedSources] = useState<SourceItem[]>([]);

  // ====== DEPENDENCY INVERSION: Use abstracted services ======
  const studioData = useStudioData(notebookId, studioService);

  // ====== SINGLE RESPONSIBILITY: Report generation state ======
  const reportGeneration: GenerationStateHook = useGenerationState({
    topic: '',
    article_title: '',
    model_provider: 'openai',
    retriever: 'searxng',
    prompt_type: 'general',
    include_image: false,
    include_domains: false,
    time_range: 'ALL',
    model: 'gpt-4'
  });

  // ====== SINGLE RESPONSIBILITY: Podcast generation state ======
  const podcastGeneration: GenerationStateHook = useGenerationState({
    title: '',
    description: '',
    topic: '',
    expert_names: {
      host: '杨飞飞',
      expert1: '奥立昆',
      expert2: '李特曼'
    },
    model: 'gpt-4'
  });

  // ====== SINGLE RESPONSIBILITY: Report generation completion ======
  const handleReportComplete = useCallback(() => {
    reportGeneration.completeGeneration();
    studioData.loadReports(); // Refresh the entire list to get updated titles
    if (reportGeneration.currentJobId) {
      jobStorage.clearJob(reportGeneration.currentJobId);
    }
    toast({
      title: "Report Generated",
      description: "Your research report has been generated successfully."
    });
  }, [reportGeneration, studioData, toast]);

  // ====== SINGLE RESPONSIBILITY: Podcast generation completion ======
  const handlePodcastComplete = useCallback(async (result: PodcastItem) => {
    podcastGeneration.completeGeneration();
    
    // Fetch complete podcast data from server to ensure we have audio URL
    try {
      const completeResult = { ...result };
      
      // If the result doesn't have an audio_url, try to fetch complete data
      if (!result.audio_url && result.job_id) {
        try {
          const freshPodcast = await studioService.getPodcastJobStatus(result.job_id, notebookId);
          Object.assign(completeResult, freshPodcast);
        } catch (error) {
          console.error('Failed to fetch complete podcast data:', error);
          // Still add the result we have, the PodcastAudioPlayer will handle retries
        }
      }
      
      studioData.addPodcast(completeResult);
    } catch (error) {
      console.error('Error in handlePodcastComplete:', error);
      // Fallback to original behavior
      studioData.addPodcast(result);
    }
    
    if (podcastGeneration.currentJobId) {
      jobStorage.clearJob(podcastGeneration.currentJobId);
    }
    toast({
      title: "Podcast Generated", 
      description: "Your panel discussion has been generated successfully."
    });
  }, [podcastGeneration, studioData, studioService, notebookId, toast]);

  // ====== SINGLE RESPONSIBILITY: Job status monitoring ======
  const handleReportError = useCallback((error: string) => {
    if (error === 'Job was cancelled') {
      reportGeneration.cancelGeneration();
    } else {
      reportGeneration.failGeneration(error);
    }
  }, [reportGeneration]);

  const handlePodcastError = useCallback((error: string) => {
    if (error === 'Job was cancelled') {
      podcastGeneration.cancelGeneration();
    } else {
      podcastGeneration.failGeneration(error);
    }
  }, [podcastGeneration]);

  const reportJobStatus = useJobStatus(
    reportGeneration.currentJobId,
    handleReportComplete,
    handleReportError,
    notebookId,
    'report'
  );

  const podcastJobStatus = useJobStatus(
    podcastGeneration.currentJobId,
    handlePodcastComplete,
    handlePodcastError,
    notebookId,
    'podcast'
  );

  // ====== SINGLE RESPONSIBILITY: Job recovery on page load ======
  useEffect(() => {
    const recoverRunningJobs = async () => {
      try {
        // Fetch current reports to check for running jobs
        const response = await studioService.listReportJobs(notebookId);
        const reports = response.jobs;
        
        // Find running report jobs
        const runningReport = reports.find((report: any) => 
          report.status === 'running' || report.status === 'pending'
        );
        
        // Find running podcast jobs
        const podcastResponse = await studioService.listPodcastJobs(notebookId);
        const podcasts = podcastResponse.jobs;
        const runningPodcast = podcasts.find((podcast: any) => 
          podcast.status === 'generating' || podcast.status === 'pending'
        );
        
        // Recover report job if found
        if (runningReport) {
          console.log('Recovering running report job:', runningReport.job_id);
          reportGeneration.startGeneration(runningReport.job_id);
          reportGeneration.updateProgress(runningReport.progress || 'Generating report...');
        }
        
        // Recover podcast job if found
        if (runningPodcast) {
          console.log('Recovering running podcast job:', runningPodcast.job_id);
          podcastGeneration.startGeneration(runningPodcast.job_id);
          podcastGeneration.updateProgress(runningPodcast.progress || 'Generating podcast...');
        }
      } catch (error) {
        console.error('Error recovering running jobs:', error);
      }
    };
    
    if (notebookId) {
      recoverRunningJobs();
    }
  }, [notebookId, studioService, reportGeneration, podcastGeneration]);

  // ====== SINGLE RESPONSIBILITY: Progress sync ======
  useEffect(() => {
    if (reportJobStatus.progress) {
      reportGeneration.updateProgress(reportJobStatus.progress);
    }
  }, [reportJobStatus.progress, reportGeneration.updateProgress]);

  useEffect(() => {
    if (podcastJobStatus.progress) {
      podcastGeneration.updateProgress(podcastJobStatus.progress);
    }
  }, [podcastJobStatus.progress, podcastGeneration.updateProgress]);

  // ====== SINGLE RESPONSIBILITY: Source selection sync ======
  useEffect(() => {
    if (sourcesListRef?.current) {
      const updateSelection = () => {
        const selected = sourcesListRef.current?.getSelectedFiles?.() || [];
        const sources = sourcesListRef.current?.getSelectedSources?.() || [];
        setSelectedFiles(selected);
        setSelectedSources(sources);
      };

      updateSelection();
      onSelectionChange?.(updateSelection);
    }
  }, [sourcesListRef, onSelectionChange]);

  // ====== SINGLE RESPONSIBILITY: Report generation handler ======
  const handleGenerateReport = useCallback(async (configOverrides?: Partial<any>) => {
    try {
      const config = {
        ...reportGeneration.config,
        ...configOverrides,
        notebook_id: notebookId,
        selected_files_paths: selectedFiles.map((f: FileItem) => f.id),
        model: configOverrides?.model || reportGeneration.config.model || 'gpt-4'
      };

      const response = await studioService.generateReport(config, notebookId);
      reportGeneration.startGeneration(response.job_id);
      jobStorage.saveJob(response.job_id, { 
        type: 'report', 
        config, 
        created_at: new Date().toISOString() 
      });

    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      reportGeneration.failGeneration(errorMessage);
      toast({
        title: "Generation Failed",
        description: errorMessage,
        variant: "destructive"
      });
    }
  }, [reportGeneration, notebookId, selectedFiles, toast]);

  // ====== SINGLE RESPONSIBILITY: Podcast generation handler ======
  const handleGeneratePodcast = useCallback(async (configOverrides?: Partial<any>) => {
    try {
      const config = {
        ...podcastGeneration.config,
        ...configOverrides,
        notebook_id: notebookId,
        source_file_ids: selectedFiles.map((f: FileItem) => f.id),
        model: configOverrides?.model || podcastGeneration.config.model || 'gpt-4'
      };

      // Convert config to FormData as expected by the API
      const formData = new FormData();
      Object.keys(config).forEach(key => {
        if (config[key] !== undefined && config[key] !== null) {
          if (Array.isArray(config[key])) {
            config[key].forEach((item: any) => {
              formData.append(key, item);
            });
          } else {
            formData.append(key, config[key]);
          }
        }
      });
      
      const response = await studioService.generatePodcast(formData, notebookId);
      podcastGeneration.startGeneration(response.job_id);
      podcastGeneration.updateProgress('Starting podcast generation (10%)');
      jobStorage.saveJob(response.job_id, { 
        type: 'podcast', 
        config, 
        created_at: new Date().toISOString() 
      });

    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      podcastGeneration.failGeneration(errorMessage);
      toast({
        title: "Generation Failed",
        description: errorMessage,
        variant: "destructive"
      });
    }
  }, [podcastGeneration, notebookId, selectedFiles, toast]);

  // ====== SINGLE RESPONSIBILITY: Cancellation handlers ======
  const handleCancelReport = useCallback(async () => {
    if (reportGeneration.currentJobId) {
      // Validate job ID is not empty or invalid
      if (reportGeneration.currentJobId.trim() === '') {
        reportGeneration.cancelGeneration();
        jobStorage.clearJob(reportGeneration.currentJobId);
        toast({
          title: "Invalid Job",
          description: "Invalid job detected. Status has been reset.",
          variant: "destructive"
        });
        return;
      }
      
      try {
        await studioService.cancelReportJob(reportGeneration.currentJobId, notebookId);
        
        // Don't set local state immediately - let SSE handle the status update
        jobStorage.clearJob(reportGeneration.currentJobId);
        
        toast({
          title: "Cancelled",
          description: "Report generation cancelled successfully."
        });
      } catch (error: unknown) {
        // Check if it's a 404 (job not found) - clean up state
        if ((error as any)?.response?.status === 404) {
          reportGeneration.cancelGeneration();
          jobStorage.clearJob(reportGeneration.currentJobId);
          toast({
            title: "Job Not Found",
            description: "Job no longer exists. Status has been reset.",
            variant: "destructive"
          });
        } else {
          // Only set local state if API call failed for other reasons
          reportGeneration.failGeneration('Failed to cancel generation');
          toast({
            title: "Cancel Failed",
            description: "Failed to cancel report generation. Please try again.",
            variant: "destructive"
          });
        }
      }
    } else {
      // If there's no job ID but we're in a generating state, reset the state
      if (reportGeneration.state === 'generating') {
        reportGeneration.cancelGeneration();
        toast({
          title: "Invalid State",
          description: "Invalid generation state detected. Status has been reset.",
          variant: "destructive"
        });
      }
    }
  }, [reportGeneration, jobStorage, toast]);

  const handleCancelPodcast = useCallback(async () => {
    if (podcastGeneration.currentJobId) {
      try {
        await studioService.cancelPodcastJob(podcastGeneration.currentJobId, notebookId);
        // Don't set local state immediately - let SSE handle the status update
        // podcastGeneration.cancelGeneration();
        jobStorage.clearJob(podcastGeneration.currentJobId);
      } catch (error) {
        console.error('Failed to cancel podcast generation:', error);
        // Only set local state if API call failed
        podcastGeneration.failGeneration('Failed to cancel generation');
      }
    }
  }, [podcastGeneration]);


  const toggleExpanded = useCallback(() => {
    if (onToggleExpand) {
      onToggleExpand();
    }
  }, [onToggleExpand]);

  const toggleViewMode = useCallback(() => {
    setViewMode(prev => prev === 'preview' ? 'edit' : 'preview');
  }, []);

  // ====== SINGLE RESPONSIBILITY: Data refresh ======
  const handleRefresh = useCallback(() => {
    studioData.loadReports();
    studioData.loadPodcasts();
    studioData.loadModels();
  }, [studioData]);

  // ====== SINGLE RESPONSIBILITY: File operations ======
  const handleSelectReport = useCallback(async (report: ReportItem) => {
    try {
      // Use job_id if id is not available, as API might return job_id instead of id
      const reportId = report.id || report.job_id;
      if (!reportId) {
        throw new Error('Report ID not found');
      }
      
      const content = await studioService.getReportContent(reportId, notebookId);
      setSelectedFile(report);
      setSelectedFileContent(content.content || content.markdown_content || '');
      setViewMode('preview');
      setIsReportPreview(true);
    } catch (error) {
      console.error('Failed to load report content:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Error",
        description: "Failed to load report content: " + errorMessage,
        variant: "destructive"
      });
    }
  }, [studioService, notebookId, toast]);

  const handlePodcastClick = useCallback((podcast: PodcastItem) => {
    const podcastId = podcast.id || podcast.job_id || '';
    setExpandedPodcasts(prev => {
      const newSet = new Set(prev);
      if (newSet.has(podcastId)) {
        newSet.delete(podcastId);
      } else {
        newSet.add(podcastId);
      }
      return newSet;
    });
  }, []);

  const getReportPreview = useCallback((report: ReportItem): string => {
    // Get a two-line preview from content or description
    const content = report.content || report.description || '';
    const lines = content.split('\n').filter((line: string) => line.trim());
    return lines.slice(0, 2).join(' ').substring(0, 120) + (content.length > 120 ? '...' : '');
  }, []);

  const handleDownloadReport = useCallback(async (report: ReportItem) => {
    try {
      const reportId = report.id || report.job_id;
      if (!reportId) {
        throw new Error('Report ID not found');
      }
      
      // Add a small delay to ensure any pending save operations complete
      // This prevents race conditions between save and download
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const filename = `${report.title || report.article_title || 'report'}.pdf`;
      
      // Use notebookService.downloadReportPdf directly instead of studioService.downloadFile
      // This ensures we're using the correct PDF download endpoint
      const blob = await studioService.downloadReportPdf(reportId, notebookId);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clean up the blob URL
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
      }, 1000);
      
      toast({
        title: "Download Started",
        description: "Your report is being downloaded as PDF"
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Download Failed", 
        description: errorMessage,
        variant: "destructive"
      });
    }
  }, [studioService, notebookId, toast]);

  const handleDownloadPodcast = useCallback(async (podcast: PodcastItem) => {
    try {
      const podcastId = podcast.id || podcast.job_id;
      if (!podcastId) {
        throw new Error('Podcast ID not found');
      }
      
      // Use the API service to download the podcast audio as a blob
      const blob = await studioService.downloadPodcastAudio(podcastId, notebookId);
      
      // Create download link and trigger download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${podcast.title || 'podcast'}.mp3`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clean up the blob URL
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
      }, 1000);
      
      toast({
        title: "Download Started",
        description: "Your podcast download should begin shortly"
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Download Failed",
        description: errorMessage, 
        variant: "destructive"
      });
    }
  }, [notebookId, toast]);

  const handleDeleteReport = useCallback(async (report: ReportItem) => {
    if (!confirm('Are you sure you want to delete this report?')) {
      return;
    }
    
    try {
      const reportId = report.id || report.job_id;
      if (!reportId) {
        throw new Error('Report ID not found');
      }
      
      // Delete from backend database using the proper API call
      const result = await studioService.deleteReport(reportId, notebookId);
      
      // Verify the deletion was successful by checking the response
      if (!result || (result.error && result.error !== null)) {
        throw new Error(result?.error || 'Backend deletion failed');
      }
      
      // Only remove from local state after confirming backend deletion succeeded
      studioData.removeReport(reportId);
      
      // Clear selected file if it's the one being deleted, without navigating to another file
      if (selectedFile?.id === reportId || selectedFile?.job_id === reportId) {
        setSelectedFile(null);
        setSelectedFileContent('');
      }
      
      toast({
        title: "Report Deleted",
        description: "The report has been deleted successfully"
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Delete Failed", 
        description: `Failed to delete report: ${errorMessage}`,
        variant: "destructive"
      });
    }
  }, [studioData, selectedFile, notebookId, toast]);

  const handleDeletePodcast = useCallback(async (podcast: PodcastItem) => {
    if (!confirm('Are you sure you want to delete this podcast?')) {
      return;
    }
    
    try {
      const podcastId = podcast.id || podcast.job_id;
      if (!podcastId) {
        throw new Error('Podcast ID not found');
      }
      
      const result = await studioService.deletePodcast(podcastId, notebookId);
      
      // Verify the deletion was successful by checking the response
      // For podcasts, successful deletion returns HTTP 204 (no content)
      if (result && result.error) {
        throw new Error(result.error || 'Backend deletion failed');
      }
      
      // Only remove from local state after confirming backend deletion succeeded
      studioData.removePodcast(podcastId);
      
      if (selectedFile?.id === podcastId || selectedFile?.job_id === podcastId) {
        setSelectedFile(null);
        setSelectedFileContent('');
      }
      
      toast({
        title: "Podcast Deleted",
        description: "The podcast has been deleted successfully"
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Delete Failed",
        description: `Failed to delete podcast: ${errorMessage}`,
        variant: "destructive"
      });
    }
  }, [studioData, selectedFile, notebookId, toast]);

  const handleSaveFile = useCallback(async (content: string) => {
    if (!selectedFile) return;
    
    try {
      // Use job_id if id is not available, as API expects job_id for reports
      const fileId = selectedFile.id || selectedFile.job_id;
      if (!fileId) {
        throw new Error('File ID not found');
      }
      
      console.log('Saving file:', { fileId, notebookId, contentLength: content.length });
      await studioService.updateReport(fileId, notebookId, content);
      setSelectedFileContent(content);
      
      // Refresh the report data to ensure it's synchronized
      studioData.loadReports();
      
      toast({
        title: "File Saved",
        description: "Your changes have been saved and synchronized"
      });
    } catch (error) {
      console.error('Save error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Save Failed",
        description: `Failed to save: ${errorMessage}`,
        variant: "destructive"
      });
    }
  }, [selectedFile, studioService, studioData, notebookId, toast]);

  const handleCloseFile = useCallback(() => {
    setSelectedFile(null);
    setSelectedFileContent('');
    setViewMode('preview');
    setIsReportPreview(false);
    setIsPreviewingEdits(false);
  }, []);

  const handlePreviewEdits = useCallback(() => {
    setIsPreviewingEdits(true);
    setViewMode('preview');
  }, []);

  // ====== OPEN/CLOSED PRINCIPLE (OCP) ======
  // Render method that can be extended without modification
  return (
    <div className="flex flex-col h-full">
      {/* ====== SINGLE RESPONSIBILITY: Header rendering ====== */}
      <div className={`${PANEL_HEADERS.container}`}>
        <div className={PANEL_HEADERS.layout}>
          <div className={PANEL_HEADERS.titleContainer}>
            <div className={PANEL_HEADERS.iconContainer}>
              <Palette className={PANEL_HEADERS.icon} />
            </div>
            <h3 className={PANEL_HEADERS.title}>
              {isReportPreview ? 'Studio/Report' : 'Studio'}
            </h3>
            {(reportGeneration.isGenerating || podcastGeneration.isGenerating) && (
              <div className="flex items-center space-x-2 text-sm text-red-600">
                <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse"></div>
                <span>Generating...</span>
              </div>
            )}
          </div>
          <div className={PANEL_HEADERS.actionsContainer}>
            {isReportPreview && selectedFile ? (
              // Report preview controls
              <>
                {viewMode === 'preview' && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
                    onClick={() => setViewMode('edit')}
                  >
                    <Edit className="h-3 w-3 mr-1" />
                    Edit
                  </Button>
                )}
                {viewMode === 'edit' && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-xs text-blue-600 hover:text-blue-800"
                      onClick={handlePreviewEdits}
                    >
                      <Eye className="h-3 w-3 mr-1" />
                      Preview
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
                      onClick={() => handleSaveFile(selectedFileContent)}
                    >
                      <Save className="h-3 w-3 mr-1" />
                      Save
                    </Button>
                  </>
                )}
                {viewMode === 'preview' && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
                    onClick={() => handleDownloadReport(selectedFile)}
                  >
                    <Download className="h-3 w-3 mr-1" />
                    Download
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 text-gray-400 hover:text-gray-600"
                  onClick={toggleExpanded}
                >
                  {isStudioExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 text-gray-400 hover:text-gray-600"
                  onClick={handleCloseFile}
                >
                  <X className="h-4 w-4" />
                </Button>
              </>
            ) : (
              // Default studio controls
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
                  onClick={handleRefresh}
                  disabled={studioData.loading.reports || studioData.loading.podcasts}
                >
                  <RefreshCw className={`h-3 w-3 mr-1 ${studioData.loading.reports || studioData.loading.podcasts ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
                  onClick={() => {
                    // Import AdvancedSettingsModal component dynamically
                    import('./AdvancedSettingsModal').then(({ default: AdvancedSettingsModal }) => {
                      const settingsContent = (
                        <AdvancedSettingsModal
                          isOpen={true}
                          onClose={() => onCloseModal('advancedSettings')}
                          reportConfig={reportGeneration.config}
                          podcastConfig={podcastGeneration.config}
                          onReportConfigChange={reportGeneration.updateConfig}
                          onPodcastConfigChange={podcastGeneration.updateConfig}
                          availableModels={studioData.availableModels || {}}
                        />
                      );
                      onOpenModal('advancedSettings', settingsContent);
                    });
                  }}
                  title="Advanced Settings"
                >
                  <Settings className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 text-gray-400 hover:text-gray-600"
                  onClick={toggleExpanded}
                >
                  {isStudioExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ====== SINGLE RESPONSIBILITY: Main content area ====== */}
      {!isReportPreview ? (
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* ====== FIXED SECTIONS: Generation Forms ====== */}
          <div className="flex-shrink-0 p-4 space-y-4 bg-gray-50/50 border-b border-gray-200/60">
            {/* ====== LISKOV SUBSTITUTION PRINCIPLE (LSP) ====== */}
            {/* Both forms follow the same interface contract */}
            
            <ReportGenerationForm
              config={reportGeneration.config}
              onConfigChange={reportGeneration.updateConfig}
              availableModels={studioData.availableModels || {}}
              generationState={{
                state: reportGeneration.state,
                progress: reportGeneration.progress,
                error: reportGeneration.error || undefined,
                isGenerating: reportGeneration.isGenerating
              }}
              onGenerate={handleGenerateReport}
              onCancel={handleCancelReport}
              selectedFiles={selectedFiles}
              onOpenModal={onOpenModal}
              onCloseModal={onCloseModal}
            />

            <PodcastGenerationForm
              config={podcastGeneration.config}
              onConfigChange={podcastGeneration.updateConfig}
              generationState={{
                state: podcastGeneration.state,
                progress: podcastGeneration.progress,
                error: podcastGeneration.error || undefined
              }}
              onGenerate={handleGeneratePodcast}
              onCancel={handleCancelPodcast}
              selectedFiles={selectedFiles}
              selectedSources={selectedSources}
              onOpenModal={onOpenModal}
              onCloseModal={onCloseModal}
            />
          </div>

          {/* ====== SCROLLABLE SECTION: Generated Files List ====== */}
          <div className="flex-1 overflow-auto scrollbar-overlay">
            {(studioData.reports.length > 0 || studioData.podcasts.length > 0) ? (() => {
              // Combine reports and podcasts into a unified list
              const allItems = [
                ...studioData.reports.map((report: ReportItem) => ({
                  ...report,
                  type: 'report',
                  created_at: report.created_at || new Date().toISOString()
                })),
                ...studioData.podcasts.map((podcast: PodcastItem) => ({
                  ...podcast,
                  type: 'podcast',
                  created_at: podcast.created_at || new Date().toISOString()
                }))
              ];

              // Sort by creation date, newest first
              allItems.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

              return (
                <div className="p-6">
                  <div className="space-y-3">
                    {allItems.map((item: any, index: number) => {
                      const itemId = item.id || item.job_id || index.toString();
                      
                      if (item.type === 'report') {
                        return (
                          <div
                            key={`report-${itemId}`}
                            className="p-4 bg-white hover:bg-gray-50 rounded-xl transition-all duration-200 cursor-pointer group border border-gray-200 hover:border-gray-300"
                            onClick={() => handleSelectReport(item)}
                          >
                            <div className="flex items-start space-x-3">
                              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-sm flex-shrink-0 mt-1">
                                <FileText className="h-4 w-4 text-white" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <h4 className="text-sm font-semibold text-gray-900 group-hover:text-blue-700 mb-2 truncate">
                                  {item.title || 'Research Report'}
                                </h4>
                                <p className="text-xs text-gray-600 leading-relaxed mb-2">
                                  {getReportPreview(item)}
                                </p>
                                <div className="flex items-center text-xs text-gray-500">
                                  <span>{new Date(item.created_at).toLocaleDateString()}</span>
                                  <span className="mx-2">•</span>
                                  <span>Report</span>
                                  <span className="mx-2">•</span>
                                  <span>Click to view</span>
                                </div>
                              </div>
                              <div className="opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0 text-gray-400 hover:text-red-600 hover:bg-red-50"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteReport(item);
                                  }}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          </div>
                        );
                      } else if (item.type === 'podcast') {
                        const isExpanded = expandedPodcasts.has(itemId);
                        
                        return (
                          <div
                            key={`podcast-${itemId}`}
                            className="bg-white rounded-xl border border-gray-200 hover:border-gray-300 transition-all duration-200 overflow-hidden"
                          >
                            {/* Podcast Header */}
                            <div
                              className="p-4 cursor-pointer hover:bg-gray-50 transition-colors duration-200 group"
                              onClick={() => handlePodcastClick(item)}
                            >
                              <div className="flex items-center space-x-3">
                                <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center shadow-sm flex-shrink-0">
                                  {isExpanded ? (
                                    <ChevronDown className="h-4 w-4 text-white" />
                                  ) : (
                                    <Play className="h-4 w-4 text-white" />
                                  )}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <h4 className="text-sm font-semibold text-gray-900 hover:text-purple-700 truncate">
                                    {item.title || 'Panel Discussion'}
                                  </h4>
                                  <div className="flex items-center text-xs text-gray-500 mt-1">
                                    <span>{new Date(item.created_at).toLocaleDateString()}</span>
                                    <span className="mx-2">•</span>
                                    <span>Podcast</span>
                                    <span className="mx-2">•</span>
                                    <span>Click to {isExpanded ? 'collapse' : 'play'}</span>
                                  </div>
                                </div>
                                <div className="flex-shrink-0 flex items-center space-x-2">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 w-8 p-0 text-gray-400 hover:text-red-600 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleDeletePodcast(item);
                                    }}
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                  <div className={`w-2 h-2 rounded-full transition-colors ${isExpanded ? 'bg-purple-400' : 'bg-gray-300'}`}></div>
                                </div>
                              </div>
                            </div>

                            {/* Expanded Audio Player */}
                            {isExpanded && (
                              <div className="border-t border-gray-100 p-4 bg-gray-50">
                                <PodcastAudioPlayer
                                  podcast={item}
                                  onDownload={() => handleDownloadPodcast(item)}
                                  onDelete={() => handleDeletePodcast(item)}
                                  notebookId={notebookId}
                                />
                              </div>
                            )}
                          </div>
                        );
                      }
                      return null;
                    })}
                  </div>
                </div>
              );
            })() : (
              <div className="flex-1 flex items-center justify-center p-8">
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
                    <FileText className="h-8 w-8 text-gray-400" />
                  </div>
                  <h3 className="text-sm font-medium text-gray-900 mb-1">No generated content yet</h3>
                  <p className="text-xs text-gray-500">Create a research report or podcast to see it here</p>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-auto p-0 scrollbar-overlay">
          {/* Report preview content when viewing a specific report */}
        </div>
      )}

      {/* ====== SINGLE RESPONSIBILITY: File viewer overlay ====== */}
      {selectedFile && (
        <FileViewer
          file={selectedFile}
          content={selectedFileContent}
          isExpanded={isStudioExpanded || false}
          viewMode={viewMode}
          onClose={handleCloseFile}
          onEdit={() => {
            setViewMode('edit');
            setIsPreviewingEdits(false);
          }}
          onSave={handleSaveFile}
          onDownload={selectedFile.audio_file ? 
            () => handleDownloadPodcast(selectedFile) : 
            () => handleDownloadReport(selectedFile)
          }
          onToggleExpand={toggleExpanded}
          onToggleViewMode={toggleViewMode}
          onContentChange={setSelectedFileContent}
          notebookId={notebookId}
          useMinIOUrls={config.USE_MINIO_URLS}
          hideHeader={isReportPreview}
          isPreviewingEdits={isPreviewingEdits}
        />
      )}


    </div>
  );
};

export default StudioPanel;

// ====== SUMMARY: SOLID PRINCIPLES IMPLEMENTATION ======
/*
1. SINGLE RESPONSIBILITY PRINCIPLE (SRP):
   - Each hook manages one specific concern (data, generation state, audio)
   - Each component has a single, well-defined purpose
   - Business logic separated from UI logic

2. OPEN/CLOSED PRINCIPLE (OCP):
   - Service abstraction allows new implementations without changing components
   - Status configurations can be extended without modifying StatusDisplay
   - Generation forms can be extended through props

3. LISKOV SUBSTITUTION PRINCIPLE (LSP):
   - All generation forms follow the same interface contract
   - Status components have consistent behavior regardless of state
   - Service implementations can be substituted seamlessly

4. INTERFACE SEGREGATION PRINCIPLE (ISP):
   - Props are focused and specific to each component's needs
   - No component receives props it doesn't use
   - Type definitions provide minimal, focused interfaces

5. DEPENDENCY INVERSION PRINCIPLE (DIP):
   - Components depend on abstract service interfaces
   - Concrete implementations are injected as dependencies
   - High-level components don't depend on low-level modules
*/