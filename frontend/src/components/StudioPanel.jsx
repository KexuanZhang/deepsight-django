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
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Clock,
  Play,
  ChevronDown,
  ChevronUp,
  Loader2,
  Info,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github.css";
import apiService from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";
import { usePodcastJobStatus } from "@/hooks/usePodcastJobStatus";
import { Badge } from "@/components/ui/badge";
import { config } from "@/config";

// Utility function for formatting model names
const formatModelName = (value) => {
  return value.charAt(0).toUpperCase() + value.slice(1);
};

// Status Icon Component
const StatusIcon = ({ isGenerating, error }) => {
  if (isGenerating) {
    return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
  }
  if (error) {
    if (error === 'Cancelled' || error === 'Cancelled by user') {
      return <X className="h-4 w-4 text-yellow-500" />;
    }
    return <AlertCircle className="h-4 w-4 text-red-500" />;
  }
  return <CheckCircle className="h-4 w-4 text-green-500" />;
};

// Connection Status Component
const ConnectionStatus = ({ isConnected, connectionError }) => {
  if (isConnected) {
    return (
      <div className="flex items-center space-x-1 text-xs">
        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
        <span className="text-green-600">Connected</span>
      </div>
    );
  }
  
  if (connectionError) {
    return (
      <div className="flex items-center space-x-1 text-xs">
        <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
        <span className="text-yellow-600">Reconnecting...</span>
      </div>
    );
  }
  
  return (
    <div className="flex items-center space-x-1 text-xs">
      <div className="w-2 h-2 bg-red-500 rounded-full"></div>
      <span className="text-red-600">Disconnected</span>
    </div>
  );
};

