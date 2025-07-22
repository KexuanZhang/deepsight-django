// ====== SOLID PRINCIPLES REFACTORED STUDIO PANEL ======
// This component demonstrates all 5 SOLID principles in action

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { RefreshCw, Maximize2, Minimize2, Settings, FileText, Play, Palette, ChevronDown, Trash2, Edit, Download, Save, X } from 'lucide-react';
import { Button } from '@/common/components/ui/button';
import { useToast } from '@/common/components/ui/use-toast';

// ====== DEPENDENCY INVERSION PRINCIPLE (DIP) ======
// Import service abstractions, not concrete implementations
import { ApiStudioService, LocalStorageJobService } from '@/features/notebook/services/StudioService';
import apiService from '@/common/utils/api';

// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Import focused custom hooks for specific concerns
import { config } from '@/config';
import { PANEL_HEADERS, COLORS } from "@/features/notebook/config/uiConfig";
import { useStudioData, useGenerationState, useJobStatus } from '@/features/notebook/hooks';

// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Import focused UI components
import ReportGenerationForm from './components/ReportGenerationForm';
import PodcastGenerationForm from './components/PodcastGenerationForm';
import PodcastAudioPlayer from './components/PodcastAudioPlayer';
import FileViewer from './components/FileViewer';

// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Import type definitions and prop creators
import { 
  StudioPanelProps,
  FileItem,
  SourceItem,
  ReportItem,
  PodcastItem,
  GenerationStateHook,
  CollapsedSections
} from './types';

