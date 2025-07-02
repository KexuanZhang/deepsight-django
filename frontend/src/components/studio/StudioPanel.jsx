// ====== SOLID PRINCIPLES REFACTORED STUDIO PANEL ======
// This component demonstrates all 5 SOLID principles in action

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { RefreshCw, Maximize2, Minimize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';

// ====== DEPENDENCY INVERSION PRINCIPLE (DIP) ======
// Import service abstractions, not concrete implementations
import { ApiStudioService, LocalStorageJobService } from './services/StudioService';
import apiService from '@/lib/api';

// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Import focused custom hooks for specific concerns
import { useStudioData } from './hooks/useStudioData';
import { useGenerationState } from './hooks/useGenerationState';
import { useJobStatus } from '@/hooks/useJobStatus';

// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Import focused UI components
import ReportGenerationForm from './components/ReportGenerationForm';
import PodcastGenerationForm from './components/PodcastGenerationForm';
import ReportListSection from './components/ReportListSection';
import PodcastListSection from './components/PodcastListSection';
import FileViewer from './components/FileViewer';

// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Import type definitions and prop creators
import { GenerationState, createStatusProps, createFileOperationProps } from './types';

// ====== DEPENDENCY INVERSION PRINCIPLE (DIP) ======
// Service instances - can be injected for testing
// Note: studioService will be created inside component with notebookId
const jobService = new LocalStorageJobService();

// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Main container component focused on orchestration and state coordination
const StudioPanel = ({ 
  notebookId, 
  sourcesListRef, 
  onSelectionChange 
}) => {
  const { toast } = useToast();

  // ====== SINGLE RESPONSIBILITY: UI State Management ======
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedFileContent, setSelectedFileContent] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [viewMode, setViewMode] = useState('preview'); // 'preview' or 'edit'
  const [collapsedSections, setCollapsedSections] = useState({
    report: false,
    podcast: false,
    reports: false,
    podcasts: false
  });

  // ====== SINGLE RESPONSIBILITY: File Selection State ======
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [selectedSources, setSelectedSources] = useState([]);

  // ====== DEPENDENCY INVERSION: Create service instance with notebookId ======
  const studioService = useMemo(() => new ApiStudioService(apiService, notebookId), [notebookId]);
  
  // ====== DEPENDENCY INVERSION: Use abstracted services ======
  const studioData = useStudioData(notebookId, studioService);

  // ====== SINGLE RESPONSIBILITY: Report generation state ======
  const reportGeneration = useGenerationState({
    topic: '',
    article_title: '',
    model_provider: 'openai',
    retriever: 'tavily'
  });

  // ====== SINGLE RESPONSIBILITY: Podcast generation state ======
  const podcastGeneration = useGenerationState({
    title: '',
    description: ''
  });

  // ====== SINGLE RESPONSIBILITY: Report generation completion ======
  const handleReportComplete = useCallback((result) => {
    reportGeneration.completeGeneration();
    studioData.addReport(result);
    jobService.clearJob(reportGeneration.currentJobId);
    toast({
      title: "Report Generated",
      description: "Your research report has been generated successfully."
    });
  }, [reportGeneration, studioData, toast]);

  // ====== SINGLE RESPONSIBILITY: Podcast generation completion ======
  const handlePodcastComplete = useCallback((result) => {
    podcastGeneration.completeGeneration();
    studioData.addPodcast(result);
    jobService.clearJob(podcastGeneration.currentJobId);
    toast({
      title: "Podcast Generated", 
      description: "Your panel discussion has been generated successfully."
    });
  }, [podcastGeneration, studioData, toast]);

  // ====== SINGLE RESPONSIBILITY: Job status monitoring ======
  const reportJobStatus = useJobStatus(
    reportGeneration.currentJobId,
    reportGeneration.updateProgress,
    handleReportComplete,
    reportGeneration.failGeneration
  );

  const podcastJobStatus = useJobStatus(
    podcastGeneration.currentJobId,
    podcastGeneration.updateProgress,
    handlePodcastComplete,
    podcastGeneration.failGeneration
  );

  // ====== SINGLE RESPONSIBILITY: Source selection sync ======
  useEffect(() => {
    if (sourcesListRef?.current) {
      const updateSelection = () => {
        const selected = sourcesListRef.current.getSelectedFiles?.() || [];
        const sources = sourcesListRef.current.getSelectedSources?.() || [];
        setSelectedFiles(selected);
        setSelectedSources(sources);
      };

      updateSelection();
      onSelectionChange?.(updateSelection);
    }
  }, [sourcesListRef, onSelectionChange]);

  // ====== SINGLE RESPONSIBILITY: Report generation handler ======
  const handleGenerateReport = useCallback(async () => {
    try {
      const config = {
        ...reportGeneration.config,
        notebook_id: notebookId,
        selected_files_paths: selectedFiles.map(f => f.id)
      };

      const response = await studioService.generateReport(config);
      reportGeneration.startGeneration(response.job_id);
      jobService.saveJob(response.job_id, { 
        type: 'report', 
        config, 
        created_at: new Date().toISOString() 
      });

    } catch (error) {
      reportGeneration.failGeneration(error.message);
      toast({
        title: "Generation Failed",
        description: error.message,
        variant: "destructive"
      });
    }
  }, [reportGeneration, notebookId, selectedFiles, toast]);

  // ====== SINGLE RESPONSIBILITY: Podcast generation handler ======
  const handleGeneratePodcast = useCallback(async () => {
    try {
      const config = {
        ...podcastGeneration.config,
        notebook_id: notebookId,
        selected_files: selectedFiles.map(f => f.id)
      };

      const response = await studioService.generatePodcast(config);
      podcastGeneration.startGeneration(response.job_id);
      jobService.saveJob(response.job_id, { 
        type: 'podcast', 
        config, 
        created_at: new Date().toISOString() 
      });

    } catch (error) {
      podcastGeneration.failGeneration(error.message);
      toast({
        title: "Generation Failed",
        description: error.message,
        variant: "destructive"
      });
    }
  }, [podcastGeneration, notebookId, selectedFiles, toast]);

  // ====== SINGLE RESPONSIBILITY: Cancellation handlers ======
  const handleCancelReport = useCallback(async () => {
    if (reportGeneration.currentJobId) {
      try {
        await studioService.cancelGeneration(reportGeneration.currentJobId);
        reportGeneration.cancelGeneration();
        jobService.clearJob(reportGeneration.currentJobId);
      } catch (error) {
        console.error('Failed to cancel report generation:', error);
      }
    }
  }, [reportGeneration]);

  const handleCancelPodcast = useCallback(async () => {
    if (podcastGeneration.currentJobId) {
      try {
        await studioService.cancelGeneration(podcastGeneration.currentJobId);
        podcastGeneration.cancelGeneration();
        jobService.clearJob(podcastGeneration.currentJobId);
      } catch (error) {
        console.error('Failed to cancel podcast generation:', error);
      }
    }
  }, [podcastGeneration]);

  // ====== SINGLE RESPONSIBILITY: UI toggle handlers ======
  const toggleSection = useCallback((section) => {
    setCollapsedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  }, []);

  const toggleExpanded = useCallback(() => {
    setIsExpanded(prev => !prev);
  }, []);

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
  const handleSelectReport = useCallback(async (report) => {
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
    } catch (error) {
      console.error('Failed to load report content:', error);
      toast({
        title: "Error",
        description: "Failed to load report content: " + error.message,
        variant: "destructive"
      });
    }
  }, [studioService, toast]);


  const handleDownloadReport = useCallback(async (report) => {
    try {
      const reportId = report.id || report.job_id;
      if (!reportId) {
        throw new Error('Report ID not found');
      }
      
      const filename = `${report.title || report.article_title || 'report'}.md`;
      await studioService.downloadFile(reportId, filename);
      toast({
        title: "Download Started",
        description: "Your report is being downloaded"
      });
    } catch (error) {
      toast({
        title: "Download Failed", 
        description: error.message,
        variant: "destructive"
      });
    }
  }, [studioService, toast]);

  const handleDownloadPodcast = useCallback(async (podcast) => {
    try {
      const podcastId = podcast.id || podcast.job_id;
      if (!podcastId) {
        throw new Error('Podcast ID not found');
      }
      
      const filename = `${podcast.title || 'podcast'}.mp3`;
      const blob = await studioService.api.downloadPodcastAudio(podcastId, notebookId);
      
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
      toast({
        title: "Download Failed",
        description: error.message, 
        variant: "destructive"
      });
    }
  }, [studioService, notebookId, toast]);

  const handleDeleteReport = useCallback(async (report) => {
    if (!confirm('Are you sure you want to delete this report?')) {
      return;
    }
    
    try {
      const reportId = report.id || report.job_id;
      if (!reportId) {
        throw new Error('Report ID not found');
      }
      
      // Delete from backend database using the proper API call
      await studioService.api.deleteReport(reportId, notebookId);
      studioData.removeReport(reportId);
      
      // Clear selected file if it's the one being deleted, without navigating to another file
      if (selectedFile?.id === reportId || selectedFile?.job_id === reportId) {
        setSelectedFile(null);
        setSelectedFileContent('');
      }
      
      toast({
        title: "Report Deleted",
        description: "The report has been deleted successfully from the database"
      });
    } catch (error) {
      toast({
        title: "Delete Failed",
        description: error.message,
        variant: "destructive"
      });
    }
  }, [studioService, studioData, selectedFile, notebookId, toast]);

  const handleDeletePodcast = useCallback(async (podcast) => {
    if (!confirm('Are you sure you want to delete this podcast?')) {
      return;
    }
    
    try {
      const podcastId = podcast.id || podcast.job_id;
      if (!podcastId) {
        throw new Error('Podcast ID not found');
      }
      
      await studioService.deleteFile(podcastId);
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
      toast({
        title: "Delete Failed",
        description: error.message,
        variant: "destructive"
      });
    }
  }, [studioService, studioData, selectedFile, toast]);

  const handleSaveFile = useCallback(async (content) => {
    if (!selectedFile) return;
    
    try {
      await studioService.updateFile(selectedFile.id, content);
      setSelectedFileContent(content);
      toast({
        title: "File Saved",
        description: "Your changes have been saved"
      });
    } catch (error) {
      toast({
        title: "Save Failed",
        description: error.message,
        variant: "destructive"
      });
    }
  }, [selectedFile, studioService, toast]);

  const handleCloseFile = useCallback(() => {
    setSelectedFile(null);
    setSelectedFileContent('');
    setViewMode('preview');
  }, []);

  // ====== OPEN/CLOSED PRINCIPLE (OCP) ======
  // Render method that can be extended without modification
  return (
    <div className={`flex flex-col h-full ${isExpanded ? 'fixed inset-0 z-50 bg-white' : ''}`}>
      {/* ====== SINGLE RESPONSIBILITY: Header rendering ====== */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center space-x-3">
          <h2 className="text-xl font-bold text-gray-900">Studio</h2>
          {(reportGeneration.isGenerating || podcastGeneration.isGenerating) && (
            <div className="flex items-center space-x-2 text-sm text-blue-600">
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
              <span>Generating...</span>
            </div>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={studioData.loading.reports || studioData.loading.podcasts}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${studioData.loading.reports || studioData.loading.podcasts ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={toggleExpanded}
          >
            {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* ====== SINGLE RESPONSIBILITY: Main content area ====== */}
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* ====== LISKOV SUBSTITUTION PRINCIPLE (LSP) ====== */}
        {/* Both forms follow the same interface contract */}
        
        <ReportGenerationForm
          config={reportGeneration.config}
          onConfigChange={reportGeneration.updateConfig}
          availableModels={studioData.availableModels}
          generationState={reportGeneration}
          onGenerate={handleGenerateReport}
          onCancel={handleCancelReport}
          isCollapsed={collapsedSections.report}
          onToggleCollapse={() => toggleSection('report')}
          selectedFiles={selectedFiles}
          onShowCustomize={() => {/* TODO: Implement customize modal */}}
        />

        <PodcastGenerationForm
          config={podcastGeneration.config}
          onConfigChange={podcastGeneration.updateConfig}
          generationState={podcastGeneration}
          onGenerate={handleGeneratePodcast}
          onCancel={handleCancelPodcast}
          isCollapsed={collapsedSections.podcast}
          onToggleCollapse={() => toggleSection('podcast')}
          selectedFiles={selectedFiles}
          selectedSources={selectedSources}
        />

        {/* ====== SINGLE RESPONSIBILITY: Report list rendering ====== */}
        <ReportListSection
          reports={studioData.reports}
          loading={studioData.loading.reports}
          error={studioData.errors.reports}
          isCollapsed={collapsedSections.reports}
          onToggleCollapse={() => toggleSection('reports')}
          onSelectReport={handleSelectReport}
          onDownloadReport={handleDownloadReport}
          onEditReport={handleSelectReport} // Same as select for now
          onDeleteReport={handleDeleteReport}
        />

        {/* ====== SINGLE RESPONSIBILITY: Podcast list rendering ====== */}
        <PodcastListSection
          podcasts={studioData.podcasts}
          loading={studioData.loading.podcasts}
          error={studioData.errors.podcasts}
          isCollapsed={collapsedSections.podcasts}
          onToggleCollapse={() => toggleSection('podcasts')}
          onDownloadPodcast={handleDownloadPodcast}
          onDeletePodcast={handleDeletePodcast}
          studioService={studioService}
        />
      </div>

      {/* ====== SINGLE RESPONSIBILITY: File viewer overlay ====== */}
      {selectedFile && (
        <FileViewer
          file={selectedFile}
          content={selectedFileContent}
          isExpanded={isExpanded}
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