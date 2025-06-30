import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Pause,
  Maximize2,
  Minimize2,
  Edit,
  Share2,
  FileText,
  Trash2,
  X,
  Plus,
  Settings,
  HelpCircle,
  MoreVertical,
  Download,
  CheckCircle,
  AlertCircle,
  Clock,
  Play,
  ChevronDown,
  ChevronUp,
  Loader2,
  Info,
  ChevronLeft,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github.css";
import apiService from "@/lib/api";
import { useJobStatus } from "@/hooks/useJobStatus";
import { Badge } from "@/components/ui/badge";
import { config } from "@/config";

// Utility function for formatting model names
const formatModelName = (value) => {
  return value.charAt(0).toUpperCase() + value.slice(1);
};

// Simplified Status Card Component - focused on user-friendly information
const StatusCard = ({ 
  title, 
  isGenerating, 
  progress, 
  error, 
  onCancel, 
  showCancel = false
}) => {
  // Keep progress messages simple and direct
  const getSimpleProgress = (progress) => {
    if (!progress) return '';
    
    // Just truncate if too long, otherwise show as-is
    return progress.length > 60 ? progress.substring(0, 57) + '...' : progress;
  };

  const getStatusInfo = () => {
    // Check error state first - this takes priority over progress
    if (error) {
      if (error === 'Cancelled' || error === 'Cancelled by user') {
        return {
          icon: <X className="h-5 w-5 text-amber-600" />,
          text: 'Cancelled',
          color: 'text-amber-600',
          bgColor: 'bg-amber-50',
          borderColor: 'border-amber-200'
        };
      }
      return {
        icon: <AlertCircle className="h-5 w-5 text-red-600" />,
        text: 'Failed',
        color: 'text-red-600',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200'
      };
    }
    
    if (isGenerating) {
      return {
        icon: <Loader2 className="h-5 w-5 animate-spin text-blue-600" />,
        text: title,
        color: 'text-blue-600',
        bgColor: 'bg-blue-50',
        borderColor: 'border-blue-200'
      };
    }
    
    return {
      icon: <CheckCircle className="h-5 w-5 text-green-600" />,
      text: 'Ready',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200'
    };
  };

  const status = getStatusInfo();
  const simpleProgress = getSimpleProgress(progress);

  return (
    <div className={`rounded-xl p-4 border ${status.borderColor} ${status.bgColor}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {status.icon}
          <div>
            <p className={`font-medium ${status.color}`}>{status.text}</p>
            {simpleProgress && (
              <p className="text-sm text-gray-600 mt-1">{simpleProgress}</p>
            )}
          </div>
        </div>
        
        {showCancel && isGenerating && (
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
      
      {isGenerating && (
        <div className="mt-3">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className="bg-blue-600 h-2 rounded-full animate-pulse transition-all duration-500" 
                 style={{ width: '65%' }}></div>
          </div>
        </div>
      )}
    </div>
  );
};

// Panel Discussion Generation Component
const PodcastGenerationSection = ({ 
  podcastGenerationState, 
  onGeneratePodcast, 
  isCollapsed, 
  onToggleCollapse,
  selectedFiles, // Now passed as prop instead of using ref
  selectedSources, // Now passed as prop instead of using ref
  onTitleChange,
  onDescriptionChange,
  onCancel,
  isConnected,
  connectionError
}) => {
  const hasSelectedFiles = selectedFiles.length > 0;

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm hover:shadow-md transition-all duration-200">
      <div 
        className="px-6 py-4 bg-gradient-to-r from-orange-50 to-amber-50 border-b border-orange-100 cursor-pointer hover:from-orange-100 hover:to-amber-100 transition-all duration-200 min-h-[72px]"
        onClick={onToggleCollapse}
      >
        <div className="flex items-center justify-between h-full">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-amber-500 rounded-lg flex items-center justify-center shadow-sm">
              <Play className="h-4 w-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Generate Panel Discussion</h3>
              <p className="text-xs text-gray-600">Create engaging AI-powered conversations</p>
            </div>
          </div>
          {isCollapsed ? <ChevronDown className="h-4 w-4 text-gray-500" /> : <ChevronUp className="h-4 w-4 text-gray-500" />}
        </div>
      </div>
      
      {!isCollapsed && (
        <div className="p-6 space-y-5">
          {(podcastGenerationState.isGenerating || podcastGenerationState.progress || podcastGenerationState.error) && (
            <StatusCard
              title="Generating Panel Discussion"
              isGenerating={podcastGenerationState.isGenerating}
              progress={podcastGenerationState.progress}
              error={podcastGenerationState.error}
              showCancel={true}
              onCancel={onCancel}
            />
          )}

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Panel Discussion Title
            </label>
            <input
              type="text"
              placeholder="Enter panel discussion title..."
              className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              value={podcastGenerationState.title || ""}
              onChange={(e) => onTitleChange(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Description (Optional)</label>
            <textarea
              placeholder="Enter panel discussion description..."
              className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              rows={3}
              value={podcastGenerationState.description || ""}
              onChange={(e) => onDescriptionChange(e.target.value)}
            />
          </div>

          <div className="bg-blue-50 p-3 rounded-lg">
            <p className="text-sm text-blue-700 flex items-center">
              <Info className="h-4 w-4 mr-2" />
              Select files from the Sources panel to generate a panel discussion between three experts: 杨飞飞 (host), 奥立昆, and 李特曼.
            </p>
          </div>

          {!hasSelectedFiles && (
            <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg">
              <p className="text-sm text-yellow-800 flex items-center font-medium">
                <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
                {selectedSources.length === 0 
                  ? "Please select at least one file from the Sources panel to generate a panel discussion."
                  : "Selected files are not ready for generation."
                }
              </p>
              <p className="text-xs text-yellow-700 mt-2 ml-6">
                {selectedSources.length === 0 
                  ? "Go to the Sources panel → Upload files or select existing files → Return here to generate"
                  : `You have ${selectedSources.length} file(s) selected, but they need to be fully parsed and completed before generation. Check the Sources panel for file status.`
                }
              </p>
              {selectedSources.length > 0 && (
                <div className="mt-2 ml-6">
                  <p className="text-xs text-yellow-700 font-medium">Selected files need to finish processing before generation.</p>
                </div>
              )}
            </div>
          )}

          <Button
            className={`w-full font-medium py-3 transition-all duration-200 ${
              !hasSelectedFiles && !podcastGenerationState.isGenerating
                ? 'bg-gray-400 hover:bg-gray-500 text-white cursor-not-allowed'
                : 'bg-gray-900 hover:bg-gray-800 text-white'
            }`}
            onClick={onGeneratePodcast}
            disabled={podcastGenerationState.isGenerating || !hasSelectedFiles}
            title={!hasSelectedFiles ? "Please select files from the Sources panel first" : "Generate panel discussion from selected files"}
          >
            {podcastGenerationState.isGenerating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating Panel Discussion...
              </>
            ) : !hasSelectedFiles ? (
              <>
                <AlertCircle className="mr-2 h-4 w-4" />
                Select Files to Generate
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Generate Panel Discussion
              </>
            )}
          </Button>


        </div>
      )}
    </div>
  );
};

// Report Configuration Section Component
const ReportConfigSection = ({ 
  reportConfig, 
  setReportConfig, 
  availableModels, 
  onGenerateReport, 
  onShowCustomize, 
  isGenerating, 
  selectedFiles, // Now passed as prop instead of using ref
  isCollapsed,
  onToggleCollapse,
  // Add these props for status display
  reportGenerationState,
  onCancel,
  isConnected,
  connectionError
}) => {
  // Check for valid input
  const hasTopic = reportConfig.topic.trim();
  const hasFiles = selectedFiles.length > 0;
  const hasValidInput = hasTopic || hasFiles;

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm hover:shadow-md transition-all duration-200">
      <div 
        className="px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-100 cursor-pointer hover:from-blue-100 hover:to-indigo-100 transition-all duration-200 min-h-[72px]"
        onClick={onToggleCollapse}
      >
        <div className="flex items-center justify-between h-full">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-sm">
              <FileText className="h-4 w-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Generate Research Report</h3>
              <p className="text-xs text-gray-600">Comprehensive AI-powered research analysis</p>
            </div>
          </div>
          {isCollapsed ? <ChevronDown className="h-4 w-4 text-gray-500" /> : <ChevronUp className="h-4 w-4 text-gray-500" />}
        </div>
      </div>

      {!isCollapsed && (
        <div className="p-6 space-y-5">
          {/* Report Generation Status */}
          {(reportGenerationState.isGenerating || reportGenerationState.progress || reportGenerationState.error) && (
            <StatusCard
              title="Generating Research Report"
              isGenerating={reportGenerationState.isGenerating}
              progress={reportGenerationState.progress}
              error={reportGenerationState.error}
              showCancel={true}
              onCancel={onCancel}
            />
          )}

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Research Topic
            </label>
            <input
              type="text"
              placeholder="Enter research topic (e.g., 'AI in healthcare')"
              className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={reportConfig.topic}
              onChange={(e) => setReportConfig(prev => ({ ...prev, topic: e.target.value }))}
            />
            <p className="text-xs text-gray-500 flex items-center">
              <Info className="h-3 w-3 mr-1" />
              You can also upload PDF, transcript, or paper files in the Sources panel for analysis.
            </p>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Report Title</label>
            <input
              type="text"
              placeholder="Enter report title..."
              className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={reportConfig.article_title}
              onChange={(e) => setReportConfig(prev => ({ ...prev, article_title: e.target.value }))}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">AI Model</label>
              <select
                className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={reportConfig.model_provider}
                onChange={(e) => setReportConfig(prev => ({ ...prev, model_provider: e.target.value }))}
              >
                {(availableModels?.model_providers || []).map(provider => (
                  <option key={provider} value={provider}>{formatModelName(provider)}</option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">Search Engine</label>
              <select
                className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={reportConfig.retriever}
                onChange={(e) => setReportConfig(prev => ({ ...prev, retriever: e.target.value }))}
              >
                {(availableModels?.retrievers || []).map(retriever => (
                  <option key={retriever} value={retriever}>{formatModelName(retriever)}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Advanced Settings Button */}
          <div className="flex justify-center">
            <Button
              variant="outline"
              size="sm"
              onClick={onShowCustomize}
              className="text-sm border-blue-200 text-blue-700 hover:bg-blue-50 hover:border-blue-300 transition-all duration-200"
            >
              <Settings className="mr-2 h-4 w-4" />
              Advanced Settings
            </Button>
          </div>

          <Button
            className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white font-medium py-3 shadow-lg hover:shadow-xl transition-all duration-200"
            onClick={onGenerateReport}
            disabled={isGenerating || !hasValidInput}
          >
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating Report...
              </>
            ) : (
              <>
                <Plus className="mr-2 h-4 w-4" />
                Generate Report
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
};

// Memoized file list item component
const FileListItem = React.memo(({ file, isSelected, onFileClick, onDownload, onMenuToggle, isMenuOpen, onEdit, onDelete }) => (
  <div className="p-4 hover:bg-gray-50 transition-colors">
    <div
      className="flex items-center justify-between cursor-pointer"
      onClick={() => onFileClick(file)}
    >
      <div className="flex items-center space-x-3 flex-1 min-w-0">
        <div className="flex-shrink-0">
          <FileText className="h-5 w-5 text-blue-500" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {file.name}
          </p>
          {file.createdAt && (
            <p className="text-xs text-gray-500">
              {new Date(file.createdAt).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>
      
      <div className="flex items-center space-x-1">
        {file.jobId && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDownload(file);
            }}
            className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
            title="Download"
          >
            <Download className="w-4 h-4" />
          </button>
        )}
        <div className="relative">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onMenuToggle(file.id);
            }}
            className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
            data-menu-id={file.id}
          >
            <MoreVertical className="w-4 h-4" />
          </button>
          {isMenuOpen && (
            <div className="absolute right-0 top-8 w-48 bg-white border rounded-lg shadow-xl z-50 overflow-hidden border-gray-200">
              <button
                className="w-full px-4 py-3 text-sm flex items-center gap-3 hover:bg-gray-50 text-gray-700 transition-colors"
                onClick={() => onEdit(file)}
              >
                <Edit className="w-4 h-4" />
                <span>Edit Report</span>
              </button>
              <div className="border-t border-gray-100" />
              <button
                className="w-full px-4 py-3 text-sm flex items-center gap-3 text-red-600 hover:bg-red-50 transition-colors"
                onClick={() => onDelete(file.id)}
              >
                <Trash2 className="w-4 h-4" />
                <span>Delete Report</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  </div>
));

// Memoized podcast list item component
const PodcastListItem = React.memo(({ podcast, onDownload, onMenuToggle, isMenuOpen, onDelete, audioBlob, isLoading }) => (
  <div className="p-4 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0">
    {/* Header */}
    <div className="flex items-start justify-between mb-3">
      <div className="flex items-start space-x-3 flex-1 min-w-0">
        <div className="flex-shrink-0 mt-1">
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin text-orange-500" />
          ) : (
            <Play className="h-5 w-5 text-orange-500" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-gray-900 truncate">
            {podcast.title}
          </h4>
          {podcast.description && (
            <p className="text-xs text-gray-600 truncate mt-1">
              {podcast.description}
            </p>
          )}
          <div className="flex items-center space-x-3 mt-2">
            {podcast.createdAt && (
              <span className="text-xs text-gray-500">
                {new Date(podcast.createdAt).toLocaleDateString()}
              </span>
            )}
            <span className="text-xs text-gray-500">MP3</span>
          </div>
        </div>
      </div>
      
      <div className="flex items-center space-x-1 ml-3">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDownload(podcast);
          }}
          className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
          title="Download"
        >
          <Download className="w-4 h-4" />
        </button>
        <div className="relative">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onMenuToggle(podcast.id);
            }}
            className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <MoreVertical className="w-4 h-4" />
          </button>
          {isMenuOpen && (
            <div className="absolute right-0 top-8 w-48 bg-white border rounded-lg shadow-xl z-50 overflow-hidden border-gray-200">
              <button
                className="w-full px-4 py-3 text-sm flex items-center gap-3 text-red-600 hover:bg-red-50 transition-colors"
                onClick={() => onDelete(podcast.id)}
              >
                <Trash2 className="w-4 h-4" />
                <span>Delete Podcast</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
    
    {/* Audio Player - Always visible when loaded */}
    {audioBlob && (
      <div className="mt-2">
        <audio 
          controls 
          className="w-full rounded-md" 
          preload="metadata"
          controlsList="nodownload"
          style={{ height: '40px' }}
        >
          <source src={audioBlob} type="audio/mpeg" />
          Your browser does not support the audio element.
        </audio>
      </div>
    )}
    
    {/* Loading indicator */}
    {isLoading && (
      <div className="mt-2">
        <div className="flex items-center p-3 bg-orange-50 rounded-lg border border-orange-200">
          <Loader2 className="h-4 w-4 animate-spin text-orange-500 mr-2" />
          <span className="text-sm text-orange-700">Loading audio player...</span>
        </div>
      </div>
    )}
  </div>
));

// Memoized markdown content component
const MarkdownContent = React.memo(({ content }) => (
  <div className="prose prose-gray max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900">
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        h1: ({children}) => <h1 className="text-3xl font-bold text-gray-900 mb-6 pb-3 border-b">{children}</h1>,
        h2: ({children}) => <h2 className="text-2xl font-semibold text-gray-800 mt-8 mb-4">{children}</h2>,
        h3: ({children}) => <h3 className="text-xl font-medium text-gray-800 mt-6 mb-3">{children}</h3>,
        p: ({children}) => <p className="text-gray-700 leading-relaxed mb-4">{children}</p>,
        ul: ({children}) => <ul className="list-disc pl-6 mb-4 space-y-2">{children}</ul>,
        ol: ({children}) => <ol className="list-decimal pl-6 mb-4 space-y-2">{children}</ol>,
        li: ({children}) => <li className="text-gray-700">{children}</li>,
        blockquote: ({children}) => <blockquote className="border-l-4 border-blue-200 pl-4 italic text-gray-600 my-4">{children}</blockquote>,
        code: ({children}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono text-gray-800">{children}</code>,
        pre: ({children}) => <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto my-4">{children}</pre>,
      }}
    >
      {content}
    </ReactMarkdown>
  </div>
));

// Main StudioPanel Component
const StudioPanel = ({ notebookId, sourcesListRef, onSelectionChange }) => {
  // UI State
  const [files, setFiles] = useState([]);
  const [podcastFiles, setPodcastFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeMenuFileId, setActiveMenuFileId] = useState(null);
  const [viewMode, setViewMode] = useState("preview");
  const [isEditing, setIsEditing] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState("");
  const [showCustomizeReport, setShowCustomizeReport] = useState(false);
  
  // State for selected files from Sources panel
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [selectedSources, setSelectedSources] = useState([]);
  
  // State for audio playback
  const [audioBlobs, setAudioBlobs] = useState(new Map()); // Map of podcast.id -> blob URL
  const [loadingAudio, setLoadingAudio] = useState(new Set()); // Set of podcast.id being loaded
  
  // Function to update selected files when Sources panel selection changes
  const updateSelectedFiles = useCallback(() => {
    if (sourcesListRef?.current) {
      const newSelectedFiles = sourcesListRef.current.getSelectedFiles() || [];
      const newSelectedSources = sourcesListRef.current.getSelectedSources() || [];
      setSelectedFiles(newSelectedFiles);
      setSelectedSources(newSelectedSources);
      // console.log("studio files", selectedFiles)
    }
  }, [sourcesListRef]);
  
  // Register callback with parent component only once
  useEffect(() => {
    if (onSelectionChange) {
      onSelectionChange(updateSelectedFiles);
    }
  }, [onSelectionChange, updateSelectedFiles]);
  
  // Initial load with a small delay to avoid race conditions
  useEffect(() => {
    const timer = setTimeout(() => {
      updateSelectedFiles();
    }, 200);
    
    return () => clearTimeout(timer);
  }, []); // Empty dependency array for one-time initial load
  
  // Collapsible sections state
  const [collapsedSections, setCollapsedSections] = useState({
    podcast: true,
    report: true,
    podcastList: true,
    reportList: true,
  });

  // Report generation state
  const [reportGenerationState, setReportGenerationState] = useState({
    isGenerating: false,
    currentJobId: null,
    progress: '',
    error: null,
  });
  
  // Available models state
  const [availableModels, setAvailableModels] = useState({
    model_providers: ['openai', 'google'],
    retrievers: ['tavily', 'brave', 'serper', 'you', 'bing', 'duckduckgo', 'searxng'],
    time_ranges: ['day', 'week', 'month', 'year'],
  });

  // Report configuration state
  const [reportConfig, setReportConfig] = useState({
    topic: '',
    article_title: 'Research Report',
    model_provider: 'openai',
    retriever: 'tavily',
    temperature: 0.2,
    top_p: 0.4,
    max_conv_turn: 3,
    max_perspective: 3,
    search_top_k: 10,
    do_research: true,
    do_generate_outline: true,
    do_generate_article: true,
    do_polish_article: true,
    remove_duplicate: true,
    post_processing: true,
  });

  // Podcast generation state
  const [podcastGenerationState, setPodcastGenerationState] = useState({
    isGenerating: false,
    jobId: null,
    progress: '',
    error: null,
    title: '',
    description: '',
  });

  const { toast } = useToast();

  // Persistent job tracking helpers
  const saveJobToStorage = useCallback((jobId, jobType, jobData) => {
    try {
      const storageKey = `activeJob_${notebookId}_${jobType}`;
      const jobInfo = {
        jobId,
        jobType,
        notebookId,
        startTime: Date.now(),
        ...jobData
      };
      localStorage.setItem(storageKey, JSON.stringify(jobInfo));
      console.log(`Saved ${jobType} job to storage:`, jobInfo);
    } catch (error) {
      console.error('Error saving job to storage:', error);
    }
  }, [notebookId]);

  const getJobFromStorage = useCallback((jobType) => {
    try {
      const storageKey = `activeJob_${notebookId}_${jobType}`;
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const jobInfo = JSON.parse(stored);
        // Check if job is not too old (2 hours max)
        const maxAge = 2 * 60 * 60 * 1000;
        if (Date.now() - jobInfo.startTime < maxAge) {
          console.log(`Retrieved ${jobType} job from storage:`, jobInfo);
          return jobInfo;
        } else {
          console.log(`Stored ${jobType} job is too old, removing`);
          localStorage.removeItem(storageKey);
        }
      }
    } catch (error) {
      console.error('Error retrieving job from storage:', error);
    }
    return null;
  }, [notebookId]);

  const clearJobFromStorage = useCallback((jobType) => {
    try {
      const storageKey = `activeJob_${notebookId}_${jobType}`;
      localStorage.removeItem(storageKey);
      console.log(`Cleared ${jobType} job from storage`);
    } catch (error) {
      console.error('Error clearing job from storage:', error);
    }
  }, [notebookId]);

  // Memoized helper functions
  const toggleSection = useCallback((section) => {
    setCollapsedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  }, []);

  // Load available models and existing reports on component mount
  useEffect(() => {
    loadAvailableModels();
    loadExistingReports();
    loadExistingPodcasts();
  }, []);

  // Enhanced job restoration on component mount
  useEffect(() => {
    const restoreJobsFromStorage = async () => {
      console.log('Attempting to restore jobs from storage...');
      
      // Try to restore report generation state
      const savedReportJob = getJobFromStorage('report');
      if (savedReportJob && savedReportJob.jobId) {
        console.log('Found saved report job, attempting to restore:', savedReportJob);
        
        // Verify job status by checking with backend
        try {
          const response = await apiService.listReportJobs(notebookId, 50);
          const activeJob = response?.jobs?.find(job => job.job_id === savedReportJob.jobId);
          
          if (activeJob) {
            if (activeJob.status === 'cancelled') {
              console.log('Found cancelled report job, restoring cancelled state:', activeJob);
              setReportGenerationState({
                isGenerating: false,
                currentJobId: savedReportJob.jobId,
                progress: '',
                error: 'Cancelled',
              });
            } else if (activeJob.status === 'running' || activeJob.status === 'pending') {
              console.log('Verified job is still running, restoring state:', activeJob);
              setReportGenerationState({
                isGenerating: true,
                currentJobId: savedReportJob.jobId,
                progress: 'Reconnected to ongoing report generation...',
                error: null,
              });
            } else {
              console.log('Job completed or failed, clearing from storage');
              clearJobFromStorage('report');
            }
          } else {
            console.log('Job not found, clearing from storage');
            clearJobFromStorage('report');
          }
        } catch (error) {
          console.error('Error verifying report job status:', error);
          // Keep the stored job info but mark as potentially stale
          setReportGenerationState({
            isGenerating: true,
            currentJobId: savedReportJob.jobId,
            progress: 'Reconnecting to report generation...',
            error: null,
          });
        }
      }
      
      // Try to restore podcast generation state
      const savedPodcastJob = getJobFromStorage('podcast');
      if (savedPodcastJob && savedPodcastJob.jobId) {
        console.log('Found saved podcast job, attempting to restore:', savedPodcastJob);
        
        try {
          const response = await apiService.listPodcastJobs(notebookId);
          const activeJob = response?.jobs?.find(job => job.job_id === savedPodcastJob.jobId);
          
          if (activeJob) {
            if (activeJob.status === 'cancelled') {
              console.log('Found cancelled podcast job, restoring cancelled state:', activeJob);
              setPodcastGenerationState({
                isGenerating: false,
                jobId: savedPodcastJob.jobId,
                progress: '',
                error: 'Cancelled',
                title: savedPodcastJob.title || '',
                description: savedPodcastJob.description || '',
              });
            } else if (activeJob.status === 'generating' || activeJob.status === 'pending') {
              console.log('Verified podcast job is still running, restoring state:', activeJob);
              setPodcastGenerationState({
                isGenerating: true,
                jobId: savedPodcastJob.jobId,
                progress: 'Reconnected to ongoing panel discussion generation...',
                error: null,
                title: savedPodcastJob.title || '',
                description: savedPodcastJob.description || '',
              });
            } else {
              console.log('Podcast job completed or failed, clearing from storage');
              clearJobFromStorage('podcast');
            }
          } else {
            console.log('Podcast job not found, clearing from storage');
            clearJobFromStorage('podcast');
          }
        } catch (error) {
          console.error('Error verifying podcast job status:', error);
          setPodcastGenerationState({
            isGenerating: true,
            jobId: savedPodcastJob.jobId,
            progress: 'Reconnecting to panel discussion generation...',
            error: null,
            title: savedPodcastJob.title || '',
            description: savedPodcastJob.description || '',
          });
        }
      }
    };

    // Run restoration after a short delay to allow other effects to complete
    const timeoutId = setTimeout(restoreJobsFromStorage, 500);
    return () => clearTimeout(timeoutId);
  }, [getJobFromStorage, clearJobFromStorage, notebookId]);

  // Cleanup blob URLs when component unmounts
  useEffect(() => {
    return () => {
      // Clean up all blob URLs
      audioBlobs.forEach((blobUrl) => {
        window.URL.revokeObjectURL(blobUrl);
      });
    };
  }, []);

  // Auto-load audio for new podcasts
  useEffect(() => {
    podcastFiles.forEach(podcast => {
      if (podcast.jobId && 
          !audioBlobs.has(podcast.id) && 
          !loadingAudio.has(podcast.id)) {
        // Auto-load this podcast's audio
        handlePlayPodcast(podcast);
      }
    });
  }, [podcastFiles]);

  // Clean up blob URLs for deleted podcasts
  useEffect(() => {
    const currentPodcastIds = new Set(podcastFiles.map(p => p.id));
    const blobsToCleanup = [];
    
    audioBlobs.forEach((blobUrl, podcastId) => {
      if (!currentPodcastIds.has(podcastId)) {
        blobsToCleanup.push(podcastId);
        window.URL.revokeObjectURL(blobUrl);
      }
    });
    
    if (blobsToCleanup.length > 0) {
      setAudioBlobs(prev => {
        const newMap = new Map(prev);
        blobsToCleanup.forEach(id => newMap.delete(id));
        return newMap;
      });
    }
  }, [podcastFiles, audioBlobs]);

  // Real-time job status monitoring using SSE for reports (unified with podcast approach)
  const { 
    status: jobStatus, 
    progress: jobProgress, 
    result: jobResult, 
    error: jobError, 
    isConnected,
    connectionError,
    cancel: reportCancelJob,
    disconnect: reportDisconnect,
  } = useJobStatus(
    reportGenerationState.currentJobId,
    // onComplete callback
    async (result) => {
        if (result && result.generated_files) {
            await loadGeneratedReport(result);
        }
        toast({
            title: "Report Generated",
            description: "Your research report has been generated successfully!",
        });
        setTimeout(() => handleClearReportStatus(), 3000);
    },
    // onError callback
    (error) => {
        const isCancellation = typeof error === 'string' && (error.includes('cancelled') || error.includes('Cancelled'));
        if (!isCancellation) {
            toast({
                title: "Generation Failed",
                description: error || "Report generation failed. Please try again.",
                variant: "destructive",
            });
        }
        setTimeout(() => handleClearReportStatus(), isCancellation ? 0 : 5000);
    },
    // Pass notebookId and specify this is for report jobs
    notebookId,
    'report'
  );



  const handleClearReportStatus = useCallback(() => {
    setReportGenerationState({
        isGenerating: false,
        currentJobId: null,
        progress: '',
        error: null,
    });
    // Clear the job from persistent storage
    clearJobFromStorage('report');
  }, [clearJobFromStorage]);

  // Effect to handle report job results and errors
  useEffect(() => {
    const currentJobId = reportGenerationState.currentJobId;
    
    if (currentJobId) {
      if (jobStatus) {
        setReportGenerationState(prev => {
          if (prev.currentJobId !== currentJobId) return prev;
          
          const isGenerating = jobStatus === 'running' || jobStatus === 'pending';
          const isCancelled = jobStatus === 'cancelled';
          const isCompleted = jobStatus === 'completed';
          
          return {
            ...prev,
            isGenerating: isGenerating && !isCompleted && !isCancelled,
            progress: isCancelled ? '' : prev.progress,
            error: isCancelled ? 'Cancelled' : (jobError || prev.error),
          };
        });
      }
      
      if (jobProgress) {
        setReportGenerationState(prev => 
          prev.currentJobId === currentJobId ? { ...prev, progress: jobProgress } : prev
        );
      }
      
      if (jobError && jobError !== 'Cancelled') {
        setReportGenerationState(prev => 
          prev.currentJobId === currentJobId ? { ...prev, error: jobError } : prev
        );
      }
    }
  }, [jobStatus, jobProgress, jobError, reportGenerationState.currentJobId]);

  // Effect to handle connection errors and clear stale state
  useEffect(() => {
    if (connectionError && reportGenerationState.currentJobId) {
      // If we have persistent connection errors, the job might be stale
      const timeoutId = setTimeout(() => {
        if (connectionError && !isConnected) {
          console.log('Clearing report state due to persistent connection error:', connectionError);
          handleClearReportStatus();
        }
      }, 5000); // Wait 5 seconds before clearing due to connection error

      return () => clearTimeout(timeoutId);
    }
  }, [connectionError, isConnected, reportGenerationState.currentJobId, handleClearReportStatus]);

  const handleClearPodcastStatus = useCallback(() => {
    setPodcastGenerationState({
      isGenerating: false,
      jobId: null,
      progress: '',
      error: null,
      title: '',
      description: '',
    });
    // Clear the job from persistent storage
    clearJobFromStorage('podcast');
  }, [clearJobFromStorage]);

  // Real-time job status monitoring using SSE for podcasts
  const { 
    status: podcastJobStatus, 
    progress: podcastJobProgress, 
    result: podcastJobResult, 
    error: podcastJobError, 
    isConnected: podcastIsConnected,
    connectionError: podcastConnectionError,
    cancel: podcastCancelJob
  } = useJobStatus(
    podcastGenerationState.jobId,
    // onComplete callback
    async (result) => {
      console.log('Podcast generation completed, result:', result);
      
      try {
        setPodcastGenerationState(prev => ({
          ...prev,
          isGenerating: false,
          progress: 'Panel discussion generated successfully!',
        }));
        
        // Handle different result formats - check for audio_path, audioUrl, or generated_files
        const hasAudio = result && (result.audio_path || result.audioUrl || result.generated_files);
        console.log('Has audio result:', hasAudio, 'audio_path:', result?.audio_path, 'audioUrl:', result?.audioUrl);
        
        if (hasAudio) {
          console.log('Loading generated podcast...');
          await loadGeneratedPodcast(result);
        } else {
          console.warn('No audio found in result, reloading podcast list...');
        }
        
        // Always reload the full list to ensure consistency
        console.log('Reloading existing podcasts...');
        await loadExistingPodcasts();
        
        toast({
          title: "Panel Discussion Generated",
          description: "Your panel discussion has been generated successfully!",
        });
        
      } catch (error) {
        console.error('Error in podcast completion callback:', error);
        // Still show success toast since the podcast was generated
        toast({
          title: "Panel Discussion Generated",
          description: "Your panel discussion has been generated successfully!",
        });
        
        // Clear the job from persistent storage since it's completed
        clearJobFromStorage('podcast');
        
        // Force reload to ensure UI is updated
        await loadExistingPodcasts();
      }
    },
    // onError callback
    (error) => {
      console.error('Podcast generation error:', error);
      
      // Check if this is a cancellation (don't show error toast for cancellations)
      const isCancellation = typeof error === 'string' && (error.includes('cancelled') || error.includes('Cancelled'));
      
      setPodcastGenerationState(prev => ({
        ...prev,
        isGenerating: false,
        error: isCancellation ? 'Cancelled' : (error || 'Panel discussion generation failed'),
      }));
      
      // Only show error toast if it's not a cancellation
      if (!isCancellation) {
        toast({
          title: "Generation Failed",
          description: error || "Panel discussion generation failed. Please try again.",
          variant: "destructive",
        });
      }
      
      // Clear the job from persistent storage since it failed or was cancelled
      clearJobFromStorage('podcast');
    },
    // Pass notebookId and specify this is for podcast jobs
    notebookId,
    'podcast'
  );



  // Update local state when podcast job status changes
  useEffect(() => {
    const currentJobId = podcastGenerationState.jobId;
    
    if (currentJobId) {
      if (podcastJobStatus) {
        setPodcastGenerationState(prev => {
          if (prev.jobId !== currentJobId) return prev;
          
          const isGenerating = podcastJobStatus === 'generating' || podcastJobStatus === 'pending';
          const isCancelled = podcastJobStatus === 'cancelled';
          const isCompleted = podcastJobStatus === 'completed';
          
          return {
            ...prev,
            isGenerating: isGenerating && !isCompleted && !isCancelled,
            progress: isCancelled ? '' : prev.progress,
            error: isCancelled ? 'Cancelled' : prev.error,
          };
        });
      }
      
      if (podcastJobProgress) {
        setPodcastGenerationState(prev => 
          prev.jobId === currentJobId ? { ...prev, progress: podcastJobProgress } : prev
        );
      }
      
      if (podcastJobError && podcastJobError !== 'Cancelled') {
        setPodcastGenerationState(prev => 
          prev.jobId === currentJobId ? { ...prev, error: podcastJobError } : prev
        );
      }
    }
  }, [podcastJobStatus, podcastJobProgress, podcastJobError]);

  // Effect to handle podcast connection errors and clear stale state
  useEffect(() => {
    if (podcastConnectionError && podcastGenerationState.jobId) {
      // If we have persistent connection errors, the job might be stale
      const timeoutId = setTimeout(() => {
        if (podcastConnectionError && !podcastIsConnected) {
          console.log('Clearing podcast state due to persistent connection error:', podcastConnectionError);
          handleClearPodcastStatus();
        }
      }, 5000); // Wait 5 seconds before clearing due to connection error

      return () => clearTimeout(timeoutId);
    }
  }, [podcastConnectionError, podcastIsConnected, podcastGenerationState.jobId, handleClearPodcastStatus]);

  const checkBackendHealth = async () => {
    try {
      await apiService.healthCheck();
      console.log('Backend is healthy');
    } catch (error) {
      console.error('Backend health check failed:', error);
      // Only show error toast if this is a persistent connection issue
      // Add a delay and retry before showing the error to avoid false positives during page navigation
      setTimeout(async () => {
        try {
          await apiService.healthCheck();
          console.log('Backend is healthy on retry');
        } catch (retryError) {
          console.error('Backend health check failed on retry:', retryError);
          toast({
            title: "Backend Connection Issue",
            description: "Unable to connect to the backend. Please check if the server is running.",
            variant: "destructive",
          });
        }
      }, 2000); // Wait 2 seconds before retry
    }
  };

  const loadAvailableModels = async () => {
    try {
      const models = await apiService.getAvailableModels();
      // Map the API response to match our state structure
      setAvailableModels({
        model_providers: models.providers || ['openai', 'google'],
        retrievers: models.retrievers || ['tavily', 'brave', 'serper', 'you', 'bing', 'duckduckgo', 'searxng'],
        time_ranges: models.time_ranges || ['day', 'week', 'month', 'year'],
      });
      console.log('Loaded available models:', models);
    } catch (error) {
      console.error('Failed to load available models:', error);
      // Keep the default values on error
      setAvailableModels({
        model_providers: ['openai', 'google'],
        retrievers: ['tavily', 'brave', 'serper', 'you', 'bing', 'duckduckgo', 'searxng'],
        time_ranges: ['day', 'week', 'month', 'year'],
      });
    }
  };

  const loadExistingReports = async () => {
    try {
      console.log('Loading existing reports...');
      const response = await apiService.listReportJobs(notebookId, 50);
      
      if (response && response.jobs) {
        const completedJobs = response.jobs.filter(job => job.status === 'completed');
        const runningJobs = response.jobs.filter(job => 
            (job.status === 'running' || job.status === 'pending') &&
            (new Date().getTime() - new Date(job.updated_at).getTime()) < 15 * 60 * 1000
        );
        
        console.log('Found completed jobs:', completedJobs);
        console.log('Found running report jobs:', runningJobs);
        
        // Restore state for any running jobs (only if they're recent, not stale)
        if (runningJobs.length > 0) {
          const runningJob = runningJobs[0];
          const jobAge = new Date().getTime() - new Date(runningJob.updated_at).getTime();
          const isStale = jobAge > 15 * 60 * 1000;
          
          if (!isStale) {
            setReportGenerationState(prev => ({
              ...prev,
              isGenerating: true,
              currentJobId: runningJob.job_id,
              progress: 'Reconnecting to ongoing report generation...',
              error: null,
            }));
          }
        }
        
        // Convert completed jobs to files format - simplified approach
        const reportFiles = completedJobs.map((job) => ({
          id: `report-${job.job_id}`,
          name: `${reportConfig.article_title || 'Research Report'}.md`,
          jobId: job.job_id,
          createdAt: job.created_at || new Date().toISOString(),
          // Content will be loaded on-demand when file is clicked
          content: null,
          generatedFiles: job.generated_files || [],
        }));

        if (reportFiles.length > 0) {
          console.log('Loaded existing reports:', reportFiles);
          setFiles(reportFiles);
        }
      }
    } catch (error) {
      console.error('Error loading existing reports:', error);
      toast({
        title: "Error Loading Reports",
        description: "Failed to load existing reports. Please try refreshing the page.",
        variant: "destructive",
      });
    }
  };

  // Add new function to load report content on-demand
  const loadReportContent = async (file) => {
    if (!file.content) {
      try {
        const contentResponse = await apiService.getReportContent(file.jobId, notebookId);
        if (contentResponse && contentResponse.content) {
          // Update the file with content
          setFiles(prevFiles => 
            prevFiles.map(f => 
              f.id === file.id 
                ? { ...f, content: contentResponse.content }
                : f
            )
          );
          return contentResponse.content;
        }
      } catch (error) {
        console.error(`Error loading content for report ${file.jobId}:`, error);
        return `# ${file.name}\n\nError: Report content could not be loaded. Please try downloading the report file directly.`;
      }
    }
    return file.content;
  };

  const loadGeneratedReport = async (result) => {
    try {
      // Start with default content
      let reportContent = `# ${result.article_title}\n\nReport generated successfully!\n\nOutput directory: ${result.output_directory}\n\nGenerated files:\n${result.generated_files.map(f => `- ${f}`).join('\n')}`;
      
      if (reportGenerationState.currentJobId) {
        try {
          console.log('Attempting to fetch report content for job:', reportGenerationState.currentJobId);
          const contentResponse = await apiService.getReportContent(reportGenerationState.currentJobId, notebookId);
          console.log('Content response:', contentResponse);
          
          if (contentResponse && contentResponse.content) {
            reportContent = contentResponse.content;
            console.log('Successfully loaded report content');
          } else {
            console.warn('Content response was empty or invalid');
          }
        } catch (contentError) {
          console.warn('Could not fetch report content:', contentError);
          
          // Try different fallback approaches to get the polished content
          try {
            console.log('Attempting fallback download of polished file');
            // First try the direct filename
            let blob;
            try {
              blob = await apiService.downloadReportFile(reportGenerationState.currentJobId, notebookId, 'storm_gen_article_polished.md');
            } catch (directError) {
              console.log('Direct filename failed, trying with subdirectory path');
              // Try with the Research_Report subdirectory path
              blob = await apiService.downloadReportFile(reportGenerationState.currentJobId, notebookId, 'Research_Report/storm_gen_article_polished.md');
            }
            reportContent = await blob.text();
            console.log('Successfully downloaded polished file');
          } catch (downloadError) {
            console.warn('Could not download polished file, using default content:', downloadError);
          }
        }
      }

      const newReport = {
        id: `report-${Date.now()}`,
        name: `${reportConfig.article_title || 'Research Report'}.md`,
        content: reportContent,
        jobId: reportGenerationState.currentJobId,
        generatedFiles: result.generated_files,
      };
      
      console.log('Adding report to files list:', newReport);
      setFiles(prev => [newReport, ...prev]);
    } catch (error) {
      console.error('Error loading generated report:', error);
      
      // Ensure we still add the report even if content loading fails
      const fallbackReport = {
        id: `report-${Date.now()}`,
        name: `${reportConfig.article_title || 'Research Report'}.md`,
        content: `# ${result.article_title}\n\nReport generated successfully!\n\nOutput directory: ${result.output_directory}\n\nGenerated files:\n${result.generated_files.map(f => `- ${f}`).join('\n')}`,
        jobId: reportGenerationState.currentJobId,
        generatedFiles: result.generated_files,
      };
      
      setFiles(prev => [fallbackReport, ...prev]);
    }
  };

  const loadExistingPodcasts = async () => {
    try {
      console.log('Loading existing podcasts...');
      const response = await apiService.listPodcastJobs(notebookId);
      
      if (response && response.jobs) {
        const completedJobs = response.jobs.filter(job => job.status === 'completed');
        const runningJobs = response.jobs.filter(job => 
            (job.status === 'generating' || job.status === 'pending') &&
            // Check if job was updated in the last 15 minutes to avoid stale jobs
            (new Date().getTime() - new Date(job.updated_at).getTime()) < 15 * 60 * 1000
        );
        
        console.log('Found completed podcast jobs:', completedJobs);
        console.log('Found running podcast jobs:', runningJobs);
        
        // Restore state for any running jobs (only if they're recent, not stale)
        if (runningJobs.length > 0) {
          const runningJob = runningJobs[0]; // Take the most recent running job
          
          // Double-check that this job is really recent (within last 15 minutes)
          const jobAge = new Date().getTime() - new Date(runningJob.updated_at).getTime();
          const isStale = jobAge > 15 * 60 * 1000; // 15 minutes
          
          if (!isStale) {
            console.log('Restoring podcast generation state for job:', runningJob.job_id);
            
            setPodcastGenerationState(prev => ({
              ...prev,
              isGenerating: true,
              jobId: runningJob.job_id,
              progress: 'Reconnecting to ongoing panel discussion generation...',
              error: null,
              title: runningJob.title || prev.title || '',
              description: runningJob.description || prev.description || '',
            }));
          } else {
            console.log('Skipping stale podcast job:', runningJob.job_id, 'age:', Math.round(jobAge / 1000 / 60), 'minutes');
          }
        }
        
        // Convert completed jobs to podcast format
        const podcastList = completedJobs.map((job) => {
          // Extract filename from audio_path, audio_url, or use job_id
          let filename = `${job.job_id}.mp3`;
          
          // Check for audio_path first (matches the log format), then audio_url as fallback
          const audioSource = job.audio_path || job.audio_url;
          if (audioSource) {
            const urlParts = audioSource.split('/');
            filename = urlParts[urlParts.length - 1];
            console.log('Extracted filename for existing podcast:', filename, 'from:', audioSource);
          }

          return {
            id: `podcast-${job.job_id}`,
            name: filename,
            title: job.title || 'Panel Discussion',
            description: job.description || '',
            jobId: job.job_id,
            type: 'podcast',
            createdAt: job.created_at || new Date().toISOString(),
            generatedFiles: [],
          };
        });

        console.log('Setting podcast files:', podcastList);
        setPodcastFiles(podcastList);
        
        // Force a re-render by updating a dummy state if needed
        if (podcastList.length > 0) {
          console.log('Loaded existing podcasts:', podcastList);
        }
      }
    } catch (error) {
      console.error('Error loading existing podcasts:', error);
    }
  };

  const loadGeneratedPodcast = async (result) => {
    try {
      console.log('Loading newly generated podcast:', result);
      
      // Extract filename from audio_path, audio_url, or use job_id
      let filename = `${podcastGenerationState.jobId}.mp3`;
      
      // Check for audio_path first (from your log), then audio_url as fallback
      const audioSource = result.audio_path || result.audioUrl || result.audio_url;
      if (audioSource) {
        const urlParts = audioSource.split('/');
        filename = urlParts[urlParts.length - 1];
        console.log('Extracted filename from audio source:', filename, 'from:', audioSource);
      }

      const newPodcast = {
        id: `podcast-${podcastGenerationState.jobId}`,
        name: filename,
        title: podcastGenerationState.title || result.title || 'Panel Discussion',
        description: podcastGenerationState.description || result.description || '',
        jobId: podcastGenerationState.jobId,
        type: 'podcast',
        createdAt: new Date().toISOString(),
        generatedFiles: result.generated_files || [],
      };
      
      console.log('Adding new podcast to files list:', newPodcast);
      
      // Force state update to ensure UI refresh
      setPodcastFiles(prev => {
        const exists = prev.find(p => p.jobId === podcastGenerationState.jobId);
        if (exists) {
          console.log('Podcast already exists, updating:', exists);
          // Update existing podcast
          const updated = prev.map(p => p.jobId === podcastGenerationState.jobId ? newPodcast : p);
          console.log('Updated podcast list:', updated);
          return updated;
        }
        console.log('Adding new podcast to list');
        const newList = [newPodcast, ...prev];
        console.log('New podcast list:', newList);
        return newList;
      });
      
      // Force a small delay to ensure state has updated
      setTimeout(() => {
        console.log('Current podcast files after update:', podcastFiles);
      }, 100);
      
    } catch (error) {
      console.error('Error loading generated podcast:', error);
      throw error; // Re-throw so the calling function can handle it
    }
  };

  const handleGenerateReport = async () => {
    // Use the state instead of calling the ref directly
    const hasFiles = selectedFiles.length > 0;
    const hasTopic = reportConfig.topic.trim();

    // Validate that at least one input is provided
    if (!hasTopic && !hasFiles) {
      toast({
        title: "Input Required",
        description: "Please enter a topic or select files from the Sources panel.",
        variant: "destructive",
      });
      return;
    }

    try {
      setReportGenerationState({
        isGenerating: true,
        currentJobId: null,
        progress: 'Starting report generation...',
        error: null,
      });

      let response;

      if (hasFiles) {
        // Use file-based generation (same approach as podcast generation)
        const sourceFileIds = selectedFiles.map(file => file.file_id);
        
        const requestData = {
          // Strictly keep topic empty if not provided by user
          topic: hasTopic ? reportConfig.topic.trim() : "",
          // When no topic is provided, use empty article_title to avoid confusion with topic
          article_title: hasTopic ? 
            (reportConfig.article_title && reportConfig.article_title !== 'Research Report' ? reportConfig.article_title : reportConfig.topic.trim()) : 
            "",
          model_provider: reportConfig.model_provider,
          retriever: reportConfig.retriever,
          selected_files_paths: sourceFileIds,
          // Include all config properties for file-based generation
          temperature: reportConfig.temperature,
          top_p: reportConfig.top_p,
          max_conv_turn: reportConfig.max_conv_turn,
          max_perspective: reportConfig.max_perspective,
          search_top_k: reportConfig.search_top_k,
          do_research: reportConfig.do_research,
          do_generate_outline: reportConfig.do_generate_outline,
          do_generate_article: reportConfig.do_generate_article,
          do_polish_article: reportConfig.do_polish_article,
          remove_duplicate: reportConfig.remove_duplicate,
          post_processing: reportConfig.post_processing,
        };

        console.log('Generating report with selected file IDs:', sourceFileIds, 'and topic:', hasTopic ? reportConfig.topic.trim() : '(empty)');
        response = await apiService.generateReportWithSourceIds(requestData, notebookId);
      } else if (hasTopic) {
        // Use topic-based generation only
        console.log('Generating report with topic only:', reportConfig.topic);
        response = await apiService.generateReport(reportConfig, notebookId);
      } else {
        // This should not happen due to validation above, but handle gracefully
        toast({
          title: "No Valid Input",
          description: "Please enter a topic to generate a report.",
          variant: "destructive",
        });
        setReportGenerationState({
          isGenerating: false,
          currentJobId: null,
          progress: '',
          error: null,
        });
        return;
      }
      
      setReportGenerationState(prev => ({
        ...prev,
        currentJobId: response.job_id,
        progress: 'Report generation started...',
      }));

      // Save job to persistent storage for tracking across navigation
      saveJobToStorage(response.job_id, 'report', {
        topic: reportConfig.topic,
        article_title: reportConfig.article_title,
        hasFiles,
        hasTopic,
      });

      console.log('Report generation job created:', response.job_id);

      toast({
        title: "Report Generation Started",
        description: `Job ID: ${response.job_id}`,
      });

    } catch (error) {
      console.error('Report generation error:', error);
      
      // Check if this is just a warning about input fields (which shouldn't cause failure)
      const isInputFieldWarning = error && error.message && 
        (error.message.includes('Not all input fields were provided') || 
         error.message.includes('input field warnings') ||
         error.message.includes('Missing:'));
      
      if (isInputFieldWarning) {
        // Don't treat input field warnings as failures during API call
        console.warn('Input field warning during API call (not treating as failure):', error.message);
        
        setReportGenerationState(prev => ({
          ...prev,
          progress: 'Report generation started (with input field warnings)...',
        }));
        
        toast({
          title: "Generation Started",
          description: "Report generation is proceeding with some input field warnings. This is normal for topic-only generation.",
          variant: "default",
        });
        return; // Don't set error state
      }
      
      setReportGenerationState({
        isGenerating: false,
        currentJobId: null,
        progress: '',
        error: error.message,
      });

      toast({
        title: "Generation Failed",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleCancelGeneration = async () => {
    if (!reportGenerationState.currentJobId) return;

    try {
      // Use SSE-based cancellation
      const success = reportCancelJob();
      
      if (success) {
        setReportGenerationState(prev => ({
          ...prev,
          isGenerating: false,
          progress: '',
          error: 'Cancelled',
        }));

        toast({
          title: "Cancellation Requested",
          description: "Cancellation request sent. The job will stop shortly.",
        });

        // Immediately clear the status so the UI doesn't hang
        handleClearReportStatus();
      } else {
        // Fallback to HTTP API if SSE cancellation is not available
        console.warn('SSE cancellation failed, falling back to HTTP API');
        await apiService.cancelReportJob(reportGenerationState.currentJobId, notebookId);
        
        setReportGenerationState(prev => ({
          ...prev,
          isGenerating: false,
          progress: '',
          error: 'Cancelled',
        }));

        toast({
          title: "Generation Cancelled",
          description: "Report generation has been cancelled.",
        });
        
        // Immediately clear the status so the UI doesn't hang
        handleClearReportStatus();
      }
    } catch (error) {
      console.error('Failed to cancel job:', error);
      toast({
        title: "Cancel Failed",
        description: error.message || "Failed to cancel job. It may have already completed.",
        variant: "destructive",
      });
    }
  };

  // Podcast generation handlers
  const handleGeneratePodcast = async () => {
    try {
      // Use the state instead of calling the ref directly
      if (!selectedFiles || selectedFiles.length === 0) {
        toast({
          title: "No Files Selected",
          description: "Please select at least one file from the Sources panel to generate a podcast.",
          variant: "destructive",
        });
        return;
      }

      const sourceFileIds = selectedFiles.map(file => file.file_id);
      
      setPodcastGenerationState(prev => ({
        ...prev,
        isGenerating: true,
        progress: 'Starting panel discussion generation...',
        error: null,
      }));

      const formData = new FormData();
      sourceFileIds.forEach(id => formData.append('source_file_ids', id));
      formData.append('title', podcastGenerationState.title || 'Generated Podcast');
      formData.append('description', podcastGenerationState.description || '');

      const response = await apiService.generatePodcast(formData, notebookId);
      
      setPodcastGenerationState(prev => ({
        ...prev,
        jobId: response.job_id,
        progress: 'Panel discussion generation started...',
      }));

      // Save job to persistent storage for tracking across navigation
      saveJobToStorage(response.job_id, 'podcast', {
        title: podcastGenerationState.title || 'Generated Podcast',
        description: podcastGenerationState.description || '',
        sourceFileIds,
      });

      toast({
        title: "Panel Discussion Generation Started",
        description: "Your panel discussion is being generated. This may take several minutes.",
      });
    } catch (error) {
      setPodcastGenerationState(prev => ({
        ...prev,
        isGenerating: false,
        error: error.message || 'Failed to start panel discussion generation',
      }));
      
      toast({
        title: "Generation Failed",
        description: error.message || "Failed to start panel discussion generation. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleCancelPodcast = async () => {
    if (!podcastGenerationState.jobId) return;

    try {
      // Use SSE-based cancellation (same as reports)
      const success = podcastCancelJob();
      
      if (success) {
        setPodcastGenerationState(prev => ({
          ...prev,
          isGenerating: false,
          progress: '',
          error: 'Cancelled',
        }));

        toast({
          title: "Cancellation Requested",
          description: "Cancellation request sent. The job will stop shortly.",
        });

        // Immediately clear the status so the UI doesn't hang (same as reports)
        handleClearPodcastStatus();
      } else {
        // Fallback to HTTP API if SSE cancellation is not available
        console.warn('SSE cancellation failed, falling back to HTTP API');
        await apiService.cancelPodcastJob(podcastGenerationState.jobId, notebookId);
        
        setPodcastGenerationState(prev => ({
          ...prev,
          isGenerating: false,
          progress: '',
          error: 'Cancelled',
        }));

        toast({
          title: "Generation Cancelled",
          description: "Panel discussion generation has been cancelled.",
        });
        
        // Immediately clear the status so the UI doesn't hang (same as reports)
        handleClearPodcastStatus();
      }
    } catch (error) {
      toast({
        title: "Cancel Failed",
        description: error.message || "Failed to cancel panel discussion generation.",
        variant: "destructive",
      });
    }
  };

  const handlePodcastTitleChange = (title) => {
    setPodcastGenerationState(prev => ({
      ...prev,
      title,
    }));
  };

  const handlePodcastDescriptionChange = (description) => {
    setPodcastGenerationState(prev => ({
      ...prev,
      description,
    }));
  };

  const handleDownloadFile = async (file) => {
    if (!file.jobId) {
      toast({
        title: "Download Not Available",
        description: "This file is not available for download.",
        variant: "destructive",
      });
      return;
    }

    try {
      // Always download without specifying filename - let backend choose the polished report
      const blob = await apiService.downloadReportFile(file.jobId, notebookId, null);
      
      // Use the report name as the filename, ensuring it has .md extension
      let filename = file.name || 'report.md';
      if (!filename.endsWith('.md')) {
        filename = filename.replace(/\.[^/.]+$/, "") + '.md'; // Replace extension with .md
      }
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast({
        title: "Download Started",
        description: `Downloading ${filename}...`,
      });
    } catch (error) {
      toast({
        title: "Download Failed",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handlePlayPodcast = async (podcast) => {
    if (!podcast.jobId) {
      toast({
        title: "Playback Not Available",
        description: "This podcast is not available for playback.",
        variant: "destructive",
      });
      return;
    }

    // If audio is already loaded, don't reload
    if (audioBlobs.has(podcast.id)) {
      return;
    }

    // If already loading, don't start another request
    if (loadingAudio.has(podcast.id)) {
      return;
    }

    try {
      // Mark as loading
      setLoadingAudio(prev => new Set(prev).add(podcast.id));

      // Download the audio file
      const blob = await apiService.downloadPodcastAudio(podcast.jobId, notebookId);
      
      // Create blob URL
      const blobUrl = window.URL.createObjectURL(blob);
      
      // Store the blob URL
      setAudioBlobs(prev => new Map(prev).set(podcast.id, blobUrl));
    } catch (error) {
      toast({
        title: "Audio Load Failed",
        description: error.message || "Failed to load audio for playback",
        variant: "destructive",
      });
    } finally {
      // Remove from loading set
      setLoadingAudio(prev => {
        const newSet = new Set(prev);
        newSet.delete(podcast.id);
        return newSet;
      });
    }
  };



  const handleDownloadPodcast = async (podcast) => {
    if (!podcast.jobId) {
      toast({
        title: "Download Not Available",
        description: "This podcast is not available for download.",
        variant: "destructive",
      });
      return;
    }

    try {
      // Use the authenticated API service to download the audio file
      const blob = await apiService.downloadPodcastAudio(podcast.jobId, notebookId);
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = podcast.name || 'panel-discussion.mp3';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast({
        title: "Download Started",
        description: `Downloading ${podcast.name}...`,
      });
    } catch (error) {
      toast({
        title: "Download Failed",
        description: error.message || "Failed to download podcast",
        variant: "destructive",
      });
    }
  };

  const handleDeletePodcast = async (podcastId) => {
    try {
      // Extract job ID from podcast ID (format: "podcast-{jobId}")
      const jobId = podcastId.replace('podcast-', '');
      
      // Call the backend API to delete the podcast
      await apiService.deletePodcast(jobId, notebookId);
      
      // Clean up blob URL if exists
      const blobUrl = audioBlobs.get(podcastId);
      if (blobUrl) {
        window.URL.revokeObjectURL(blobUrl);
        setAudioBlobs(prev => {
          const newMap = new Map(prev);
          newMap.delete(podcastId);
          return newMap;
        });
      }
      
      // Remove from local state
      setPodcastFiles((prev) => prev.filter((p) => p.id !== podcastId));
      setActiveMenuFileId(null);
      
      toast({
        title: "Podcast Deleted",
        description: "The podcast has been deleted successfully.",
      });
    } catch (error) {
      toast({
        title: "Delete Failed",
        description: error.message || "Failed to delete podcast. Please try again.",
        variant: "destructive",
      });
    }
  };





  const handleEdit = useCallback(() => {
    setIsEditing(true);
    setViewMode("code");
  }, []);

  const handleSave = useCallback(() => {
    setSelectedFile((prev) => ({
      ...prev,
      content: modalContent,
    }));
    setFiles((prevFiles) =>
      prevFiles.map((file) =>
        file.id === selectedFile.id ? { ...file, content: modalContent } : file
      )
    );
    setIsEditing(false);
    setModalOpen(false);
    
    toast({
      title: "Report Saved",
      description: "Your changes have been saved successfully.",
    });
  }, [modalContent, selectedFile?.id, toast]);

  const handleClose = useCallback(() => {
    setSelectedFile(null);
    setIsExpanded(false);
  }, []);

  const handleFileClick = useCallback(async (file) => {
    setSelectedFile(file);
    setViewMode("preview");
    setIsEditing(false);
    setIsExpanded(false);
    
    // Load content if not already loaded
    if (!file.content) {
      const content = await loadReportContent(file);
      setSelectedFile(prev => prev ? { ...prev, content } : prev);
    }
  }, []);

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Enhanced Header */}
      <div className="flex-shrink-0 px-6 py-4 bg-gradient-to-r from-slate-50 to-gray-50 border-b border-gray-200/80">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-sm">
              <FileText className="h-4 w-4 text-white" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-gray-900">AI Studio</h3>
              <p className="text-xs text-gray-500">Create reports and panel discussions</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {(reportGenerationState.isGenerating || podcastGenerationState.isGenerating) && (
              <div className="flex items-center space-x-2 px-3 py-1.5 bg-blue-50 rounded-full border border-blue-100">
                <Loader2 className="h-3 w-3 animate-spin text-blue-600" />
                <span className="text-xs font-medium text-blue-700">Processing...</span>
              </div>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 px-3 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-100/80 border border-transparent hover:border-gray-200 transition-all duration-200"
              onClick={() => {
                console.log('Manual refresh triggered');
                loadExistingPodcasts();
                loadExistingReports();
              }}
              title="Refresh content"
            >
              <RefreshCw className="h-3 w-3 mr-1.5" />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Unified Content Container - Only show when no file is selected */}
        {!selectedFile && (
          <div className="p-6 space-y-8">
            {/* Panel Discussion Generation Section */}
            <PodcastGenerationSection
              podcastGenerationState={podcastGenerationState}
              onGeneratePodcast={handleGeneratePodcast}
              isCollapsed={collapsedSections.podcast}
              onToggleCollapse={() => toggleSection('podcast')}
              selectedFiles={selectedFiles}
              selectedSources={selectedSources}
              onTitleChange={handlePodcastTitleChange}
              onDescriptionChange={handlePodcastDescriptionChange}
              onCancel={handleCancelPodcast}
              isConnected={podcastIsConnected}
              connectionError={podcastConnectionError}
            />

            {/* Report Generation Section */}
            <ReportConfigSection
              reportConfig={reportConfig}
              setReportConfig={setReportConfig}
              availableModels={availableModels}
              onGenerateReport={handleGenerateReport}
              onShowCustomize={() => setShowCustomizeReport(true)}
              isGenerating={reportGenerationState.isGenerating}
              selectedFiles={selectedFiles}
              isCollapsed={collapsedSections.report}
              onToggleCollapse={() => toggleSection('report')}
              reportGenerationState={reportGenerationState}
              onCancel={handleCancelGeneration}
              isConnected={isConnected}
              connectionError={connectionError}
            />

            {/* Generated Podcasts List */}
            {podcastFiles.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden">
                <div 
                  className="px-6 py-4 bg-gradient-to-r from-orange-50 to-amber-50 border-b border-orange-100 cursor-pointer hover:from-orange-100 hover:to-amber-100 transition-all duration-200 min-h-[72px]"
                  onClick={() => toggleSection('podcastList')}
                >
                  <div className="flex items-center justify-between h-full">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-amber-500 rounded-lg flex items-center justify-center shadow-sm">
                        <Play className="h-4 w-4 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">Panel Discussions</h3>
                        <p className="text-sm text-gray-600">{podcastFiles.length} available • Ready to play</p>
                      </div>
                    </div>
                    {collapsedSections.podcastList ? (
                      <ChevronDown className="h-5 w-5 text-gray-500" />
                    ) : (
                      <ChevronUp className="h-5 w-5 text-gray-500" />
                    )}
                  </div>
                </div>
                {!collapsedSections.podcastList && (
                  <div>
                    {podcastFiles.map((podcast) => (
                      <PodcastListItem
                        key={podcast.id}
                        podcast={podcast}
                        onDownload={handleDownloadPodcast}
                        onMenuToggle={(podcastId) => setActiveMenuFileId(activeMenuFileId === podcastId ? null : podcastId)}
                        isMenuOpen={activeMenuFileId === podcast.id}
                        audioBlob={audioBlobs.get(podcast.id)}
                        isLoading={loadingAudio.has(podcast.id)}
                        onDelete={handleDeletePodcast}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Generated Files List */}
            {files.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden">
                <div 
                  className="px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-100 cursor-pointer hover:from-blue-100 hover:to-indigo-100 transition-all duration-200 min-h-[72px]"
                  onClick={() => toggleSection('reportList')}
                >
                  <div className="flex items-center justify-between h-full">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-sm">
                        <FileText className="h-4 w-4 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">Research Reports</h3>
                        <p className="text-sm text-gray-600">{files.length} available • Ready to view</p>
                      </div>
                    </div>
                    {collapsedSections.reportList ? (
                      <ChevronDown className="h-5 w-5 text-gray-500" />
                    ) : (
                      <ChevronUp className="h-5 w-5 text-gray-500" />
                    )}
                  </div>
                </div>
                {!collapsedSections.reportList && (
                  <div className="divide-y divide-gray-100">
                    {files.map((file) => (
                      <FileListItem
                        key={file.id}
                        file={file}
                        isSelected={selectedFile?.id === file.id}
                        onFileClick={handleFileClick}
                        onDownload={handleDownloadFile}
                        onMenuToggle={(fileId) => setActiveMenuFileId(activeMenuFileId === fileId ? null : fileId)}
                        isMenuOpen={activeMenuFileId === file.id}
                        onEdit={(file) => {
                          setModalContent(file.content);
                          setSelectedFile(file);
                          setModalOpen(true);
                          setActiveMenuFileId(null);
                        }}
                        onDelete={(fileId) => {
                          setFiles((prev) => prev.filter((f) => f.id !== fileId));
                          setActiveMenuFileId(null);
                        }}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Enhanced Empty State */}
        {!selectedFile && files.length === 0 && podcastFiles.length === 0 && !reportGenerationState.isGenerating && !podcastGenerationState.isGenerating && (
          <div className="flex-1 flex items-center justify-center p-12">
            <div className="text-center max-w-lg">
              <div className="relative mb-8">
                <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-3xl mx-auto mb-4 flex items-center justify-center shadow-xl">
                  <FileText className="h-10 w-10 text-white" />
                </div>
                <div className="absolute -top-2 -right-2 w-8 h-8 bg-gradient-to-br from-orange-500 to-amber-500 rounded-xl flex items-center justify-center shadow-lg">
                  <Play className="h-4 w-4 text-white" />
                </div>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-3">Welcome to AI Studio</h3>
              <p className="text-gray-600 mb-8 leading-relaxed">Transform your knowledge into comprehensive research reports and engaging panel discussions with the power of AI</p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
                <div className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <FileText className="h-4 w-4 text-white" />
                  </div>
                  <h4 className="font-semibold text-gray-900 mb-1">Research Reports</h4>
                  <p className="text-xs text-gray-600">AI-powered comprehensive analysis</p>
                </div>
                <div className="p-4 bg-gradient-to-br from-orange-50 to-amber-50 rounded-xl border border-orange-100">
                  <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-amber-500 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <Play className="h-4 w-4 text-white" />
                  </div>
                  <h4 className="font-semibold text-gray-900 mb-1">Panel Discussions</h4>
                  <p className="text-xs text-gray-600">Engaging AI conversations</p>
                </div>
              </div>
              
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button
                  className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white shadow-lg hover:shadow-xl transition-all duration-200"
                  onClick={() => toggleSection('report')}
                >
                  <FileText className="mr-2 h-4 w-4" />
                  Create Research Report
                </Button>
                <Button
                  className="bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white shadow-lg hover:shadow-xl transition-all duration-200"
                  onClick={() => toggleSection('podcast')}
                >
                  <Play className="mr-2 h-4 w-4" />
                  Generate Panel Discussion
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Report Viewer */}
        {selectedFile && (
          <div className="p-6 space-y-8">
            {/* Report Display Panel */}
            <div
              className={`bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col transition-all duration-300 ${
                isExpanded ? "fixed inset-4 z-50" : "min-h-[500px]"
              }`}
            >
              {/* Toolbar */}
              <div className="px-6 py-4 border-b bg-gray-50 rounded-t-xl">
                {/* Top row - Navigation and Actions */}
                <div className="flex justify-between items-center mb-3">
                  <div className="flex items-center space-x-3">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={handleClose}
                      title="Close Report"
                      className="hover:bg-gray-100 text-gray-600 hover:text-gray-900"
                    >
                      <X className="h-4 w-4 mr-1" />
                      Close
                    </Button>
                    
                    <div className="h-4 w-px bg-gray-300"></div>
                    
                    <div className="flex items-center space-x-1">
                      <button
                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200 ${
                          viewMode === "preview"
                            ? "bg-gray-900 text-white"
                            : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                        }`}
                        onClick={() => setViewMode("preview")}
                      >
                        Preview
                      </button>
                      <button
                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200 ${
                          viewMode === "code"
                            ? "bg-gray-900 text-white"
                            : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                        }`}
                        onClick={() => setViewMode("code")}
                      >
                        Source
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center space-x-1">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={handleEdit}
                      title="Edit Report"
                      className="hover:bg-gray-100 text-gray-600 hover:text-gray-900"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      title="Share Report"
                      className="hover:bg-gray-100 text-gray-600 hover:text-gray-900"
                    >
                      <Share2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setIsExpanded(!isExpanded)}
                      title={isExpanded ? "Minimize" : "Maximize"}
                      className="hover:bg-gray-100 text-gray-600 hover:text-gray-900"
                    >
                      {isExpanded ? (
                        <Minimize2 className="h-4 w-4" />
                      ) : (
                        <Maximize2 className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
                
                {/* Bottom row - File Name */}
                <div className="flex items-center space-x-2">
                  <FileText className="h-4 w-4 text-gray-500" />
                  <span className="text-sm font-medium text-gray-900 truncate">
                    {selectedFile.name}
                  </span>
                </div>
              </div>

              {/* Content Area */}
              <div className="flex-1 overflow-auto">
                {viewMode === "preview" ? (
                  <div className="p-8">
                    <MarkdownContent content={selectedFile.content} />
                  </div>
                ) : (
                  <div className="p-6">
                    <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono leading-relaxed">
                      {selectedFile.content}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

                 {/* Customize Report Modal */}
         {showCustomizeReport && (
           <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm">
             <div className="bg-white rounded-xl shadow-2xl w-[90%] max-w-2xl p-6">
               <div className="flex justify-between items-start mb-6">
                 <div className="flex items-center space-x-3">
                   <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                     <Settings className="h-5 w-5 text-gray-600" />
                   </div>
                   <div>
                     <h3 className="text-xl font-semibold text-gray-900">Customize Report Generation</h3>
                     <p className="text-sm text-gray-600 mt-1">
                       Configure advanced settings for your research report
                     </p>
                   </div>
                 </div>
                 <Button
                   variant="ghost"
                   size="sm"
                   onClick={() => setShowCustomizeReport(false)}
                   className="text-gray-500 hover:text-gray-800 hover:bg-gray-100"
                 >
                   <X className="w-5 h-5" />
                 </Button>
               </div>

               <div className="space-y-6">
                 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                   <div className="space-y-2">
                     <label className="block text-sm font-medium text-gray-700">Temperature</label>
                     <input
                       type="number"
                       min="0"
                       max="2"
                       step="0.1"
                       className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
                       value={reportConfig.temperature}
                       onChange={(e) => setReportConfig(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                     />
                   </div>
                   <div className="space-y-2">
                     <label className="block text-sm font-medium text-gray-700">Top P</label>
                     <input
                       type="number"
                       min="0"
                       max="1"
                       step="0.1"
                       className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
                       value={reportConfig.top_p}
                       onChange={(e) => setReportConfig(prev => ({ ...prev, top_p: parseFloat(e.target.value) }))}
                     />
                   </div>
                 </div>

                 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                   <div className="space-y-2">
                     <label className="block text-sm font-medium text-gray-700">Max Conversations</label>
                     <input
                       type="number"
                       min="1"
                       max="10"
                       className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
                       value={reportConfig.max_conv_turn}
                       onChange={(e) => setReportConfig(prev => ({ ...prev, max_conv_turn: parseInt(e.target.value) }))}
                     />
                   </div>
                   <div className="space-y-2">
                     <label className="block text-sm font-medium text-gray-700">Max Perspectives</label>
                     <input
                       type="number"
                       min="1"
                       max="10"
                       className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
                       value={reportConfig.max_perspective}
                       onChange={(e) => setReportConfig(prev => ({ ...prev, max_perspective: parseInt(e.target.value) }))}
                     />
                   </div>
                 </div>

                 <div className="space-y-2">
                   <label className="block text-sm font-medium text-gray-700">Search Results</label>
                   <input
                     type="number"
                     min="1"
                     max="50"
                     className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
                     value={reportConfig.search_top_k}
                     onChange={(e) => setReportConfig(prev => ({ ...prev, search_top_k: parseInt(e.target.value) }))}
                 />
               </div>

                 <div className="space-y-3">
                   <label className="block text-sm font-medium text-gray-700">Generation Options</label>
                   <div className="grid grid-cols-2 gap-3">
                     <label className="flex items-center space-x-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
                       <input
                         type="checkbox"
                         checked={reportConfig.do_research}
                         onChange={(e) => setReportConfig(prev => ({ ...prev, do_research: e.target.checked }))}
                         className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
                       />
                       <span className="text-sm font-medium text-gray-700">Research</span>
                     </label>
                     <label className="flex items-center space-x-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
                       <input
                         type="checkbox"
                         checked={reportConfig.do_generate_outline}
                         onChange={(e) => setReportConfig(prev => ({ ...prev, do_generate_outline: e.target.checked }))}
                         className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
                       />
                       <span className="text-sm font-medium text-gray-700">Generate Outline</span>
                     </label>
                     <label className="flex items-center space-x-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
                       <input
                         type="checkbox"
                         checked={reportConfig.do_generate_article}
                         onChange={(e) => setReportConfig(prev => ({ ...prev, do_generate_article: e.target.checked }))}
                         className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
                       />
                       <span className="text-sm font-medium text-gray-700">Generate Article</span>
                     </label>
                     <label className="flex items-center space-x-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
                       <input
                         type="checkbox"
                         checked={reportConfig.do_polish_article}
                         onChange={(e) => setReportConfig(prev => ({ ...prev, do_polish_article: e.target.checked }))}
                         className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
                       />
                       <span className="text-sm font-medium text-gray-700">Polish Article</span>
                     </label>
                     <label className="flex items-center space-x-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
                       <input
                         type="checkbox"
                         checked={reportConfig.remove_duplicate}
                         onChange={(e) => setReportConfig(prev => ({ ...prev, remove_duplicate: e.target.checked }))}
                         className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
                       />
                       <span className="text-sm font-medium text-gray-700">Remove Duplicates</span>
                     </label>
                     <label className="flex items-center space-x-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
                       <input
                         type="checkbox"
                         checked={reportConfig.post_processing}
                         onChange={(e) => setReportConfig(prev => ({ ...prev, post_processing: e.target.checked }))}
                         className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
                       />
                       <span className="text-sm font-medium text-gray-700">Post Processing</span>
                     </label>
                   </div>
                 </div>
               </div>

               <div className="flex justify-end mt-8 space-x-3 pt-6 border-t border-gray-200">
                 <Button
                   variant="outline"
                   onClick={() => setShowCustomizeReport(false)}
                   className="border-gray-300 text-gray-700 hover:bg-gray-50"
                 >
                   Cancel
                 </Button>
                 <Button
                   onClick={() => {
                     setShowCustomizeReport(false);
                     handleGenerateReport();
                   }}
                   disabled={reportGenerationState.isGenerating || (!reportConfig.topic.trim() && !selectedFiles.length)}
                   className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white"
                 >
                   {reportGenerationState.isGenerating ? (
                     <>
                       <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                       Generating...
                     </>
                   ) : (
                     "Generate Report"
                   )}
                 </Button>
               </div>
             </div>
           </div>
         )}

         {/* Edit Modal */}
         {modalOpen && (
           <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 backdrop-blur-sm">
             <div className="bg-white rounded-xl shadow-2xl w-[95%] h-[90%] max-w-6xl flex flex-col animate-in fade-in duration-200">
               {/* Modal Header */}
               <div className="px-6 py-4 border-b bg-gradient-to-r from-gray-50 to-slate-50 rounded-t-xl">
                 <div className="flex justify-between items-center">
                   <div className="flex items-center space-x-3">
                     <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center shadow-sm">
                       <Edit className="h-5 w-5 text-white" />
                     </div>
                     <div>
                       <h3 className="text-xl font-semibold text-gray-900">Edit Report</h3>
                       <p className="text-sm text-gray-600 mt-1">
                         Modify your report content using Markdown syntax
                       </p>
                     </div>
                   </div>
                   <div className="flex items-center space-x-2">
                     <Button 
                       onClick={handleSave}
                       className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white"
                     >
                       <CheckCircle className="mr-2 h-4 w-4" />
                       Save Changes
                     </Button>
                     <Button 
                       variant="outline" 
                       onClick={() => setModalOpen(false)}
                       className="text-gray-600 hover:text-gray-900 border-gray-300"
                     >
                       <X className="h-4 w-4" />
                     </Button>
                   </div>
                 </div>
               </div>
               
               {/* Modal Content */}
               <div className="flex-1 p-6 overflow-hidden">
                 <textarea
                   value={modalContent}
                   onChange={(e) => setModalContent(e.target.value)}
                   className="w-full h-full p-4 border border-gray-300 rounded-lg font-mono text-sm resize-none focus:ring-2 focus:ring-green-500 focus:border-transparent shadow-sm"
                   placeholder="Edit your report content here..."
                   autoFocus
                 />
               </div>
               
               {/* Modal Footer */}
               <div className="px-6 py-4 border-t bg-gradient-to-r from-gray-50 to-slate-50 rounded-b-xl">
                 <div className="flex justify-between items-center">
                   <div className="text-sm text-gray-500">
                     💡 Use Markdown syntax for formatting • Support for headers, lists, links, and more
                   </div>
                   <div className="flex space-x-2">
                     <Button 
                       variant="outline" 
                       onClick={() => setModalOpen(false)}
                       className="border-gray-300 text-gray-700 hover:bg-gray-50"
                     >
                       Cancel
                     </Button>
                     <Button 
                       onClick={handleSave}
                       className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white"
                     >
                       Save Changes
                     </Button>
                   </div>
                 </div>
               </div>
             </div>
           </div>
         )}
      </div>

      {/* Enhanced Footer */}
      {(files.length > 0 || podcastFiles.length > 0) && (
        <div className="flex-shrink-0 px-6 py-3 bg-gradient-to-r from-slate-50 to-gray-50 border-t border-gray-200/80">
          <div className="flex items-center justify-center space-x-6 text-xs text-gray-600">
            {files.length > 0 && (
              <div className="flex items-center space-x-1.5">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <span className="font-medium">{files.length} {files.length === 1 ? 'Report' : 'Reports'}</span>
              </div>
            )}
            {podcastFiles.length > 0 && (
              <div className="flex items-center space-x-1.5">
                <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                <span className="font-medium">{podcastFiles.length} {podcastFiles.length === 1 ? 'Discussion' : 'Discussions'}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default StudioPanel;