// ====== DEPENDENCY INVERSION PRINCIPLE (DIP) ======
// Service instances - can be injected for testing
// Note: studioService will be created inside component with notebookId
const jobService = new LocalStorageJobService();

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
  const [collapsedSections, setCollapsedSections] = useState<CollapsedSections>({
    report: false,
    podcast: false,
    reports: false,
    podcasts: false
  });
  const [expandedPodcasts, setExpandedPodcasts] = useState<Set<string>>(new Set());


  // ====== SINGLE RESPONSIBILITY: File Selection State ======
  const [selectedFiles, setSelectedFiles] = useState<FileItem[]>([]);
  const [selectedSources, setSelectedSources] = useState<SourceItem[]>([]);

  // ====== DEPENDENCY INVERSION: Create service instance with notebookId ======
  const studioService = useMemo(() => new ApiStudioService(apiService, notebookId), [notebookId]);
  
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
      jobService.clearJob(reportGeneration.currentJobId);
    }
    toast({
      title: "Report Generated",
      description: "Your research report has been generated successfully."
    });
  }, [reportGeneration, studioData, toast]);

  // ====== SINGLE RESPONSIBILITY: Podcast generation completion ======
  const handlePodcastComplete = useCallback((result: PodcastItem) => {
    podcastGeneration.completeGeneration();
    studioData.addPodcast(result);
    if (podcastGeneration.currentJobId) {
      jobService.clearJob(podcastGeneration.currentJobId);
    }
    toast({
      title: "Podcast Generated", 
      description: "Your panel discussion has been generated successfully."
    });
  }, [podcastGeneration, studioData, toast]);

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
        const reports = await studioService.getReports();
        
        // Find running report jobs
        const runningReport = reports.find((report: any) => 
          report.status === 'running' || report.status === 'pending'
        );
        
        // Find running podcast jobs
        const podcasts = await studioService.getPodcasts();
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

      const response = await studioService.generateReport(config);
      reportGeneration.startGeneration(response.job_id);
      jobService.saveJob(response.job_id, { 
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

      const response = await studioService.generatePodcast(config);
      podcastGeneration.startGeneration(response.job_id);
      jobService.saveJob(response.job_id, { 
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
        jobService.clearJob(reportGeneration.currentJobId);
        toast({
          title: "Invalid Job",
          description: "Invalid job detected. Status has been reset.",
          variant: "destructive"
        });
        return;
      }
      
      try {
        await studioService.cancelGeneration(reportGeneration.currentJobId);
        
        // Don't set local state immediately - let SSE handle the status update
        jobService.clearJob(reportGeneration.currentJobId);
        
        toast({
          title: "Cancelled",
          description: "Report generation cancelled successfully."
        });
      } catch (error: unknown) {
        // Check if it's a 404 (job not found) - clean up state
        if ((error as any)?.response?.status === 404) {
          reportGeneration.cancelGeneration();
          jobService.clearJob(reportGeneration.currentJobId);
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
  }, [reportGeneration, studioService, jobService, toast]);

  const handleCancelPodcast = useCallback(async () => {
    if (podcastGeneration.currentJobId) {
      try {
        await studioService.cancelGeneration(podcastGeneration.currentJobId);
        // Don't set local state immediately - let SSE handle the status update
        // podcastGeneration.cancelGeneration();
        jobService.clearJob(podcastGeneration.currentJobId);
      } catch (error) {
        console.error('Failed to cancel podcast generation:', error);
        // Only set local state if API call failed
        podcastGeneration.failGeneration('Failed to cancel generation');
      }
    }
  }, [podcastGeneration]);

  // ====== SINGLE RESPONSIBILITY: UI toggle handlers ======
  const toggleSection = useCallback((section: keyof CollapsedSections) => {
    setCollapsedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  }, []);

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
      
      const content = await studioService.loadReportContent(reportId);
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
  }, [studioService, toast]);

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
      
      // Use apiService.downloadReportPdf directly instead of studioService.downloadFile
      // This ensures we're using the correct PDF download endpoint
      const blob = await apiService.downloadReportPdf(reportId, notebookId);
      
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
  }, [apiService, notebookId, toast]);

  const handleDownloadPodcast = useCallback(async (podcast: PodcastItem) => {
    try {
      const podcastId = podcast.id || podcast.job_id;
      if (!podcastId) {
        throw new Error('Podcast ID not found');
      }
      
      const filename = `${podcast.title || 'podcast'}.mp3`;
      // Note: This will need to be implemented in the service layer
      const blob = await (studioService as any).downloadPodcastAudio?.(podcastId, notebookId);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast({
        title: "Download Started",
        description: "Your podcast is being downloaded"
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
      const result = await apiService.deleteReport(reportId, notebookId);
      
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
      
      const result = await apiService.deletePodcast(podcastId, notebookId);
      
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
      await studioService.updateFile(fileId, content);
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
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
                    onClick={() => handleSaveFile(selectedFileContent)}
                  >
                    <Save className="h-3 w-3 mr-1" />
                    Save
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
                  onClick={() => handleDownloadReport(selectedFile)}
                >
                  <Download className="h-3 w-3 mr-1" />
                  Download
                </Button>
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
                    import('./components/AdvancedSettingsModal').then(({ default: AdvancedSettingsModal }) => {
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
      <div className={`flex-1 overflow-auto ${isReportPreview ? 'p-0' : 'p-6 space-y-6'} scrollbar-overlay`}>
        {!isReportPreview && (
          <>
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
            progress: podcastGeneration.progress ? parseInt(podcastGeneration.progress) || 0 : undefined,
            error: podcastGeneration.error || undefined
          }}
          onGenerate={handleGeneratePodcast}
          onCancel={handleCancelPodcast}
          selectedFiles={selectedFiles}
          selectedSources={selectedSources}
          onOpenModal={onOpenModal}
          onCloseModal={onCloseModal}
        />

        {/* ====== SEPARATOR BETWEEN PODCAST FORM AND REPORT LISTINGS ====== */}
        {studioData.reports.length > 0 && (
          <div className="px-6 py-2">
            <div className="border-t border-gray-200/60"></div>
          </div>
        )}

        {/* ====== INLINE REPORT LISTINGS ====== */}
        {studioData.reports.length > 0 && (
          <div className="px-6 py-4">
            <div className="space-y-3">
              {studioData.reports.map((report: ReportItem, index: number) => (
                <div
                  key={report.id || index}
                  className="p-4 bg-white hover:bg-gray-50 rounded-xl transition-all duration-200 cursor-pointer group border border-gray-200 hover:border-gray-300"
                  onClick={() => handleSelectReport(report)}
                >
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-sm flex-shrink-0 mt-1">
                      <FileText className="h-4 w-4 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-semibold text-gray-900 group-hover:text-blue-700 mb-2">
                        {report.title || 'Research Report'}
                      </h4>
                      <p className="text-xs text-gray-600 leading-relaxed mb-2">
                        {getReportPreview(report)}
                      </p>
                      <div className="flex items-center text-xs text-gray-500">
                        <span>{report.created_at ? new Date(report.created_at).toLocaleDateString() : 'Generated'}</span>
                        <span className="mx-2">•</span>
                        <span>Click to edit</span>
                      </div>
                    </div>
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-gray-400 hover:text-red-600 hover:bg-red-50"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteReport(report);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ====== SEPARATOR BETWEEN PODCAST FORM AND PODCAST LISTINGS ====== */}
        {studioData.podcasts.length > 0 && (
          <div className="px-6 py-2">
            <div className="border-t border-gray-200/60"></div>
          </div>
        )}

        {/* ====== INLINE PODCAST LISTINGS ====== */}
        {studioData.podcasts.length > 0 && (
          <div className="px-6 py-4">
            <div className="space-y-3">
              {studioData.podcasts.map((podcast: PodcastItem, index: number) => {
                const podcastId = podcast.id || podcast.job_id || index.toString();
                const isExpanded = expandedPodcasts.has(podcastId);
                
                return (
                  <div
                    key={podcastId}
                    className="bg-white rounded-xl border border-gray-200 hover:border-gray-300 transition-all duration-200 overflow-hidden"
                  >
                    {/* Podcast Header */}
                    <div
                      className="p-4 cursor-pointer hover:bg-gray-50 transition-colors duration-200 group"
                      onClick={() => handlePodcastClick(podcast)}
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
                          <h4 className="text-sm font-semibold text-gray-900 hover:text-purple-700">
                            {podcast.title || 'Panel Discussion'}
                          </h4>
                          <div className="flex items-center text-xs text-gray-500 mt-1">
                            <span>{podcast.created_at ? new Date(podcast.created_at).toLocaleDateString() : 'Generated'}</span>
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
                              handleDeletePodcast(podcast);
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
                          podcast={podcast}
                          onDownload={() => handleDownloadPodcast(podcast)}
                          onDelete={() => handleDeletePodcast(podcast)}
                          notebookId={notebookId}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
          </>
        )}
      </div>

      {/* ====== SINGLE RESPONSIBILITY: File viewer overlay ====== */}
      {selectedFile && (
        <FileViewer
          file={selectedFile}
          content={selectedFileContent}
          isExpanded={isStudioExpanded || false}
          viewMode={viewMode}
          onClose={handleCloseFile}
          onEdit={() => setViewMode('edit')}
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