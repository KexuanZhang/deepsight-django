import React, { useState, useRef, useImperativeHandle, forwardRef, useEffect, useCallback, useMemo } from "react";
import { Trash2, Plus, ChevronLeft, RefreshCw, AlertCircle, Upload, Group, File as FileIcon, FileText, Music, Video, Presentation, Loader2, Eye, Database, Link2, Globe, ImageIcon } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/shared/components/ui/button";
import { Alert, AlertDescription } from "@/shared/components/ui/alert";
import { Badge } from "@/shared/components/ui/badge";
import sourceService from "@/features/notebook/services/SourceService";
import { supportsPreview } from "@/features/notebook/utils/filePreview";
import { PANEL_HEADERS, COLORS } from "@/features/notebook/config/uiConfig";
import { FileIcons } from "@/shared/types";
import { Source, SourcesListProps, SourceItemProps } from "@/features/notebook/type";
import { FileMetadata } from "@/shared/types";
import { useFileUploadStatus } from "@/features/notebook/hooks/generation/useFileUploadStatus";
import { useFileStatus } from "@/features/notebook/hooks/generation/useFileStatus";
import AddSourceModal from "./AddSourceModal";

const fileIcons: FileIcons = {
  pdf: FileIcon,
  txt: FileText,
  md: FileText, 
  ppt: Presentation,
  pptx: Presentation,
  docx: FileText,
  mp3: Music,
  mp4: Video,
  wav: Music,
  m4a: Music,
  avi: Video,
  mov: Video,
  mkv: Video,
  webm: Video,
  wmv: Video,
  m4v: Video,
  url: Link2,
  website: Globe,
  media: Video
};

// Component to handle individual file status tracking with SSE
const FileStatusTracker: React.FC<{
  fileId: string;
  notebookId: string;
  onStatusUpdate: (fileId: string, newStatus: string) => void;
  onProcessingComplete: (fileId: string) => void;
  onError: (fileId: string, error: string) => void;
}> = ({ fileId, notebookId, onStatusUpdate, onProcessingComplete, onError }) => {
  
  const { status } = useFileStatus(
    fileId,
    notebookId,
    () => {
      onStatusUpdate(fileId, 'completed');
      onProcessingComplete(fileId);
    },
    (error) => {
      onStatusUpdate(fileId, 'error');
      onError(fileId, error);
    }
  );

  // Update status when it changes (for intermediate status updates)
  useEffect(() => {
    if (status && status !== 'done' && status !== 'error') {
      // Map backend status to frontend status
      const frontendStatus = status === 'pending' ? 'pending' : 
                           status === 'in_progress' ? 'processing' : 
                           status;
      onStatusUpdate(fileId, frontendStatus);
    }
  }, [status, fileId, onStatusUpdate]);

  return null; // This component doesn't render anything
};

// Define ref interface for the SourcesList component
interface SourcesListRef {
  getSelectedFiles: () => Source[];
  getSelectedSources: () => Source[];
  clearSelection: () => void;
  refreshSources: () => Promise<void>;
  startUploadTracking: (uploadFileId: string) => void;
  onProcessingComplete: (completedUploadId?: string) => void;
}

// Helper function to get principle file icon with visual indicator
  const getPrincipleFileIcon = (source: Source): React.ComponentType<any> => {
  // Enhanced URL detection with multiple fallbacks
  const isUrl = source.ext === 'url' || 
                source.metadata?.source_url || 
                source.metadata?.extraction_type === 'url_extractor' ||
                source.metadata?.processing_method === 'media' ||
                source.metadata?.processing_method === 'web_scraping_no_crawl4ai' ||
                source.metadata?.processing_method === 'crawl4ai_only' ||
                source.metadata?.file_extension === '.md' && source.metadata?.original_filename?.includes('_20');
  
  if (isUrl) {
    const processingType = source.metadata?.processing_method || source.metadata?.processing_type;
    return processingType === 'media' ? (fileIcons.media ?? FileIcon) : (fileIcons.website ?? Globe);
  }
  
  // For regular files, use the file extension
  const icon = fileIcons[source.ext || 'unknown'];
  return icon ?? FileIcon;
};