// Progress Card Component
const ProgressCard = ({ 
  title, 
  isGenerating, 
  progress, 
  error, 
  onCancel, 
  jobId, 
  showCancel = false,
  isConnected,
  connectionError 
}) => {
  const getStatusText = () => {
    if (isGenerating) return `${title}...`;
    if (error) {
      if (error === 'Cancelled' || error === 'Cancelled by user') {
        return 'Generation Cancelled';
      }
      return 'Generation Failed';
    }
    return 'Ready';
  };

  return (
    <div className="border rounded-lg p-4 bg-gray-50 border-gray-200">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <StatusIcon isGenerating={isGenerating} error={error} />
          <div>
            <h4 className="font-medium text-gray-900">{getStatusText()}</h4>
            {jobId && <ConnectionStatus isConnected={isConnected} connectionError={connectionError} />}
          </div>
        </div>
        
        {showCancel && isGenerating && jobId && (
          <Button
            variant="outline"
            size="sm"
            onClick={onCancel}
            className="text-red-600 border-red-300 hover:bg-red-50"
          >
            <X className="mr-1 h-3 w-3" />
            Cancel
          </Button>
        )}
      </div>
      
      {progress && (
        <div className="space-y-2">
          <p className="text-sm text-gray-700">{progress}</p>
          {isGenerating && (
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
            </div>
          )}
        </div>
      )}
      
      {connectionError && (
        <p className="text-xs text-yellow-600 mt-2 flex items-center">
          <Info className="h-3 w-3 mr-1" />
          {connectionError}
        </p>
      )}
      
      {jobId && (
        <p className="text-xs text-gray-500 mt-2 font-mono">
          Job ID: {jobId}
        </p>
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
  
  // Additional debugging - check what filters are failing
  const debugSelectedSources = selectedSources.map(source => ({
    title: source.title,
    selected: source.selected,
    has_file_id: !!(source.file_id || source.file),
    parsing_status: source.parsing_status,
    passes_filter: source.selected && (source.file_id || source.file) && source.parsing_status === 'completed'
  }));

  return (
    <div className="border rounded-lg overflow-hidden">
      <div 
        className="p-4 bg-gray-50 border-b cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={onToggleCollapse}
      >
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-gray-900 flex items-center">
            <Play className="h-4 w-4 mr-2 text-gray-600" />
            Generate Panel Discussion
          </h3>
          {isCollapsed ? <ChevronDown className="h-4 w-4 text-gray-500" /> : <ChevronUp className="h-4 w-4 text-gray-500" />}
        </div>
      </div>
      
      {!isCollapsed && (
        <div className="p-4 space-y-4">
          {(podcastGenerationState.isGenerating || podcastGenerationState.progress) && (
            <ProgressCard
              title="Generating Panel Discussion"
              isGenerating={podcastGenerationState.isGenerating}
              progress={podcastGenerationState.progress}
              error={podcastGenerationState.error}
              jobId={podcastGenerationState.jobId}
              showCancel={true}
              onCancel={onCancel}
              isConnected={isConnected}
              connectionError={connectionError}
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
                  <p className="text-xs text-yellow-700 font-medium">Selected files status:</p>
                  {debugSelectedSources.map((source, index) => (
                    <p key={index} className="text-xs text-yellow-600">
                      • {source.title}: {source.parsing_status || 'unknown status'}
                      {!source.passes_filter && source.parsing_status !== 'completed' && ' (needs to complete parsing)'}
                    </p>
                  ))}
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

// Report Configuration Component
const ReportConfigSection = ({ 
  reportConfig, 
  setReportConfig, 
  availableModels, 
  onGenerateReport, 
  onShowCustomize, 
  isGenerating, 
  selectedFiles, // Now passed as prop instead of using ref
  isCollapsed,
  onToggleCollapse 
}) => {
  // Check for valid input
  const hasTopic = reportConfig.topic.trim();
  const hasFiles = selectedFiles.length > 0;
  const hasValidInput = hasTopic || hasFiles;

  return (
    <div className="border rounded-lg overflow-hidden">
      <div 
        className="p-4 bg-gray-50 border-b cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={onToggleCollapse}
      >
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-gray-900 flex items-center">
            <FileText className="h-4 w-4 mr-2 text-gray-600" />
            Generate Research Report
          </h3>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onShowCustomize();
              }}
              className="text-xs border-gray-300 text-gray-600 hover:bg-gray-50"
            >
              <Settings className="mr-1 h-3 w-3" />
              Customize
            </Button>
            {isCollapsed ? <ChevronDown className="h-4 w-4 text-gray-500" /> : <ChevronUp className="h-4 w-4 text-gray-500" />}
          </div>
        </div>
      </div>

      {!isCollapsed && (
        <div className="p-4 space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Research Topic <span className="text-red-500">*</span>
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

          <Button
            className="w-full bg-gray-900 hover:bg-gray-800 text-white font-medium py-3"
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
const PodcastListItem = React.memo(({ podcast, onDownload, onMenuToggle, isMenuOpen, onDelete }) => (
  <div className="p-4 hover:bg-gray-50 transition-colors">
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-3 flex-1 min-w-0">
        <div className="flex-shrink-0">
          <Play className="h-5 w-5 text-orange-500" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {podcast.title}
          </p>
          {podcast.description && (
            <p className="text-xs text-gray-600 truncate mt-1">
              {podcast.description}
            </p>
          )}
          {podcast.createdAt && (
            <p className="text-xs text-gray-500 mt-1">
              {new Date(podcast.createdAt).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>
      
      <div className="flex items-center space-x-1">
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
    
    {/* Audio Player */}
    {podcast.audioUrl && (
      <div className="mt-3 pl-8">
        <audio 
          controls 
          className="w-full" 
          preload="metadata"
          controlsList="nodownload"
        >
          <source src={podcast.audioUrl} type="audio/mpeg" />
          Your browser does not support the audio element.
        </audio>
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
  
  // Function to update selected files when Sources panel selection changes
  const updateSelectedFiles = useCallback(() => {
    if (sourcesListRef?.current) {
      const newSelectedFiles = sourcesListRef.current.getSelectedFiles() || [];
      const newSelectedSources = sourcesListRef.current.getSelectedSources() || [];
      setSelectedFiles(newSelectedFiles);
      setSelectedSources(newSelectedSources);
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
    podcast: false,
    report: false,
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

  // Real-time job status monitoring using WebSocket for reports
  const { 
    status: jobStatus, 
    progress: jobProgress, 
    result: jobResult, 
    error: jobError, 
    isConnected,
    connectionError,
    cancelJob: webSocketCancelJob
  } = useWebSocket(
    reportGenerationState.currentJobId,
    // onComplete callback
    async (result) => {
      setReportGenerationState(prev => ({
        ...prev,
        isGenerating: false,
        progress: 'Report generated successfully!',
      }));
      
      // Use jobResult from the hook state for more reliable data
      const finalResult = result || jobResult;
      if (finalResult && finalResult.generated_files) {
        await loadGeneratedReport(finalResult);
      }
      
      toast({
        title: "Report Generated",
        description: "Your research report has been generated successfully!",
      });
    },
    // onError callback
    (error) => {
      // Check if this is just a warning about input fields (which shouldn't cause failure)
      const isInputFieldWarning = error && typeof error === 'string' && 
        (error.includes('Not all input fields were provided') || 
         error.includes('input field warnings') ||
         error.includes('Missing:'));
      
      if (isInputFieldWarning) {
        // Don't treat input field warnings as failures
        console.warn('Input field warning (not treating as failure):', error);
        setReportGenerationState(prev => ({
          ...prev,
          progress: prev.progress + ' (with input field warnings - this is normal)',
        }));
        
        toast({
          title: "Generation Note",
          description: "Report generation is proceeding with some input field warnings. This is normal for topic-only generation.",
          variant: "default", // Use default variant instead of destructive
        });
        return; // Don't set error state or stop generation
      }
      
      setReportGenerationState(prev => ({
        ...prev,
        isGenerating: false,
        error: error || 'Report generation failed',
      }));
      
      toast({
        title: "Generation Failed",
        description: error || "Report generation failed. Please try again.",
        variant: "destructive",
      });
    }
  );

  // Real-time job status monitoring using SSE for podcasts
  const { 
    status: podcastJobStatus, 
    progress: podcastJobProgress, 
    result: podcastJobResult, 
    error: podcastJobError, 
    isConnected: podcastIsConnected,
    connectionError: podcastConnectionError,
    cancelJob: podcastWebSocketCancelJob
  } = usePodcastJobStatus(
    podcastGenerationState.jobId,
    // onComplete callback
    async (result) => {
      setPodcastGenerationState(prev => ({
        ...prev,
        isGenerating: false,
        progress: 'Panel discussion generated successfully!',
      }));
      
      // Add the generated podcast to the podcast files list
      if (result && (result.audioUrl || result.generated_files)) {
        await loadGeneratedPodcast(result);
      }
      
      // Also reload the full list to ensure consistency
      await loadExistingPodcasts();
      
      toast({
        title: "Panel Discussion Generated",
        description: "Your panel discussion has been generated successfully!",
      });
    },
    // onError callback
    (error) => {
      setPodcastGenerationState(prev => ({
        ...prev,
        isGenerating: false,
        error: error || 'Panel discussion generation failed',
      }));
      
      toast({
        title: "Generation Failed",
        description: error || "Panel discussion generation failed. Please try again.",
        variant: "destructive",
      });
    }
  );

  // Update local state when job status changes
  useEffect(() => {
    const currentJobId = reportGenerationState.currentJobId;
    
    if (currentJobId) {
      if (jobStatus) {
        setReportGenerationState(prev => {
          // Only update if the current job ID hasn't changed
          if (prev.currentJobId !== currentJobId) return prev;
          
          return {
            ...prev,
            isGenerating: jobStatus === 'running' || jobStatus === 'pending',
          };
        });
        
        // Handle cancelled status
        if (jobStatus === 'cancelled') {
          setReportGenerationState(prev => {
            // Only update if the current job ID hasn't changed
            if (prev.currentJobId !== currentJobId) return prev;
            
            return {
              ...prev,
              isGenerating: false,
              progress: 'Report generation was cancelled',
              error: 'Cancelled',
            };
          });
        }
      }
      
      if (jobProgress) {
        setReportGenerationState(prev => {
          // Only update if the current job ID hasn't changed
          if (prev.currentJobId !== currentJobId) return prev;
          
          return {
            ...prev,
            progress: jobProgress,
          };
        });
      }
      
      if (jobError) {
        setReportGenerationState(prev => {
          // Only update if the current job ID hasn't changed
          if (prev.currentJobId !== currentJobId) return prev;
          
          return {
            ...prev,
            error: jobError,
          };
        });
      }
    }
  }, [jobStatus, jobProgress, jobError]); // Removed reportGenerationState.currentJobId from deps

  // Update local state when podcast job status changes
  useEffect(() => {
    const currentJobId = podcastGenerationState.jobId;
    
    if (currentJobId) {
      if (podcastJobStatus) {
        setPodcastGenerationState(prev => {
          if (prev.jobId !== currentJobId) return prev;
          
          const isGenerating = podcastJobStatus === 'generating' || podcastJobStatus === 'pending';
          const isCancelled = podcastJobStatus === 'cancelled';
          
          return {
            ...prev,
            isGenerating: isGenerating,
            progress: isCancelled ? 'Panel discussion generation was cancelled' : prev.progress,
            error: isCancelled ? 'Cancelled' : prev.error,
          };
        });
      }
      
      if (podcastJobProgress) {
        setPodcastGenerationState(prev => 
          prev.jobId === currentJobId ? { ...prev, progress: podcastJobProgress } : prev
        );
      }
      
      if (podcastJobError) {
        setPodcastGenerationState(prev => 
          prev.jobId === currentJobId ? { ...prev, error: podcastJobError } : prev
        );
      }
    }
  }, [podcastJobStatus, podcastJobProgress, podcastJobError]);

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
      const response = await apiService.listJobs(50); // Load up to 50 recent jobs
      
      if (response && response.jobs) {
        const completedJobs = response.jobs.filter(job => job.status === 'completed');
        console.log('Found completed jobs:', completedJobs);
        
        // Convert completed jobs to files format
        const reportFiles = await Promise.all(
          completedJobs.map(async (job) => {
            try {
              // Try to get the report content and generated files
              let content = `# ${job.article_title || 'Research Report'}\n\nReport generated successfully!`;
              let generatedFiles = [];
              
              try {
                const contentResponse = await apiService.getReportContent(job.job_id);
                if (contentResponse && contentResponse.content) {
                  content = contentResponse.content;
                  // Also get generated files from the content response
                  if (contentResponse.generated_files) {
                    generatedFiles = contentResponse.generated_files;
                  }
                }
              } catch (contentError) {
                console.warn(`Could not load content for job ${job.job_id}:`, contentError);
              }

              // If we still don't have generated files, try the files endpoint
              if (generatedFiles.length === 0) {
                try {
                  const filesResponse = await apiService.listJobFiles(job.job_id);
                  if (filesResponse && filesResponse.files) {
                    generatedFiles = filesResponse.files.map(f => f.filename);
                  }
                } catch (filesError) {
                  console.warn(`Could not load files list for job ${job.job_id}:`, filesError);
                }
              }

              return {
                id: `report-${job.job_id}`,
                name: `${job.article_title || 'Research Report'}.md`,
                content: content,
                jobId: job.job_id,
                generatedFiles: generatedFiles,
                createdAt: job.created_at || new Date().toISOString(),
              };
            } catch (error) {
              console.error(`Error processing job ${job.job_id}:`, error);
              return null;
            }
          })
        );

        // Filter out null results and update files state
        const validReports = reportFiles.filter(report => report !== null);
        if (validReports.length > 0) {
          console.log('Loaded existing reports:', validReports);
          setFiles(validReports);
        }
      }
    } catch (error) {
      console.error('Error loading existing reports:', error);
    }
  };

  const loadGeneratedReport = async (result) => {
    try {
      // Start with default content
      let reportContent = `# ${result.article_title}\n\nReport generated successfully!\n\nOutput directory: ${result.output_directory}\n\nGenerated files:\n${result.generated_files.map(f => `- ${f}`).join('\n')}`;
      
      if (reportGenerationState.currentJobId) {
        try {
          console.log('Attempting to fetch report content for job:', reportGenerationState.currentJobId);
          const contentResponse = await apiService.getReportContent(reportGenerationState.currentJobId);
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
              blob = await apiService.downloadFile(reportGenerationState.currentJobId, 'storm_gen_article_polished.md');
            } catch (directError) {
              console.log('Direct filename failed, trying with subdirectory path');
              // Try with the Research_Report subdirectory path
              blob = await apiService.downloadFile(reportGenerationState.currentJobId, 'Research_Report/storm_gen_article_polished.md');
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
        name: `${result.article_title}.md`,
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
        name: `${result.article_title}.md`,
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
      const response = await apiService.listPodcastJobs();
      
      if (response && response.jobs) {
        const completedJobs = response.jobs.filter(job => job.status === 'completed');
        console.log('Found completed podcast jobs:', completedJobs);
        
        // Convert completed jobs to podcast format
        const podcastList = completedJobs.map((job) => {
          // Extract filename from audio_url or use job_id
          let filename = `${job.job_id}.mp3`;
          if (job.audio_url) {
            const urlParts = job.audio_url.split('/');
            filename = urlParts[urlParts.length - 1];
          }

          return {
            id: `podcast-${job.job_id}`,
            name: filename,
            title: job.title || 'Panel Discussion',
            description: job.description || '',
                            audioUrl: `${config.API_BASE_URL}/podcasts/audio/${filename}`,
            jobId: job.job_id,
            type: 'podcast',
            createdAt: job.created_at || new Date().toISOString(),
            generatedFiles: [],
          };
        });

        if (podcastList.length > 0) {
          console.log('Loaded existing podcasts:', podcastList);
          setPodcastFiles(podcastList);
        }
      }
    } catch (error) {
      console.error('Error loading existing podcasts:', error);
    }
  };

  const loadGeneratedPodcast = async (result) => {
    try {
      console.log('Loading newly generated podcast:', result);
      
      // Extract filename from audio_url or use job_id
      let filename = `${podcastGenerationState.jobId}.mp3`;
      if (result.audio_url) {
        const urlParts = result.audio_url.split('/');
        filename = urlParts[urlParts.length - 1];
      }

      const newPodcast = {
        id: `podcast-${podcastGenerationState.jobId}`,
        name: filename,
        title: podcastGenerationState.title || result.title || 'Panel Discussion',
        description: podcastGenerationState.description || result.description || '',
        audioUrl: `${apiService.baseUrl}/podcasts/audio/${filename}`,
        jobId: podcastGenerationState.jobId,
        type: 'podcast',
        createdAt: new Date().toISOString(),
        generatedFiles: result.generated_files || [],
      };
      
      console.log('Adding new podcast to files list:', newPodcast);
      
      // Check if podcast already exists (avoid duplicates)
      setPodcastFiles(prev => {
        const exists = prev.find(p => p.jobId === podcastGenerationState.jobId);
        if (exists) {
          console.log('Podcast already exists, updating:', exists);
          return prev.map(p => p.jobId === podcastGenerationState.jobId ? newPodcast : p);
        }
        return [newPodcast, ...prev];
      });
      
    } catch (error) {
      console.error('Error loading generated podcast:', error);
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

      // Check if we have files and if they are parsed
      const parsedFiles = hasFiles ? selectedFiles.filter(f => f.file_id) : [];
      const hasParsedFiles = parsedFiles.length > 0;

      if (hasParsedFiles) {
        // Use file-based generation (with or without topic)
        const fileIds = parsedFiles.map(f => f.file_id);
        
        const requestData = {
          topic: hasTopic ? reportConfig.topic : null,
          article_title: reportConfig.article_title,
          model_provider: reportConfig.model_provider,
          retriever: reportConfig.retriever,
          selected_file_ids: fileIds
        };

        console.log('Generating report with selected file IDs:', fileIds, 'and topic:', hasTopic ? reportConfig.topic : 'none');
        response = await apiService.generateReportWithSourceIds(requestData);
      } else if (hasTopic) {
        // Use topic-based generation only
        console.log('Generating report with topic only:', reportConfig.topic);
        response = await apiService.generateReport(reportConfig);
      } else {
        // This should not happen due to validation above, but handle gracefully
        toast({
          title: "No Valid Input",
          description: hasFiles ? "Selected files are not parsed yet. Please wait for parsing to complete or enter a topic." : "Please enter a topic to generate a report.",
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
      // Use WebSocket to cancel the job
      const success = webSocketCancelJob();
      
      if (success) {
        setReportGenerationState(prev => ({
          ...prev,
          isGenerating: false,
          progress: 'Sending cancellation request...',
          error: null,
        }));

        toast({
          title: "Cancellation Requested",
          description: "Cancellation request sent. The job will stop shortly.",
        });
      } else {
        // Fallback to HTTP API if WebSocket is not available
        console.warn('WebSocket cancellation failed, falling back to HTTP API');
        await apiService.cancelJob(reportGenerationState.currentJobId);
        
        setReportGenerationState(prev => ({
          ...prev,
          isGenerating: false,
          progress: 'Report generation cancelled',
          error: 'Cancelled by user',
        }));

        toast({
          title: "Generation Cancelled",
          description: "Report generation has been cancelled.",
        });
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

      const response = await apiService.generatePodcast(formData);
      
      setPodcastGenerationState(prev => ({
        ...prev,
        jobId: response.job_id,
        progress: 'Panel discussion generation started...',
      }));

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
      // Use WebSocket to cancel the job (same as reports)
      const success = podcastWebSocketCancelJob();
      
      if (success) {
        setPodcastGenerationState(prev => ({
          ...prev,
          isGenerating: false,
          progress: 'Sending cancellation request...',
          error: null,
        }));

        toast({
          title: "Cancellation Requested",
          description: "Cancellation request sent. The job will stop shortly.",
        });
      } else {
        // Fallback to HTTP API if WebSocket is not available
        console.warn('WebSocket cancellation failed, falling back to HTTP API');
        await apiService.cancelPodcastJob(podcastGenerationState.jobId);
        
        setPodcastGenerationState(prev => ({
          ...prev,
          isGenerating: false,
          progress: 'Panel discussion generation cancelled',
          error: 'Cancelled',
        }));

        toast({
          title: "Generation Cancelled",
          description: "Panel discussion generation has been cancelled.",
        });
        
        // Refresh podcast list in case there are any state inconsistencies
        setTimeout(() => loadExistingPodcasts(), 1000);
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
      const blob = await apiService.downloadFile(file.jobId, null);
      
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

  const handleDownloadPodcast = async (podcast) => {
    if (!podcast.audioUrl) {
      toast({
        title: "Download Not Available",
        description: "This podcast is not available for download.",
        variant: "destructive",
      });
      return;
    }

    try {
      // Use fetch to download the audio file directly from the API endpoint
      const response = await fetch(podcast.audioUrl);
      if (!response.ok) {
        throw new Error(`Failed to download: ${response.statusText}`);
      }
      
      const blob = await response.blob();
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



  const getStatusIcon = () => {
    if (reportGenerationState.isGenerating) {
      return <RefreshCw className="h-4 w-4 animate-spin" />;
    }
    if (reportGenerationState.error) {
      if (reportGenerationState.error === 'Cancelled' || reportGenerationState.error === 'Cancelled by user') {
        return <X className="h-4 w-4 text-yellow-500" />;
      }
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    }
    return <CheckCircle className="h-4 w-4 text-green-500" />;
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

  const handleFileClick = useCallback((file) => {
    setSelectedFile(file);
    setViewMode("preview");
    setIsEditing(false);
    setIsExpanded(false);
  }, []);

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Simple Header */}
      <div className="flex-shrink-0 px-4 py-3 bg-white border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 bg-gray-100 rounded-md flex items-center justify-center">
              <FileText className="h-3 w-3 text-gray-600" />
            </div>
            <h3 className="text-sm font-medium text-gray-900">Studio</h3>
          </div>
          <div className="flex items-center space-x-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
              onClick={() => {
                loadExistingReports();
                loadExistingPodcasts();
              }}
            >
              Refresh
            </Button>
            {(reportGenerationState.isGenerating || podcastGenerationState.isGenerating) && (
              <span className="text-xs text-gray-500">generating...</span>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Report Generation Status */}
        {(reportGenerationState.isGenerating || reportGenerationState.error || reportGenerationState.progress) && (
          <div className="p-6 border-b border-gray-200">
            <ProgressCard
              title="Generating Report"
              isGenerating={reportGenerationState.isGenerating}
              progress={reportGenerationState.progress}
              error={reportGenerationState.error}
              onCancel={handleCancelGeneration}
              jobId={reportGenerationState.currentJobId}
              showCancel={true}
              isConnected={isConnected}
              connectionError={connectionError}
            />
          </div>
        )}

        {/* Main Generation Sections - Only show when no file is selected */}
        {!selectedFile && (
          <div className="p-6 space-y-6">
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
            />
          </div>
        )}

        {/* Generated Podcasts List */}
        {podcastFiles.length > 0 && !selectedFile && (
          <div className="mx-6 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center">
                    <Play className="h-4 w-4 text-gray-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Generated Panel Discussions</h3>
                    <p className="text-sm text-gray-600">{podcastFiles.length} audio files available</p>
                  </div>
                </div>
              </div>
              <div className="divide-y divide-gray-100">
                {podcastFiles.map((podcast) => (
                  <PodcastListItem
                    key={podcast.id}
                    podcast={podcast}
                    onDownload={handleDownloadPodcast}
                    onMenuToggle={(podcastId) => setActiveMenuFileId(activeMenuFileId === podcastId ? null : podcastId)}
                    isMenuOpen={activeMenuFileId === podcast.id}
                    onDelete={(podcastId) => {
                      setPodcastFiles((prev) => prev.filter((p) => p.id !== podcastId));
                      setActiveMenuFileId(null);
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Generated Files List */}
        {files.length > 0 && !selectedFile && (
          <div className="mx-6 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center">
                    <FileText className="h-4 w-4 text-gray-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Generated Research Reports</h3>
                    <p className="text-sm text-gray-600">{files.length} reports available</p>
                  </div>
                </div>
              </div>
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
            </div>
          </div>
        )}

        {/* Empty State */}
        {!selectedFile && files.length === 0 && podcastFiles.length === 0 && !reportGenerationState.isGenerating && !podcastGenerationState.isGenerating && (
          <div className="flex-1 flex items-center justify-center p-12">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 bg-gray-100 rounded-2xl mx-auto mb-4 flex items-center justify-center">
                <FileText className="h-8 w-8 text-gray-500" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Welcome to AI Studio</h3>
              <p className="text-sm text-gray-500 mb-6">Generate comprehensive research reports and engaging panel discussions from your knowledge base</p>
              <div className="flex flex-wrap gap-2 justify-center">
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs bg-white hover:bg-gray-50 border-gray-300 text-gray-700 hover:text-gray-900"
                  onClick={() => toggleSection('report')}
                >
                  Create Report
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs bg-white hover:bg-gray-50 border-gray-300 text-gray-700 hover:text-gray-900"
                  onClick={() => toggleSection('podcast')}
                >
                  Generate Podcast
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Report Viewer */}
        {selectedFile && (
          <div className="p-6 space-y-6">
            {/* File Navigation Bar */}
            {files.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center">
                      <FileText className="h-4 w-4 text-gray-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">Research Reports</h3>
                      <p className="text-sm text-gray-600">{files.length} reports generated</p>
                    </div>
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleClose}
                    className="text-gray-600 hover:text-gray-900 border-gray-300"
                  >
                    <X className="h-4 w-4 mr-1" />
                    Close
                  </Button>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {files.map((file) => (
                    <button
                      key={file.id}
                      className={`px-4 py-2 text-sm border rounded-lg transition-all duration-200 flex items-center gap-2 ${
                        selectedFile?.id === file.id 
                          ? 'bg-gray-900 border-gray-900 text-white' 
                          : 'bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100 hover:border-gray-300'
                      }`}
                      onClick={() => handleFileClick(file)}
                    >
                      <FileText className="h-3 w-3" />
                      <span className="truncate max-w-[120px]">{file.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            {/* Report Display Panel */}
            <div
              className={`bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col transition-all duration-300 ${
                isExpanded ? "fixed inset-4 z-50" : "min-h-[500px]"
              }`}
            >
              {/* Toolbar */}
              <div className="px-6 py-4 border-b bg-gray-50 rounded-t-xl">
                <div className="flex justify-between items-center">
                  <div className="flex items-center space-x-1">
                    <button
                      className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                        viewMode === "preview"
                          ? "bg-gray-900 text-white"
                          : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                      }`}
                      onClick={() => setViewMode("preview")}
                    >
                      Preview
                    </button>
                    <button
                      className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                        viewMode === "code"
                          ? "bg-gray-900 text-white"
                          : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                      }`}
                      onClick={() => setViewMode("code")}
                    >
                      Source
                    </button>
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
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={handleClose}
                      title="Close Report"
                      className="hover:bg-gray-100 text-gray-600 hover:text-gray-900"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
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

      {/* Simple Footer */}
      {(files.length > 0 || podcastFiles.length > 0) && (
        <div className="flex-shrink-0 p-4 bg-white border-t border-gray-200">
          <div className="text-center text-xs text-gray-500">
            {files.length} reports • {podcastFiles.length} podcasts
          </div>
        </div>
      )}
    </div>
  );
};

export default StudioPanel;