const SourcesList = forwardRef<SourcesListRef, SourcesListProps>(({ notebookId, onSelectionChange, onToggleCollapse, onOpenModal, onCloseModal }, ref) => {
  const [sources, setSources] = useState<Source[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Group state
  const [isGrouped, setIsGrouped] = useState(false);

  // Simple file upload status tracking with completion detection (for new uploads)
  const fileUploadStatus = useFileUploadStatus();
  
  // Set notebook ID for upload tracking
  useEffect(() => {
    fileUploadStatus.setNotebookId(notebookId);
    // Ensure any completion (including caption generation completion events) triggers a refresh
    fileUploadStatus.setOnAnyFileComplete(() => {
      loadParsedFiles();
      if (onSelectionChange) {
        setTimeout(() => onSelectionChange(), 100);
      }
    });
  }, [notebookId, fileUploadStatus]);

  // Individual file status update handler - updates specific file in sources array
  const updateFileStatus = useCallback((fileId: string, newStatus: string) => {
    setSources(prev => prev.map(source => 
      source.file_id === fileId 
        ? { ...source, parsing_status: newStatus as Source['parsing_status'] }
        : source
    ));
  }, []);

  // Load parsed files on component mount (only once)
  useEffect(() => {
    // Only load if we don't have sources already (prevents double loading)
    if (sources.length === 0 && !isLoading) {
      loadParsedFiles();
    }
  }, []); // Keep empty dependency array - only run on mount

  // Get processing files for individual SSE tracking
  const processingFiles = useMemo(() => {
    return sources.filter(source => 
      source.file_id && 
      source.parsing_status && 
      ['pending', 'parsing', 'uploading', 'processing', 'in_progress'].includes(source.parsing_status)
    );
  }, [sources]);



  const loadParsedFiles = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await sourceService.listParsedFiles(notebookId);
      
      // Handle paginated response format {results: [...], count: 0, etc}
      if (response && response.results !== undefined) {
        const data = response.results || [];
        
        const parsedSources = data.map((metadata: FileMetadata) => ({
          id: metadata.file_id || 'unknown',
          name: generatePrincipleTitle(metadata),
          title: generatePrincipleTitle(metadata),
          authors: generatePrincipleFileDescription(metadata),
          ext: getPrincipleFileExtension(metadata),
          selected: false,
          type: "parsed" as const,
          createdAt: metadata.upload_timestamp || new Date().toISOString(),
          file_id: metadata.file_id,
          upload_file_id: metadata.upload_file_id,
          parsing_status: metadata.parsing_status,
          metadata: {
            ...metadata,
            knowledge_item_id: metadata.knowledge_item_id
          },
          error_message: metadata.error_message,
          originalFile: getPrincipleFileInfo(metadata)
        }));
        
        setSources(parsedSources);
        
        fileUploadStatus.stopAllTracking();
      } else {
        throw new Error("Failed to load files - unexpected response format");
      }
    } catch (error) {
      console.error('Error loading parsed files:', error);
      setError(`${error instanceof Error ? error.message : 'Unknown error'}`);
      setSources([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle processing completion for specific files - reload to get fresh data
  const handleFileProcessingComplete = useCallback(() => {
    loadParsedFiles();
    
    if (onSelectionChange) {
      setTimeout(() => onSelectionChange(), 100);
    }
  }, [onSelectionChange]);

  // Handle processing errors for specific files
  const handleFileProcessingError = useCallback((_fileId: string, error: string) => {
    setError(`Processing failed for file: ${error}`);
    loadParsedFiles();
    
    if (onSelectionChange) {
      setTimeout(() => onSelectionChange(), 100);
    }
  }, [onSelectionChange]);

  // Simple helper to get original filename
  const getOriginalFilename = (metadata: FileMetadata) => {
    return metadata.original_filename || 
           metadata.metadata?.original_filename || 
           metadata.metadata?.filename || 
           metadata.filename || 
           metadata.title || 
           'Unknown File';
  };

  // New function to generate description for principle files
  const generatePrincipleFileDescription = (metadata: FileMetadata) => {
    // Enhanced URL detection with multiple fallbacks
    const isUrl = metadata.source_url || 
                  metadata.extraction_type === 'url_extractor' ||
                  metadata.processing_method === 'media' ||
                  metadata.processing_method === 'web_scraping_no_crawl4ai' ||
                  metadata.processing_method === 'crawl4ai_only' ||
                  metadata.file_extension === '.md' && metadata.original_filename?.includes('_20');
    
    if (isUrl) {
      return generateUrlDescription(metadata);
    }
    
    // Show original file information for non-URL sources
    // Try to get original file size from metadata, fallback to various fields
    let originalSize = 'Unknown size';
    if (metadata.file_size) {
      originalSize = `${(metadata.file_size / (1024 * 1024)).toFixed(1)} MB`;
    } else if (metadata.metadata?.file_size) {
      originalSize = `${(metadata.metadata.file_size / (1024 * 1024)).toFixed(1)} MB`;
    } else if (metadata.metadata?.content_length) {
      originalSize = `${(metadata.metadata.content_length / 1000).toFixed(1)}k chars`;
    }
    
    const ext = getPrincipleFileExtension(metadata).toUpperCase();
    
    return `${ext} • ${originalSize}`;
  };

  // New function to generate URL-specific descriptions
  const generateUrlDescription = (metadata: FileMetadata) => {
    const processingType = metadata.processing_method || metadata.processing_type || 'Website';
    const contentLength = metadata.content_length ? `${(metadata.content_length / 1000).toFixed(1)}k chars` : 'Unknown size';
    
    const typeLabel = processingType === 'media' ? 'Media' : 'Website';
    
    return `${typeLabel} • ${contentLength}`;
  };

  // New function to get principle file extension
  const getPrincipleFileExtension = (metadata: FileMetadata) => {
    // Enhanced URL detection with multiple fallbacks
    const isUrl = metadata.source_url || 
                  metadata.extraction_type === 'url_extractor' ||
                  metadata.processing_method === 'media' ||
                  metadata.processing_method === 'web_scraping_no_crawl4ai' ||
                  metadata.processing_method === 'crawl4ai_only' ||
                  metadata.file_extension === '.md' && metadata.original_filename?.includes('_20');
    
    if (isUrl) {
      return 'url';
    }
    
    // Use original file extension, fallback to processed extension
    // Try multiple metadata sources for the file extension
    let originalExt = "unknown";
    if (metadata.file_extension) {
      originalExt = metadata.file_extension.startsWith('.') ? 
                   metadata.file_extension.substring(1) : 
                   metadata.file_extension;
    } else if (metadata.metadata?.file_extension) {
      originalExt = metadata.metadata.file_extension.startsWith('.') ? 
                   metadata.metadata.file_extension.substring(1) : 
                   metadata.metadata.file_extension;
    } else if (metadata.original_filename) {
      const parts = metadata.original_filename.split('.');
      if (parts.length > 1) {
        originalExt = parts.pop() || 'unknown';
      }
    } else if (metadata.metadata?.filename) {
      const parts = metadata.metadata.filename.split('.');
      if (parts.length > 1) {
        originalExt = parts.pop() || 'unknown';
      }
    }
    
    return originalExt.toLowerCase();
  };

  // Helper function to extract domain from URL for better display
  const getDomainFromUrl = (url: string) => {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname.replace('www.', '');
    } catch (error) {
      return 'unknown';
    }
  };

  // New function to generate principle title
  const generatePrincipleTitle = (metadata: FileMetadata) => {
    // Enhanced URL detection with multiple fallbacks
    const isUrl = metadata.source_url || 
                  metadata.extraction_type === 'url_extractor' ||
                  metadata.processing_method === 'media' ||
                  metadata.processing_method === 'web_scraping_no_crawl4ai' ||
                  metadata.processing_method === 'crawl4ai_only' ||
                  metadata.file_extension === '.md' && metadata.original_filename?.includes('_20');
    
    if (isUrl) {
      // For URLs, show domain and title
      const domain = metadata.source_url ? getDomainFromUrl(metadata.source_url) : 'Unknown Domain';
      const title = metadata.title || metadata.metadata?.title || 'Untitled';
      return `${domain} - ${title}`;
    }
    
    // For files, show original filename
    return getOriginalFilename(metadata);
  };

  // New function to get principle file info
  const getPrincipleFileInfo = (metadata: FileMetadata) => {
    return {
      original_filename: getOriginalFilename(metadata),
      file_extension: getPrincipleFileExtension(metadata),
      file_size: metadata.file_size || metadata.metadata?.file_size,
      content_length: metadata.content_length || metadata.metadata?.content_length,
      source_url: metadata.source_url,
      processing_method: metadata.processing_method || metadata.processing_type
    };
  };

  // Calculate selected count
  const selectedCount = sources.filter(source => source.selected).length;

  // Group sources by file type
  const groupSources = useCallback((sourcesToGroup: Source[]) => {
    const grouped = sourcesToGroup.reduce((acc: Record<string, Source[]>, source: Source) => {
      const type = source.ext || 'unknown';
      if (!acc[type]) {
        acc[type] = [];
      }
      acc[type].push(source);
      return acc;
    }, {});

    // Sort groups by type name
    const sortedGroups = Object.keys(grouped)
      .sort()
      .reduce((acc: Record<string, Source[]>, type: string) => {
        acc[type] = grouped[type] || [];
        return acc;
      }, {} as Record<string, Source[]>);

    return sortedGroups;
  }, []);

  // Get processed sources (grouped or not)
  const processedSources = useMemo(() => {
    if (isGrouped) {
      const grouped = groupSources(sources);
      return grouped || {};
    }
    return sources;
  }, [sources, isGrouped, groupSources]);

  // Handle group toggle
  const handleGroupToggle = () => {
    setIsGrouped(prev => !prev);
  };


  // Handle backend completion signals
  const handleProcessingComplete = useCallback((completedUploadId?: string) => {
    if (completedUploadId) {
      fileUploadStatus.stopTracking(completedUploadId);
    }
    
    loadParsedFiles();
  }, [loadParsedFiles, fileUploadStatus]);

  // Manual refresh
  const handleManualRefresh = useCallback(async () => {
    loadParsedFiles();
  }, [loadParsedFiles]);

  // Expose methods to parent components
  useImperativeHandle(ref, (): SourcesListRef => ({
    getSelectedFiles: () => {
      return sources.filter(source => 
        source.selected && 
        (source.file_id || source.file)
      );
    },
    getSelectedSources: () => {
      return sources.filter(source => source.selected);
    },
    clearSelection: () => {
      setSources(prev => prev.map(source => ({ ...source, selected: false })));
    },
    refreshSources: loadParsedFiles,
    startUploadTracking: (uploadFileId: string) => {
      fileUploadStatus.startTracking(uploadFileId);
    },
    // New method for handling processing completion signals
    onProcessingComplete: handleProcessingComplete
  }));

  const toggleSource = useCallback((id: string | number) => {
    setSources((prev) => {
      const newSources = prev.map((source) =>
        source.id === id ? { ...source, selected: !source.selected } : source
      );
      
      return newSources;
    });
  }, []);

  // Reusable SourceItem component for consistent rendering - Memoized to prevent unnecessary re-renders
  const SourceItem = React.memo<SourceItemProps>(({ source, onToggle, onPreview, getSourceTooltip, getPrincipleFileIcon, renderFileStatus }) => {
    const handleItemClick = useCallback((e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      onToggle(String(source.id));
    }, [onToggle]);

    const handlePreviewClick = useCallback((e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      onPreview(source);
    }, [onPreview, source]);

    return (
      <div
        className={`px-4 py-3 border-b border-gray-100 cursor-pointer ${
          source.selected ? 'bg-red-50 border-red-200' : ''
        }`}
        onClick={handleItemClick}
      >
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0">
            <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
              {React.createElement(getPrincipleFileIcon(source), {
                className: "h-4 w-4 text-gray-600"
              })}
            </div>
          </div>
          
          <div className="min-w-0 flex-1">
            <div className="flex items-center space-x-2 mb-1">
              <h4 className="text-sm font-medium text-gray-900 truncate">{source.title}</h4>
              {renderFileStatus(source)}
            </div>
            <p className="text-xs text-gray-500 truncate">{source.authors}</p>
          </div>
          
          <div className="flex items-center space-x-2">
            {supportsPreview(source.metadata?.file_extension || source.ext || '', source.metadata || {}) && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-gray-400"
                onClick={handlePreviewClick}
                title={getSourceTooltip(source)}
              >
                <Eye className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  });
  
  // Separate effect to handle selection change notifications - optimized to prevent flashing
  const selectedIds = useMemo(() => sources.filter(s => s.selected).map(s => s.id), [sources]);
  const selectedIdsString = useMemo(() => selectedIds.join(','), [selectedIds]);
  
  useEffect(() => {
    if (onSelectionChange) {
      // Debounce the callback to prevent excessive calls and reduce flashing
      const timer = setTimeout(() => onSelectionChange(), 50);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [selectedIdsString, onSelectionChange]); // Use string comparison to avoid array reference changes

  const handleDeleteSelected = async (): Promise<void> => {
    const selectedSources = sources.filter(source => source.selected);
    
    if (selectedSources.length === 0) {
      return;
    }

    
    const deletionResults = [];
    const unlinkedKnowledgeItems = [];
    for (const source of selectedSources) {
      try {
        let result;
        let knowledgeItemId = null;
        
        console.log('Attempting to delete source:', source);
        
        if (source.metadata?.knowledge_item_id) {
          knowledgeItemId = source.metadata.knowledge_item_id;
          console.log('Deleting by metadata knowledge_item_id:', knowledgeItemId);
          result = await sourceService.deleteParsedFile(source.metadata.knowledge_item_id, notebookId);
        } else if (source.file_id) {
          knowledgeItemId = source.file_id;
          console.log('Deleting by file_id:', knowledgeItemId);
          result = await sourceService.deleteParsedFile(source.file_id, notebookId);
        } else if (source.upload_file_id) {
          console.log('Deleting by upload_file_id:', source.upload_file_id);
          result = await sourceService.deleteFileByUploadId(source.upload_file_id, notebookId);
          fileUploadStatus.stopTracking(source.upload_file_id);
        } else {
          console.warn('Source has no valid ID for deletion:', source);
          continue;
        }
        
        console.log('Delete result:', result);
        
        if (result.success) {
          deletionResults.push({ source, success: true });
          if (knowledgeItemId) {
            unlinkedKnowledgeItems.push(knowledgeItemId);
          }
        } else {
          deletionResults.push({ source, success: false, error: result.error });
        }
      } catch (error) {
        console.error(`Error deleting file ${source.title}:`, error);
        deletionResults.push({ source, success: false, error: error instanceof Error ? error.message : 'Unknown error' });
      }
    }
    
    const successfullyDeleted = deletionResults
      .filter(result => result.success)
      .map(result => result.source.id);
    
    setSources((prev) => prev.filter((source) => !successfullyDeleted.includes(source.id)));
    
    if (unlinkedKnowledgeItems.length > 0 && onSelectionChange) {
      setTimeout(() => {
        onSelectionChange();
      }, 100);
    }
    
    const failedDeletions = deletionResults.filter(result => !result.success);
    if (failedDeletions.length > 0) {
      const errorMessage = `Failed to delete ${failedDeletions.length} file(s): ${failedDeletions.map(f => f.source.title).join(', ')}`;
      setError(errorMessage);
    }
  };


  const handleAddSource = (): void => {
    if (onOpenModal) {
      const modalContent = (
        <AddSourceModal
          onClose={() => onCloseModal?.('addSourceModal')}
          notebookId={notebookId}
          onSourcesAdded={() => {
            loadParsedFiles();
            if (onSelectionChange) {
              setTimeout(() => onSelectionChange(), 100);
            }
          }}
          onUploadStarted={(uploadFileId: string, filename: string, fileType: string, oldUploadFileId?: string) => {
            if (oldUploadFileId) {
              console.log(`SourcesList: Updating source from ${oldUploadFileId} to ${uploadFileId}`);
              // Update existing temp source with real file_id
              setSources(prev => prev.map(source => 
                source.id === oldUploadFileId ? {
                  ...source,
                  id: uploadFileId,
                  file_id: uploadFileId, // Update to real file_id for tracking
                  upload_file_id: uploadFileId
                } : source
              ));
              
              // Stop tracking old ID and start tracking new ID
              fileUploadStatus.stopTracking(oldUploadFileId);
              fileUploadStatus.startTracking(uploadFileId, notebookId, () => {
                handleProcessingComplete(uploadFileId);
              });
            } else {
              // Add new temporary upload item to sources list
              const tempSource: Source = {
                id: uploadFileId,
                file_id: uploadFileId, // Use uploadFileId as file_id for tracking
                name: filename,
                title: filename,
                authors: `${fileType.toUpperCase()} • Processing...`,
                ext: fileType,
                selected: false,
                type: "parsed" as const,
                createdAt: new Date().toISOString(),
                upload_file_id: uploadFileId,
                parsing_status: 'processing',
                metadata: {
                  filename: filename,
                  file_extension: `.${fileType}`
                }
              };
              
              setSources(prev => [tempSource, ...prev]);
              
              fileUploadStatus.startTracking(uploadFileId, notebookId, () => {
                handleProcessingComplete(uploadFileId);
              });
            }
          }}
          onKnowledgeBaseItemsDeleted={() => {
            loadParsedFiles();
          }}
        />
      );
      onOpenModal('addSourceModal', modalContent);
    }
  };



  const renderFileStatus = (source: Source): React.ReactNode => {
    const isProcessing = source.parsing_status && ['pending', 'parsing', 'uploading', 'processing', 'in_progress'].includes(source.parsing_status);
    const isFailed = source.parsing_status === 'failed' || source.parsing_status === 'error';
    
    // Check if this is a file with images and caption generation status
    const captionGenerationStatus = source.metadata?.file_metadata?.caption_generation_status || source.metadata?.caption_generation_status;
    const hasImages = (source.metadata?.file_metadata?.image_count && source.metadata.file_metadata.image_count > 0) || 
                      (source.metadata?.image_count && source.metadata.image_count > 0);
    const imagesRequiringCaptions = source.metadata?.file_metadata?.images_requiring_captions || source.metadata?.images_requiring_captions;
    
    
    // Show caption generation status for completed files with images
    const showCaptionStatus = source.parsing_status === 'completed' && 
                              hasImages && 
                              captionGenerationStatus && 
                              ['pending', 'in_progress'].includes(captionGenerationStatus);
    
    if (isProcessing) {
      return (
        <div className="flex items-center space-x-1">
          <Loader2 className="h-3 w-3 text-red-600 animate-spin" />
          <span className="text-xs text-gray-500">
            {source.parsing_status === 'uploading' ? 'Uploading...' : 
             source.parsing_status === 'pending' ? 'Queued...' : 
             source.parsing_status === 'processing' ? 'Processing...' :
             source.parsing_status === 'in_progress' ? 'Processing...' :
             'Parsing...'}
          </span>
        </div>
      );
    }
    
    if (isFailed) {
      return (
        <div className="flex items-center space-x-1">
          <AlertCircle className="h-3 w-3 text-red-500" />
          <span className="text-xs text-red-500">
            {source.parsing_status === 'error' ? 'Error' : 'Failed'}
          </span>
        </div>
      );
    }
    
    // Show caption generation status for files with images
    if (showCaptionStatus) {
      return (
        <div className="flex items-center space-x-1" title={`Generating captions for ${imagesRequiringCaptions || "multiple"} images`}>
          <ImageIcon className="h-3 w-3 text-blue-500" />
          <Loader2 className="h-3 w-3 text-blue-500 animate-spin" />
          <span className="text-xs text-blue-500">
            {captionGenerationStatus === 'pending' ? 'Captions queued' : 'Generating captions...'}
          </span>
        </div>
      );
    }
    
    return null;
  };

  // Get tooltip text for source items
  const getSourceTooltip = (source: Source): string => {
    // Enhanced URL detection with multiple fallbacks
    const isUrl = source.metadata?.source_url || 
                  source.metadata?.extraction_type === 'url_extractor' ||
                  source.metadata?.processing_method === 'media' ||
                  source.metadata?.processing_method === 'web_scraping_no_crawl4ai' ||
                  source.metadata?.processing_method === 'crawl4ai_only' ||
                  source.metadata?.file_extension === '.md' && source.metadata?.original_filename?.includes('_20');
    
    if (isUrl) {
      const originalUrl = source.originalFile?.sourceUrl || 
                         source.metadata?.source_url || 
                         (source.metadata?.original_filename?.includes('_20') ? 
                           `https://${source.metadata.original_filename.match(/^([^_]+)/)?.[1] || 'unknown'}` : 
                           'Unknown URL');
      return `Original URL: ${originalUrl}`;
    }
    return `Original file: ${source.originalFile?.filename || source.title || ''}`;
  };

  // Handle opening file preview
  const handlePreviewFile = (source: Source) => {
    if (!onOpenModal) {
      console.log('Modal system not available, preview requested for source:', source.title);
      return;
    }

    // Import FilePreview component dynamically
    import("@/features/notebook/components/shared/FilePreview").then(({ default: FilePreview }) => {
      const previewContent = (
        <FilePreview
          source={{
            id: String(source.id),
            name: source.name || source.title || 'Unknown',
            type: source.type as 'file' | 'url' | 'text',
            createdAt: source.createdAt || new Date().toISOString(),
            content: source.content,
            url: source.url,
            metadata: source.metadata,
            selected: source.selected,
            file_id: source.file_id,
            title: source.title,
            ext: source.ext
          }}
          isOpen={true}
          onClose={() => onCloseModal?.('filePreview')}
          notebookId={notebookId}
          useMinIOUrls={true}
        />
      );
      onOpenModal('filePreview', previewContent);
    }).catch((error) => {
      console.error('Failed to load FilePreview component:', error);
    });
  };



  return (
    <div className={`h-full flex flex-col ${COLORS.panels.commonBackground} min-h-0`}>
      {/* Header */}
      <div className={`${PANEL_HEADERS.container} ${PANEL_HEADERS.separator} flex-shrink-0`}>
        <div className={PANEL_HEADERS.layout}>
          <div className={PANEL_HEADERS.titleContainer}>
            <div className={PANEL_HEADERS.iconContainer}>
              <Database className={PANEL_HEADERS.icon} />
            </div>
            <h3 className={PANEL_HEADERS.title}>Sources</h3>
          </div>
          <div className={PANEL_HEADERS.actionsContainer}>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-gray-400 hover:text-gray-600"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                handleManualRefresh();
              }}
              disabled={isLoading}
              title="Manual refresh (auto-updates via SSE)"
            >
              <RefreshCw className={`h-3 w-3 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                handleGroupToggle();
              }}
            >
              <Group className="h-3 w-3 mr-1" />
              Group
            </Button>
            {onToggleCollapse && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-gray-400 hover:text-gray-600"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onToggleCollapse();
                }}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            )}
            {isLoading && (
              <RefreshCw className="h-4 w-4 animate-spin text-gray-400" />
            )}
            {(() => {
              const processingCount = sources.filter(s => 
                s.parsing_status && ['pending', 'parsing', 'uploading', 'processing', 'in_progress'].includes(s.parsing_status)
              ).length;
              
              if (processingCount > 0) {
                return (
                  <div className="h-2 w-2 bg-blue-500 rounded-full animate-pulse" 
                       title={`${processingCount} files processing - SSE listening for completion`} />
                );
              }
              
              return (
                <div className="h-2 w-2 bg-green-500 rounded-full" 
                     title="All files processed - SSE ready" />
              );
            })()}
          </div>
        </div>
      </div>

      {/* Add Source Button */}
      <div className="flex-shrink-0 px-4 py-3 bg-white border-b border-gray-200 flex justify-center">
        <Button
          variant="default"
          size="sm"
          className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-full transition-colors text-sm"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            handleAddSource();
          }}
          disabled={isLoading}
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Source
        </Button>
      </div>

      {/* Error Display with unified styling */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex-shrink-0 p-4 border-b border-gray-200"
          >
            <Alert variant="destructive" className="border-red-200 bg-red-50">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-sm text-red-800">
                {error}
                <Button
                  variant="ghost"
                  size="sm"
                  className="ml-2 h-6 px-2 text-red-600 hover:text-red-800"
                  onClick={() => setError(null)}
                >
                  Dismiss
                </Button>
              </AlertDescription>
            </Alert>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Simple Selection Bar */}
      {sources.length > 0 && (
        <div className="flex-shrink-0 px-4 py-3 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  const allSelected = sources.length > 0 && selectedCount === sources.length;
                  setSources((prev) => prev.map((s) => ({ ...s, selected: !allSelected })));
                }}
                disabled={sources.length === 0}
              >
                {sources.length > 0 && selectedCount === sources.length ? 'Deselect All' : 'Select All'}
              </Button>
            </div>
            
            <Button
              variant="ghost"
              size="sm"
              className={`h-6 px-2 text-xs transition-colors ${
                selectedCount > 0 
                  ? 'text-gray-500 hover:text-red-600' 
                  : 'text-gray-300 cursor-not-allowed'
              }`}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                if (selectedCount > 0) {
                  handleDeleteSelected();
                }
              }}
              disabled={selectedCount === 0}
            >
              <Trash2 className="h-3 w-3 mr-1" />
              Remove
            </Button>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 min-h-0 overflow-y-auto relative">
        <AnimatePresence mode="wait">
          {isGrouped ? (
            // Grouped rendering with unified styling
            <motion.div
              key="grouped"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {Object.entries(processedSources as Record<string, Source[]>).map(([type, groupSources]: [string, Source[]]) => (
                <motion.div 
                  key={type}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                >
                  <div className="px-4 py-2 bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200 sticky top-0">
                    <div className="flex items-center space-x-2">
                      <div className="w-5 h-5 bg-gray-200 rounded-md flex items-center justify-center">
                        {React.createElement(fileIcons[type] || FileIcon, {
                          className: "h-3 w-3 text-gray-600"
                        })}
                      </div>
                      <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                        {type.toUpperCase()}
                      </h4>
                      <Badge variant="outline" className="text-xs bg-white border-gray-300">
                        {groupSources.length}
                      </Badge>
                    </div>
                  </div>
                  {groupSources.map((source: Source) => (
                    <SourceItem
                      key={`source-${source.id}-${source.file_id || source.upload_file_id}`}
                      source={source}
                      onToggle={() => toggleSource(source.id)}
                      onPreview={() => handlePreviewFile(source)}
                      getSourceTooltip={getSourceTooltip}
                      getPrincipleFileIcon={getPrincipleFileIcon}
                      renderFileStatus={renderFileStatus}
                    />
                  ))}
                </motion.div>
              ))}
            </motion.div>
          ) : (
            // Ungrouped rendering with unified styling
            <motion.div
              key="ungrouped"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {(processedSources as Source[]).map((source: Source) => (
                <SourceItem
                  key={`source-${source.id}-${source.file_id || source.upload_file_id}`}
                  source={source}
                  onToggle={() => toggleSource(source.id)}
                  onPreview={() => handlePreviewFile(source)}
                  getSourceTooltip={getSourceTooltip}
                  getPrincipleFileIcon={getPrincipleFileIcon}
                  renderFileStatus={renderFileStatus}
                />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Empty/Loading States */}
        {!isLoading && sources.length === 0 && (
          <div className="p-8 text-center">
            <div className="w-12 h-12 bg-white rounded-lg mx-auto mb-3 flex items-center justify-center">
              <Upload className="h-6 w-6 text-gray-400" />
            </div>
            <h3 className="text-sm font-medium text-gray-900 mb-1">No files yet</h3>
            <p className="text-xs text-gray-500">Add files to get started</p>
          </div>
        )}
        
        {isLoading && sources.length === 0 && (
          <div className="p-8 text-center">
            <RefreshCw className="h-6 w-6 text-gray-400 animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500">Loading...</p>
          </div>
        )}
      </div>

      {/* Individual file status trackers - hidden components that handle SSE for each processing file */}
      {processingFiles.map(file => (
        <FileStatusTracker
          key={`status-tracker-${file.file_id}`}
          fileId={file.file_id!}
          notebookId={notebookId}
          onStatusUpdate={updateFileStatus}
          onProcessingComplete={() => handleFileProcessingComplete()}
          onError={handleFileProcessingError}
        />
      ))}
    </div>
  );
});

export default SourcesList;