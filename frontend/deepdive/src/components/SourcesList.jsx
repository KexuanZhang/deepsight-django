import React, { useState, useRef, useImperativeHandle, forwardRef, useEffect, useCallback, useMemo } from "react";
import { ArrowUpDown, Trash2, Plus, ChevronLeft, RefreshCw, CheckCircle, AlertCircle, Clock, X, Upload, Link2, FileText, Globe, Youtube, Group, File, Music, Video, Presentation, Loader2, Eye, ChevronsUp } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import apiService from "@/lib/api";
import FilePreview from "./FilePreview";
import { supportsPreview } from "@/lib/filePreview";

const fileIcons = {
  pdf: File,
  txt: FileText,
  md: FileText, 
  ppt: Presentation,
  pptx: Presentation,
  mp3: Music,
  mp4: Video,
  wav: Music,
  url: Link2,
  website: Globe,
  media: Video
};

// --- NEW: builds the SSE URL for a single upload ---
function buildStatusUrl(notebookId, uploadFileId) {
  if (typeof notebookId !== 'string' && typeof notebookId !== 'number') {
    console.error("Invalid notebookId passed to buildStatusUrl:", notebookId);
    throw new Error("notebookId must be a string or number");
  }
  return `/api/v1/notebooks/${notebookId}/files/${uploadFileId}/status/stream`;
}

// Helper function to get principle file icon with visual indicator
const getPrincipleFileIcon = (source) => {
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
    return processingType === 'media' ? fileIcons.media : fileIcons.website;
  }
  
  // For regular files, use the file extension
  return fileIcons[source.ext] || File;
};

const statusConfig = {
  pending: { icon: Clock, color: "text-yellow-500", bg: "bg-yellow-50", label: "Queued" },
  parsing: { icon: RefreshCw, color: "text-blue-500", bg: "bg-blue-50", label: "Processing", animate: true },
  completed: { icon: CheckCircle, color: "text-green-500", bg: "bg-green-50", label: "Completed" },
  error: { icon: AlertCircle, color: "text-red-500", bg: "bg-red-50", label: "Failed" },
  cancelled: { icon: X, color: "text-gray-500", bg: "bg-gray-50", label: "Cancelled" },
  unsupported: { icon: AlertCircle, color: "text-orange-500", bg: "bg-orange-50", label: "Unsupported" }
};

const SourcesList = forwardRef(({ notebookId, onSelectionChange, onToggleCollapse, isCollapsed, ...props }, ref) => {
  const [sources, setSources] = useState([]);

  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const fileInputRef = useRef(null);
  
  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [linkUrl, setLinkUrl] = useState('');
  const [pasteText, setPasteText] = useState('');
  const [activeTab, setActiveTab] = useState('file'); // 'file', 'link', 'text'
  const [urlProcessingType, setUrlProcessingType] = useState('website'); // 'website' or 'media'

  // Sort and group state
  const [sortOrder, setSortOrder] = useState('newest'); // 'newest' or 'oldest'
  const [isGrouped, setIsGrouped] = useState(false);

  // Preview state
  const [previewSource, setPreviewSource] = useState(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  // SSE connections for status updates
  const sseConnectionsRef = useRef(new Map());

  // Load parsed files on component mount (only once)
  useEffect(() => {
    // Only load if we don't have sources already (prevents double loading)
    if (sources.length === 0 && !isLoading) {
      loadParsedFiles();
    }
    
    // Cleanup SSE connections on unmount
    return () => {
      sseConnectionsRef.current.forEach((eventSource) => {
        eventSource.close();
      });
      sseConnectionsRef.current.clear();
    };
  }, []); // Keep empty dependency array - only run on mount

  const loadParsedFiles = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await apiService.listParsedFiles(notebookId);
      console.log(response)
      
      if (response.success) {
        const parsedSources = response.data.map(metadata => ({
          id: metadata.file_id,
          title: generatePrincipleTitle(metadata), // Generate appropriate title based on source type
          authors: generatePrincipleFileDescription(metadata), // Use principle file description
          ext: getPrincipleFileExtension(metadata), // Get original file extension
          selected: false,
          type: "parsed",
          file_id: metadata.file_id,
          upload_file_id: metadata.upload_file_id,
          parsing_status: metadata.parsing_status,
          metadata: metadata,
          error_message: metadata.error_message,
          // Store both original and processed info for processing
          originalFile: getPrincipleFileInfo(metadata)
        }));
        
        setSources(parsedSources);
      } else {
        throw new Error(response.error || "Failed to load files");
      }
    } catch (error) {
      console.error('Error loading parsed files:', error);
      setError(`Failed to load files: ${error.message}`);
      setSources([]);
    } finally {
      setIsLoading(false);
    }
  };

  // New function to generate description for principle files
  const generatePrincipleFileDescription = (metadata) => {
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
    const originalSize = metadata.file_size ? `${(metadata.file_size / (1024 * 1024)).toFixed(1)} MB` : 'Unknown size';
    const ext = getPrincipleFileExtension(metadata).toUpperCase();
    
    return `${ext} • ${originalSize}`;
  };

  // New function to generate URL-specific descriptions
  const generateUrlDescription = (metadata) => {
    const processingType = metadata.processing_method || metadata.processing_type || 'Website';
    const contentLength = metadata.content_length ? `${(metadata.content_length / 1000).toFixed(1)}k chars` : 'Unknown size';
    
    const typeLabel = processingType === 'media' ? 'Media' : 'Website';
    
    return `${typeLabel} • ${contentLength}`;
  };

  // New function to get principle file extension
  const getPrincipleFileExtension = (metadata) => {
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
    const originalExt = metadata.file_extension?.substring(1) || 
                       metadata.original_filename?.split('.').pop() || 
                       "unknown";
    return originalExt.toLowerCase();
  };

  const generateFileDescription = (metadata) => {
    // Keep this for backward compatibility, but now it calls the principle version
    return generatePrincipleFileDescription(metadata);
  };

  // Helper function to extract domain from URL for better display
  const getDomainFromUrl = (url) => {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname.replace('www.', '');
    } catch (error) {
      // If URL parsing fails, try to extract manually
      const match = url.match(/^https?:\/\/(?:www\.)?([^\/]+)/);
      return match ? match[1] : url;
    }
  };

  // Generate appropriate title based on source type
  const generatePrincipleTitle = (metadata) => {
    // Enhanced URL detection with multiple fallbacks
    const isUrl = metadata.source_url || 
                  metadata.extraction_type === 'url_extractor' ||
                  metadata.processing_method === 'media' ||
                  metadata.processing_method === 'web_scraping_no_crawl4ai' ||
                  metadata.processing_method === 'crawl4ai_only' ||
                  metadata.file_extension === '.md' && metadata.original_filename?.includes('_20');
    
    if (isUrl) {
      const sourceUrl = metadata.source_url || metadata.original_filename;
      if (sourceUrl && sourceUrl.startsWith('http')) {
        return getDomainFromUrl(sourceUrl);
      }
      // Try to extract domain from filename pattern like "example.com_20250101_123456.md"
      if (metadata.original_filename && metadata.original_filename.includes('_20')) {
        const domainMatch = metadata.original_filename.match(/^([^_]+)_\d{8}_\d{6}\.md$/);
        if (domainMatch) {
          return domainMatch[1];
        }
      }
      // Fallback to domain extraction from filename if it looks like a URL
      return sourceUrl || 'Website Content';
    }
    
    // For regular files, show the original filename
    return metadata.original_filename || metadata.filename || 'Unknown File';
  };

  // Get principle file information based on source type
  const getPrincipleFileInfo = (metadata) => {
    // Enhanced URL detection with multiple fallbacks
    const isUrl = metadata.source_url || 
                  metadata.extraction_type === 'url_extractor' ||
                  metadata.processing_method === 'media' ||
                  metadata.processing_method === 'web_scraping_no_crawl4ai' ||
                  metadata.processing_method === 'crawl4ai_only' ||
                  metadata.file_extension === '.md' && metadata.original_filename?.includes('_20');
    
    if (isUrl) {
      // For URL sources, try to extract the original URL
      let sourceUrl = metadata.source_url;
      
      // If no source_url, try to reconstruct from filename pattern
      if (!sourceUrl && metadata.original_filename?.includes('_20')) {
        const domainMatch = metadata.original_filename.match(/^([^_]+)_\d{8}_\d{6}\.md$/);
        if (domainMatch) {
          sourceUrl = `https://${domainMatch[1]}`;
        }
      }
      
      return {
        filename: sourceUrl || metadata.original_filename,
        extension: '.url',
        size: metadata.content_length || 0,
        uploadTimestamp: metadata.upload_timestamp,
        sourceUrl: sourceUrl,
        processingType: metadata.processing_method || metadata.processing_type || 'website'
      };
    } else {
      // For regular files
      return {
        filename: metadata.original_filename || metadata.filename,
        extension: metadata.file_extension,
        size: metadata.file_size,
        uploadTimestamp: metadata.upload_timestamp
      };
    }
  };

  // Calculate selected count
  const selectedCount = sources.filter(source => source.selected).length;

  // Sort sources by time added
  const sortSources = useCallback((sourcesToSort, order) => {
    return [...sourcesToSort].sort((a, b) => {
      // Use file_id or id as a proxy for time added (larger = newer)
      const aTime = a.file_id || a.id || 0;
      const bTime = b.file_id || b.id || 0;
      
      if (order === 'newest') {
        return bTime > aTime ? 1 : -1; // Newer first
      } else {
        return aTime > bTime ? 1 : -1; // Older first
      }
    });
  }, []);

  // Group sources by file type
  const groupSources = useCallback((sourcesToGroup) => {
    const grouped = sourcesToGroup.reduce((acc, source) => {
      const type = source.ext || 'unknown';
      if (!acc[type]) {
        acc[type] = [];
      }
      acc[type].push(source);
      return acc;
    }, {});

    // Sort groups by type name and sort sources within each group
    const sortedGroups = Object.keys(grouped)
      .sort()
      .reduce((acc, type) => {
        acc[type] = sortSources(grouped[type], sortOrder);
        return acc;
      }, {});

    return sortedGroups;
  }, [sortOrder, sortSources]);

  // Get processed sources (sorted and/or grouped)
  const processedSources = useMemo(() => {
    const sorted = sortSources(sources, sortOrder);
    return isGrouped ? groupSources(sorted) : sorted;
  }, [sources, sortOrder, isGrouped, sortSources, groupSources]);

  // Handle sort toggle
  const handleSortToggle = () => {
    setSortOrder(prev => prev === 'newest' ? 'oldest' : 'newest');
  };

  // Handle group toggle
  const handleGroupToggle = () => {
    setIsGrouped(prev => !prev);
  };

  // Start SSE monitoring for file/URL status
  const startStatusMonitoring = useCallback((uploadFileId, sourceId, isUrl = false) => {
    // Don't start multiple connections for the same file/URL
    if (sseConnectionsRef.current.has(uploadFileId)) {
      return;
    }

    const onMessage = (data) => {
      console.log('SSE status update received:', data);
      
      if (data.error) {
        console.error('SSE status error:', data.error);
        return;
      }

      const { status, job_details } = data;
      
      // Update progress if available
      if (job_details?.progress_percentage !== undefined) {
        setUploadProgress(prev => ({
          ...prev,
          [uploadFileId]: job_details.progress_percentage
        }));
      }
      
      // Update source status
      setSources(prev => prev.map(source => 
        source.id === sourceId ? {
          ...source,
          parsing_status: status,
          authors: job_details ? 
            generateFileDescription({
              ...source.metadata,
              parsing_status: status,
              content_length: job_details.result?.content_length || source.metadata?.content_length
            }) : 
            source.authors,
          metadata: job_details?.result?.metadata || source.metadata,
          error_message: job_details?.error
        } : source
      ));
      
      // Close SSE connection if parsing is complete
      if (['completed', 'error', 'cancelled', 'unsupported'].includes(status)) {
        const eventSource = sseConnectionsRef.current.get(uploadFileId);
        if (eventSource) {
          eventSource.close();
          sseConnectionsRef.current.delete(uploadFileId);
        }
        
        // Clear upload progress
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[uploadFileId];
          return newProgress;
        });
        
        // If completed successfully, reload the file list to get updated data
        if (status === 'completed') {
          setTimeout(loadParsedFiles, 1000);
        }
      }
    };

    const onError = (error) => {
      console.error('SSE connection error for', uploadFileId, ':', error);
      
      // Close and remove the connection
      const eventSource = sseConnectionsRef.current.get(uploadFileId);
      if (eventSource) {
        eventSource.close();
        sseConnectionsRef.current.delete(uploadFileId);
      }
      
      // Update source to show error after connection failure
      setSources(prev => prev.map(source => 
        source.id === sourceId ? {
          ...source,
          parsing_status: "error",
          authors: source.authors.replace(/Processing|Queued/, "Connection Failed"),
          error_message: "Lost connection to server during processing"
        } : source
      ));
      
      // Clear progress
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[uploadFileId];
        return newProgress;
      });
    };

    const onClose = () => {
      console.log('SSE connection closed for', uploadFileId);
      sseConnectionsRef.current.delete(uploadFileId);
    };

    try {
      // Create SSE connection
      const eventSource = apiService.createParsingStatusStream(uploadFileId, onMessage, onError, onClose);
      sseConnectionsRef.current.set(uploadFileId, eventSource);
      console.log('SSE connection established for', uploadFileId);
    } catch (error) {
      console.error('Failed to create SSE connection for', uploadFileId, ':', error);
      onError(error);
    }
  }, []);

  // Polling for URL status (fallback when SSE is not available)
  const startUrlStatusPolling = useCallback((uploadUrlId, sourceId) => {
    const pollStatus = async () => {
      try {
        const response = await apiService.getUrlParsingStatus(uploadUrlId);
        if (response.success) {
          const { data } = response;
          const status = data.status;
          
          // Update source status
          setSources(prev => prev.map(source => 
            source.id === sourceId ? {
              ...source,
              parsing_status: status,
              authors: source.authors.replace(/Processing|Parsing/, 
                status === 'completed' ? 'Completed' : 
                status === 'error' ? 'Failed' : 'Processing'
              ),
              metadata: data.metadata || source.metadata,
              error_message: status === 'error' ? 'Processing failed' : undefined
            } : source
          ));
          
          // Stop polling if complete
          if (['completed', 'error', 'cancelled', 'failed'].includes(status)) {
            setUploadProgress(prev => {
              const newProgress = { ...prev };
              delete newProgress[uploadUrlId];
              return newProgress;
            });
            return; // Stop polling
          }
        }
      } catch (error) {
        console.error('URL status polling error:', error);
        // Update source to show error
        setSources(prev => prev.map(source => 
          source.id === sourceId ? {
            ...source,
            parsing_status: "error",
            authors: source.authors.replace(/Processing|Parsing/, 'Failed'),
            error_message: 'Connection failed during processing'
          } : source
        ));
        
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[uploadUrlId];
          return newProgress;
        });
        return; // Stop polling
      }
      
      // Continue polling after 2 seconds
      setTimeout(pollStatus, 2000);
    };
    
    // Start polling after initial delay
    setTimeout(pollStatus, 2000);
  }, []);

  // Expose methods to parent components
  useImperativeHandle(ref, () => ({
    getSelectedFiles: () => {
      return sources.filter(source => 
        source.selected && 
        (source.file_id || source.file) && 
        source.parsing_status === 'completed'
      );
    },
    getSelectedSources: () => {
      return sources.filter(source => source.selected);
    },
    clearSelection: () => {
      setSources(prev => prev.map(source => ({ ...source, selected: false })));
    },
    refreshSources: loadParsedFiles
  }));

  const toggleSource = (id) => {
    setSources((prev) => {
      const newSources = prev.map((source) =>
        source.id === id ? { ...source, selected: !source.selected } : source
      );
      
      // Notify parent component about selection change
      if (onSelectionChange) {
        // Use setTimeout to ensure state update is complete
        setTimeout(() => onSelectionChange(), 0);
      }
      
      return newSources;
    });
  };

  const handleDeleteSelected = async () => {
    const selectedSources = sources.filter(source => source.selected);
    
    if (selectedSources.length === 0) {
      return;
    }

    if (!confirm(`Are you sure you want to delete ${selectedSources.length} selected source(s)?`)) {
      return;
    }
    
    console.log('Deleting selected sources:', selectedSources);
    
    // Track which deletions succeed
    const deletionResults = [];
    
    // Delete files from backend
    for (const source of selectedSources) {
      try {
        console.log('Attempting to delete source:', source);
        
        let result;
        if (source.upload_file_id) {
          console.log('Using deleteFileByUploadId for:', source.upload_file_id);
          result = await apiService.deleteFileByUploadId(source.upload_file_id);
          
          // Stop any SSE connection for this file
          const eventSource = sseConnectionsRef.current.get(source.upload_file_id);
          if (eventSource) {
            eventSource.close();
            sseConnectionsRef.current.delete(source.upload_file_id);
          }
        } else if (source.file_id) {
          console.log('Using deleteParsedFile for:', source.file_id);
          result = await apiService.deleteParsedFile(source.file_id);
        } else {
          console.warn('Source has neither upload_file_id nor file_id:', source);
          continue;
        }
        
        console.log('Delete result:', result);
        
        if (result.success) {
          deletionResults.push({ source, success: true });
        } else {
          deletionResults.push({ source, success: false, error: result.error });
        }
      } catch (error) {
        console.error(`Error deleting file ${source.title}:`, error);
        deletionResults.push({ source, success: false, error: error.message });
      }
    }
    
    // Remove successfully deleted sources from frontend state
    const successfullyDeleted = deletionResults
      .filter(result => result.success)
      .map(result => result.source.id);
    
    setSources((prev) => prev.filter((source) => !successfullyDeleted.includes(source.id)));
    
    // Show error for failed deletions
    const failedDeletions = deletionResults.filter(result => !result.success);
    if (failedDeletions.length > 0) {
      const errorMessage = `Failed to delete ${failedDeletions.length} file(s): ${failedDeletions.map(f => f.source.title).join(', ')}`;
      setError(errorMessage);
    }
  };

  const handleAddSource = () => {
    setShowUploadModal(true);
    setActiveTab('file');
    setLinkUrl('');
    setPasteText('');
  };

  // Modified file upload handler
  const handleFileUpload = async (file) => {
    // Validate file
    const validation = validateFile(file);
    
    if (!validation.valid) {
      setError(`File validation failed: ${validation.errors.join(', ')}`);
      return;
    }
    
    // Close modal and process file
    setShowUploadModal(false);
    
    // Use existing handleFileChange logic but with the file parameter
    const event = { target: { files: [file], value: "" } };
    await handleFileChangeInternal(event);
  };

  // Drag and drop handlers
  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, []);

  // Handle link upload
  const handleLinkUpload = async () => {
    if (!linkUrl.trim()) {
      setError('Please enter a valid URL');
      return;
    }

    try {
      setError(null);
      setShowUploadModal(false);
      
      // Generate upload file ID for tracking
      const uploadFileId = `link_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Determine processing type label
      const processingTypeLabel = urlProcessingType === 'media' ? 'Media' : 'Website';
      
      // Add link to sources with initial status - showing principle URL info
      const urlTitle = getDomainFromUrl(linkUrl) || linkUrl;
      const newSource = {
        id: Date.now(),
        upload_file_id: uploadFileId,
        title: urlTitle, // Show domain/title instead of full URL
        authors: `${processingTypeLabel} • URL`,
        ext: 'url',
        selected: false,
        type: "uploading",
        parsing_status: "pending",
        metadata: {
          original_filename: urlTitle,
          file_extension: '.url',
          source_type: 'url',
          processing_type: urlProcessingType,
          source_url: linkUrl,
          upload_timestamp: new Date().toISOString()
        },
        // Store principle URL info
        originalFile: {
          filename: urlTitle,
          extension: '.url',
          size: 0, // URLs don't have file size
          uploadTimestamp: new Date().toISOString(),
          sourceUrl: linkUrl,
          processingType: urlProcessingType
        }
      };
      
      setSources((prev) => [...prev, newSource]);
      setUploadProgress(prev => ({ ...prev, [uploadFileId]: 0 }));

      // Call appropriate API method based on processing type
      setUploadProgress(prev => ({ ...prev, [uploadFileId]: 20 }));
      
      const response = urlProcessingType === 'media' 
        ? await apiService.parseUrlWithMedia(linkUrl, 'cosine', uploadFileId)
        : await apiService.parseUrl(linkUrl, 'cosine', uploadFileId);
      
      if (response.success) {
        const { data } = response;
        
        // Update source with response data while preserving principle URL display
        setSources((prev) => prev.map(source => 
          source.id === newSource.id ? {
            ...source,
            file_id: data.file_id,
            type: "parsing",
            parsing_status: data.status || 'completed',
            // Keep principle URL info in authors display
            authors: `${processingTypeLabel} • ${data.content_length ? `${(data.content_length / 1000).toFixed(1)}k chars` : 'Unknown size'}`,
            metadata: {
              ...source.metadata,
              ...data,
              processing_completed: true
            }
          } : source
        ));
        
        // Start status monitoring if needed for URLs
        if (data.status && ['pending', 'parsing'].includes(data.status)) {
          // For URLs, we might not have SSE streaming, so let's try periodic polling
          startUrlStatusPolling(uploadFileId, newSource.id);
        } else {
          // Clear progress if processing is complete
          setUploadProgress(prev => {
            const newProgress = { ...prev };
            delete newProgress[uploadFileId];
            return newProgress;
          });
        }
        
        // Clear URL input
        setLinkUrl('');
        
      } else {
        throw new Error(response.error || 'URL parsing failed');
      }
      
    } catch (error) {
      console.error('Error processing URL:', error);
      
      // Update source to show error
      setSources((prev) => prev.map(source => 
        source.upload_file_id === uploadFileId ? {
          ...source,
          parsing_status: "error",
          authors: `URL • ${urlProcessingType === 'media' ? 'Media processing' : 'Content parsing'} failed`,
          error_message: error.message
        } : source
      ));
      
      // Clear progress
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[uploadFileId];
        return newProgress;
      });
      
      setError(`Failed to process URL: ${error.message}`);
    }
  };

  // Handle text upload
  const handleTextUpload = async () => {
    if (!pasteText.trim()) {
      setError('Please enter some text content');
      return;
    }

    try {
      setError(null);
      setShowUploadModal(false);
      
      // Generate upload file ID for tracking
      const uploadFileId = `text_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Add text to sources with initial status - showing principle text info
      const textTitle = `Text Content (${pasteText.slice(0, 50)}...)`;
      const textSizeKB = (pasteText.length / 1000).toFixed(1);
      const newSource = {
        id: Date.now(),
        upload_file_id: uploadFileId,
        title: textTitle, // Show descriptive title
        authors: `TXT • ${textSizeKB}k chars`,
        ext: 'txt',
        selected: false,
        type: "uploading",
        parsing_status: "pending",
        metadata: {
          original_filename: 'pasted_text.txt',
          file_extension: '.txt',
          content_length: pasteText.length,
          source_type: 'text',
          upload_timestamp: new Date().toISOString()
        },
        // Store principle text info
        originalFile: {
          filename: 'pasted_text.txt',
          extension: '.txt',
          size: pasteText.length, // Text length in characters
          uploadTimestamp: new Date().toISOString(),
          contentLength: pasteText.length
        }
      };
      
      setSources((prev) => [...prev, newSource]);
      setUploadProgress(prev => ({ ...prev, [uploadFileId]: 0 }));

      // Create a virtual file from the text
      const blob = new Blob([pasteText], { type: 'text/plain' });
      const file = new File([blob], 'pasted_text.txt', { type: 'text/plain' });
      
      setUploadProgress(prev => ({ ...prev, [uploadFileId]: 20 }));
      
      // Use existing file upload logic
      const response = await apiService.parseFile(file, uploadFileId, notebookId);
      
      if (response.success) {
        const { data } = response;
        
        setSources((prev) => prev.map(source => 
          source.id === newSource.id ? {
            ...source,
            file_id: data.file_id,
            type: "parsing",
            parsing_status: data.status,
            // Keep principle text info in authors display
            authors: `TXT • ${textSizeKB}k chars`,
            metadata: {
              ...source.metadata,
              file_size: data.file_size,
              file_extension: data.file_extension,
              processing_completed: true
            }
          } : source
        ));
        
        startStatusMonitoring(notebookId, uploadFileId);
        
      } else {
        throw new Error(response.error || 'Text upload failed');
      }
      
    } catch (error) {
      console.error('Error processing text:', error);
      
      setSources((prev) => prev.map(source => 
        source.id === newSource.id ? {
          ...source,
          parsing_status: "error",
          authors: `TXT • Upload failed`,
          error_message: error.message
        } : source
      ));
      
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[uploadFileId];
        return newProgress;
      });
      
      setError(`Failed to upload text: ${error.message}`);
    }
  };

  const validateFile = (file) => {
    const allowedExtensions = ["pdf", "txt", "md", "ppt", "pptx", "mp3", "mp4", "wav"];
    const extension = file.name.split(".").pop()?.toLowerCase() || "";
    const maxSize = 3 * 1024 * 1024 * 1024; // 3GB
    const minSize = 100; // 100 bytes minimum
    
    const errors = [];
    const warnings = [];
    
    // Check file extension
    if (!extension) {
      errors.push("File must have an extension");
    } else if (!allowedExtensions.includes(extension)) {
      errors.push(`File type "${extension}" is not supported. Allowed types: ${allowedExtensions.join(', ')}`);
    }
    
    // Check file size
    if (file.size > maxSize) {
      errors.push(`File size (${(file.size / (1024 * 1024 * 1024)).toFixed(2)}GB) exceeds maximum allowed size of 3GB`);
    } else if (file.size < minSize) {
      warnings.push("File is very small and may be empty");
    }
    
    // Check filename for potentially dangerous characters
    if (/[<>:"|?*]/.test(file.name)) {
      errors.push("Filename contains invalid characters");
    }
    
    // Check MIME type if available
    if (file.type) {
      const expectedTypes = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "md": "text/markdown",
        "mp3": "audio/mpeg",
        "mp4": "video/mp4",
        "wav": "audio/wav"
      };
      
      const expectedType = expectedTypes[extension];
      if (expectedType && !file.type.startsWith(expectedType.split('/')[0])) {
        warnings.push(`File type "${file.type}" may not match extension "${extension}"`);
      }
    }
    
    return { valid: errors.length === 0, errors, warnings, extension };
  };

  const handleFileChangeInternal = async (event) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file
      const validation = validateFile(file);
      
      if (!validation.valid) {
        setError(`File validation failed: ${validation.errors.join(', ')}`);
        return;
      }
      
      // Show warnings if any
      if (validation.warnings.length > 0) {
        console.warn('File validation warnings:', validation.warnings);
      }

      // Clear previous errors
      setError(null);

      // Generate upload file ID for tracking
      const uploadFileId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Add file to sources with initial status - showing principle file info
      const newSource = {
        id: Date.now(),
        upload_file_id: uploadFileId,
        title: file.name, // Show original filename
        authors: `${validation.extension.toUpperCase()} • ${(file.size / (1024 * 1024)).toFixed(1)} MB`,
        ext: validation.extension,
        selected: false,
        type: "uploading",
        file: file,
        parsing_status: "pending",
        metadata: {
          original_filename: file.name,
          file_extension: `.${validation.extension}`,
          file_size: file.size,
          upload_timestamp: new Date().toISOString()
        },
        // Store principle file info
        originalFile: {
          filename: file.name,
          extension: `.${validation.extension}`,
          size: file.size,
          uploadTimestamp: new Date().toISOString()
        }
      };
      
      setSources((prev) => [...prev, newSource]);
      
      // Initialize upload progress
      setUploadProgress(prev => ({ ...prev, [uploadFileId]: 0 }));

      try {
        // Upload and parse file
        setUploadProgress(prev => ({ ...prev, [uploadFileId]: 10 }));
        
        const response = await apiService.parseFile(file, uploadFileId, notebookId);
        console.log("response", response)
        
        if (response.success) {
          // const { data } = response;
          // console.log("data", data)
          
          // Update the source with response information while preserving principle file display
          setSources((prev) => prev.map(source => 
            source.id === newSource.id ? {
              ...source,
              file_id: response.file_id,
              type: "parsing",
              // parsing_status: data.status,

              // Keep principle file info in authors (original size, not processed size)
              authors: `${validation.extension.toUpperCase()} • ${(source.originalFile?.size / (1024 * 1024)).toFixed(1)} MB`,
              metadata: {
                ...source.metadata,
                // file_size: data.file_size,
                // file_extension: data.file_extension,
                processing_completed: true
              }
            } : source
          ));
          
          // Start status polling for real-time updates
          startStatusMonitoring(notebookId, uploadFileId);
          
        } else {
          // Handle upload failure
          throw new Error(response.error || 'Upload failed');
        }
      } catch (error) {
        console.error('Error uploading file:', error);
        
        // Update source to show error
        setSources((prev) => prev.map(source => 
          source.id === newSource.id ? {
            ...source,
            parsing_status: "error",
            authors: `${validation.extension.toUpperCase()} • Upload failed`,
            error_message: error.message
          } : source
        ));
        
        // Clear progress
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[uploadFileId];
          return newProgress;
        });
        
        setError(`Failed to upload ${file.name}: ${error.message}`);
      }

      // Reset file input
      event.target.value = "";
    }
  };

  // Handle file change from modal file input
  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (file) {
      await handleFileUpload(file);
    }
  };

  const getStatusIcon = (status, isAnimated = false) => {
    const config = statusConfig[status] || statusConfig.error;
    const IconComponent = config.icon;
    
    return (
      <IconComponent 
        className={`h-3 w-3 flex-shrink-0 ${config.color} ${isAnimated && config.animate ? 'animate-spin' : ''}`} 
      />
    );
  };

  const renderFileStatus = (source) => {
    const isProcessing = ['pending', 'parsing', 'uploading'].includes(source.parsing_status);
    
    if (isProcessing) {
      return (
        <div className="mt-1 flex items-center space-x-2">
          <Loader2 className="h-3 w-3 text-blue-500 animate-spin" />
          <span className="text-xs text-gray-500">
            {source.parsing_status === 'uploading' ? 'Uploading...' : 
             source.parsing_status === 'pending' ? 'Processing...' : 
             'Parsing...'}
          </span>
        </div>
      );
    }
    
    return null;
  };

  // Get tooltip text for source items
  const getSourceTooltip = (source) => {
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
    return `Original file: ${source.originalFile?.filename || source.title}`;
  };

  // Handle opening file preview
  const handlePreviewFile = (source) => {
    setPreviewSource(source);
    setIsPreviewOpen(true);
  };

  // Handle closing file preview
  const handleClosePreview = () => {
    setIsPreviewOpen(false);
    setPreviewSource(null);
  };

  return (
    <div className="h-full flex flex-col relative">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex justify-between items-center">
        <div className="flex items-center space-x-2 min-w-0 flex-1">
                      <h2 className="text-lg font-semibold text-red-600 truncate">Knowledge Base</h2>
          {isLoading ? (
            <RefreshCw className="h-3 w-3 animate-spin text-gray-400 flex-shrink-0" />
          ) : (
            <Badge variant="secondary" className="text-xs flex-shrink-0">
              {sources.length}
            </Badge>
          )}
        </div>
        <div className="flex items-center space-x-1 flex-shrink-0">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-gray-500 hover:text-gray-700"
            onClick={handleSortToggle}
            title={`Sort by ${sortOrder === 'newest' ? 'oldest first' : 'newest first'}`}
          >
            <ArrowUpDown className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-gray-500 hover:text-gray-700"
            onClick={handleGroupToggle}
            title={isGrouped ? 'Ungroup by type' : 'Group by type'}
          >
            <Group className="h-3 w-3" />
          </Button>
          {onToggleCollapse && (
            <Button
              variant="outline"
              size="icon"
              className={`h-7 w-7 border-red-500 hover:border-red-600 hover:bg-red-50 text-red-600 hover:text-red-700 shadow-sm hover:shadow-md transition-all duration-200 ${
                !isCollapsed ? 'ring-2 ring-red-300 ring-opacity-50' : ''
              }`}
              onClick={onToggleCollapse}
              title={isCollapsed ? "Expand Sources" : "Collapse Sources"}
            >
              <motion.div
                animate={{ rotate: isCollapsed ? 180 : 0 }}
                transition={{ duration: 0.3, ease: "easeInOut" }}
                className="flex items-center justify-center"
              >
                <ChevronLeft className="h-4 w-4 text-red-600 font-bold" />
              </motion.div>
            </Button>
          )}
        </div>
      </div>

      {/* Error Display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="p-4 border-b border-gray-200"
          >
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-sm">
                {error}
                <Button
                  variant="ghost"
                  size="sm"
                  className="ml-2 h-6 px-2"
                  onClick={() => setError(null)}
                >
                  Dismiss
                </Button>
              </AlertDescription>
            </Alert>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Select All & Actions */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="selectAll"
              className="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
              checked={sources.length > 0 && selectedCount === sources.length}
              onChange={(e) => {
                const checked = e.target.checked;
                setSources((prev) => {
                  const newSources = prev.map((s) => ({ ...s, selected: checked }));
                  
                  // Notify parent component about selection change
                  if (onSelectionChange) {
                    setTimeout(() => onSelectionChange(), 0);
                  }
                  
                  return newSources;
                });
              }}
            />
            <label htmlFor="selectAll" className="text-sm text-gray-700">
              Select All
            </label>
            {selectedCount > 0 && (
              <Badge variant="outline" className="text-xs">
                {selectedCount} selected
              </Badge>
            )}
          </div>
          
          {selectedCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-red-600 hover:text-red-700 hover:bg-red-50"
              onClick={handleDeleteSelected}
              title="Delete Selected"
            >
              <Trash2 className="h-3 w-3 mr-1" />
              Delete
            </Button>
          )}
        </div>
      </div>

      {/* Source List */}
      <div className="flex-1 overflow-y-auto">
        <AnimatePresence mode="wait">
          {isGrouped ? (
            // Grouped rendering
            <motion.div
              key="grouped"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {Object.entries(processedSources).map(([type, groupSources]) => (
                <motion.div 
                  key={type}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                >
                  <div className="px-4 py-1.5 bg-gray-50 border-b border-gray-200 sticky top-0">
                    <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                      {type.toUpperCase()} ({groupSources.length})
                    </h4>
                  </div>
                  <AnimatePresence>
                    {groupSources.map((source, index) => (
                      <motion.div
                        key={source.id}
                        layout
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        transition={{ duration: 0.2, ease: "easeOut" }}
                        className={`px-4 py-2 border-b border-gray-200 flex items-center ${
                          source.selected 
                            ? "bg-red-50 hover:bg-red-100" 
                            : index % 2 === 0 
                              ? "bg-white hover:bg-gray-100/70" 
                              : "bg-gray-50/50 hover:bg-gray-100/70"
                        } ${source.parsing_status === 'error' ? 'border-l-4 border-l-red-300' : ''} transition-colors duration-150`}
                      >
                        <input
                          type="checkbox"
                          checked={source.selected}
                          onChange={() => toggleSource(source.id)}
                          className="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500 flex-shrink-0"
                          disabled={['pending', 'parsing'].includes(source.parsing_status)}
                        />
                        <div className="ml-3 flex items-center space-x-2 flex-1 min-w-0">
                          <div className="flex-shrink-0">
                            {React.createElement(getPrincipleFileIcon(source), {
                              className: "h-4 w-4 text-gray-500"
                            })}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2">
                              <div className="flex-1 min-w-0">
                                <h3 
                                  className="text-sm font-medium text-gray-900 truncate"
                                  title={getSourceTooltip(source)}
                                >
                                {source.title}
                              </h3>
                                <p className="text-xs text-gray-500">{source.authors}</p>
                              </div>
                              
                              <div className="flex items-center space-x-1 flex-shrink-0">
                                {/* Preview Button */}
                                {source.parsing_status === 'completed' && supportsPreview(source.metadata?.file_extension, source.metadata) && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-6 w-6 p-0 text-gray-400 hover:text-blue-600 hover:bg-blue-50"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handlePreviewFile(source);
                                    }}
                                    title="Preview file content"
                                  >
                                    <Eye className="h-3 w-3" />
                                  </Button>
                                )}
                              {source.parsing_status && (
                                <div className="flex-shrink-0">
                                  {getStatusIcon(
                                    source.parsing_status, 
                                    ['pending', 'parsing'].includes(source.parsing_status)
                                  )}
                                </div>
                              )}
                            </div>
                            </div>
                            
                            {/* Loading indicator for ongoing uploads/parsing */}
                            {renderFileStatus(source)}
                            
                            {/* Error message display */}
                            {source.error_message && (
                              <p className="text-xs text-red-600 mt-1 truncate" title={source.error_message}>
                                Error: {source.error_message}
                              </p>
                            )}
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </motion.div>
              ))}
            </motion.div>
          ) : (
            // Ungrouped rendering
            <motion.div
              key="ungrouped"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {processedSources.map((source, index) => (
                <motion.div
                  key={source.id}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  className={`px-4 py-2 border-b border-gray-200 flex items-center ${
                    source.selected 
                      ? "bg-red-50 hover:bg-red-100" 
                      : index % 2 === 0 
                        ? "bg-white hover:bg-gray-100/70" 
                        : "bg-gray-50/50 hover:bg-gray-100/70"
                  } ${source.parsing_status === 'error' ? 'border-l-4 border-l-red-300' : ''} transition-colors duration-150`}
                >
                  <input
                    type="checkbox"
                    checked={source.selected}
                    onChange={() => toggleSource(source.id)}
                    className="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500 flex-shrink-0"
                    disabled={['pending', 'parsing'].includes(source.parsing_status)}
                  />
                  <div className="ml-3 flex items-center space-x-2 flex-1 min-w-0">
                    <div className="flex-shrink-0">
                      {React.createElement(getPrincipleFileIcon(source), {
                        className: "h-4 w-4 text-gray-500"
                      })}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <div className="flex-1 min-w-0">
                          <h3 
                            className="text-sm font-medium text-gray-900 truncate"
                            title={getSourceTooltip(source)}
                          >
                          {source.title}
                        </h3>
                          <p className="text-xs text-gray-500">{source.authors}</p>
                        </div>
                        
                        <div className="flex items-center space-x-1 flex-shrink-0">
                          {/* Preview Button */}
                          {source.parsing_status === 'completed' && supportsPreview(source.metadata?.file_extension, source.metadata) && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 text-gray-400 hover:text-blue-600 hover:bg-blue-50"
                              onClick={(e) => {
                                e.stopPropagation();
                                handlePreviewFile(source);
                              }}
                              title="Preview file content"
                            >
                              <Eye className="h-3 w-3" />
                            </Button>
                          )}
                        {source.parsing_status && (
                          <div className="flex-shrink-0">
                            {getStatusIcon(
                              source.parsing_status, 
                              ['pending', 'parsing'].includes(source.parsing_status)
                            )}
                          </div>
                        )}
                      </div>
                      </div>
                      
                      {/* Loading indicator for ongoing uploads/parsing */}
                      {renderFileStatus(source)}
                      
                      {/* Error message display */}
                      {source.error_message && (
                        <p className="text-xs text-red-600 mt-1 truncate" title={source.error_message}>
                          Error: {source.error_message}
                        </p>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Empty state */}
        {!isLoading && sources.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            <Upload className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p className="text-sm">No files in knowledge base</p>
            <p className="text-xs text-gray-400 mt-1">Upload your first file to get started</p>
          </div>
        )}
        
        {/* Loading state */}
        {isLoading && sources.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            <RefreshCw className="h-12 w-12 mx-auto mb-4 text-gray-300 animate-spin" />
            <p className="text-sm">Loading files...</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs text-gray-500">
            {sources.length} total • {selectedCount} selected
          </p>
          {Object.keys(uploadProgress).length > 0 && (
            <p className="text-xs text-blue-600">
              {Object.keys(uploadProgress).length} processing...
            </p>
          )}
        </div>
        
        <Button
          variant="outline"
          size="sm"
          className="w-full flex items-center justify-center"
          onClick={handleAddSource}
          disabled={isLoading}
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Source
        </Button>
        
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={handleFileChange}
          accept=".pdf,.txt,.md,.ppt,.pptx,.mp3,.mp4,.wav"
        />
        
        <p className="text-xs text-gray-400 mt-2 text-center">
          Supports PDF, TXT, MD, PPT, MP3, MP4, WAV (max 3 GB)
        </p>
        <p className="text-xs text-gray-300 mt-1 text-center">
          💡 Files shown are original uploads • Extracted content used for processing
        </p>
      </div>

      {/* Upload Modal */}
      <AnimatePresence>
        {showUploadModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-[60] p-4"
            onClick={() => setShowUploadModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: "spring", duration: 0.5 }}
              className="bg-gray-900 rounded-2xl p-8 max-w-3xl w-full max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-8">
                <h2 className="text-2xl font-bold text-white">Upload sources</h2>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowUploadModal(false)}
                  className="text-gray-400 hover:text-white hover:bg-gray-800"
                >
                  <X className="h-6 w-6" />
                </Button>
              </div>

              {/* Main Upload Area */}
              <div
                className={`border-2 border-dashed rounded-xl p-12 mb-8 text-center transition-all duration-200 ${
                  isDragOver 
                    ? 'border-blue-400 bg-blue-900/20' 
                    : 'border-gray-600 bg-gray-800/50'
                }`}
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
              >
                <div className="flex flex-col items-center space-y-4">
                  <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center">
                    <Upload className="h-8 w-8 text-white" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white mb-2">Upload sources</h3>
                    <p className="text-gray-400">
                      Drag & drop or{' '}
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="text-blue-400 hover:text-blue-300 underline"
                      >
                        choose file to upload
                      </button>
                    </p>
                  </div>
                </div>
                <p className="text-sm text-gray-500 mt-6">
                  Supported file types: PDF, .txt, Markdown, Audio (mp3, wav), Video (mp4)
                </p>
              </div>

              {/* Upload Options */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Link Section */}
                <div className="bg-gray-800 rounded-xl p-6">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
                      <Link2 className="h-5 w-5 text-white" />
                    </div>
                    <h3 className="text-lg font-semibold text-white">Link</h3>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <button 
                        className={`flex items-center space-x-2 p-3 rounded-lg transition-colors ${
                          urlProcessingType === 'website' 
                            ? 'bg-blue-600 hover:bg-blue-700' 
                            : 'bg-gray-700 hover:bg-gray-600'
                        }`}
                        onClick={() => {
                          setActiveTab('link');
                          setUrlProcessingType('website');
                        }}
                      >
                        <Globe className={`h-4 w-4 ${
                          urlProcessingType === 'website' ? 'text-white' : 'text-gray-300'
                        }`} />
                        <span className={`text-sm ${
                          urlProcessingType === 'website' ? 'text-white' : 'text-gray-300'
                        }`}>Website</span>
                      </button>
                      <button 
                        className={`flex items-center space-x-2 p-3 rounded-lg transition-colors ${
                          urlProcessingType === 'media' 
                            ? 'bg-red-600 hover:bg-red-700' 
                            : 'bg-gray-700 hover:bg-gray-600'
                        }`}
                        onClick={() => {
                          setActiveTab('link');
                          setUrlProcessingType('media');
                        }}
                      >
                        <Youtube className={`h-4 w-4 ${
                          urlProcessingType === 'media' ? 'text-white' : 'text-red-400'
                        }`} />
                        <span className={`text-sm ${
                          urlProcessingType === 'media' ? 'text-white' : 'text-gray-300'
                        }`}>Video/Audio</span>
                      </button>
                    </div>
                    
                    {activeTab === 'link' && (
                      <div className="space-y-3">
                        <input
                          type="url"
                          placeholder={
                            urlProcessingType === 'media' 
                              ? "Enter URL (YouTube, audio/video links)" 
                              : "Enter URL (website or blog)"
                          }
                          value={linkUrl}
                          onChange={(e) => setLinkUrl(e.target.value)}
                          className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                        <Button
                          onClick={handleLinkUpload}
                          disabled={!linkUrl.trim()}
                          className={`w-full text-white ${
                            urlProcessingType === 'media' 
                              ? 'bg-red-600 hover:bg-red-700' 
                              : 'bg-blue-600 hover:bg-blue-700'
                          }`}
                        >
                          {urlProcessingType === 'media' ? 'Process Media' : 'Process Website'}
                        </Button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Paste Text Section */}
                <div className="bg-gray-800 rounded-xl p-6">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center">
                      <FileText className="h-5 w-5 text-white" />
                    </div>
                    <h3 className="text-lg font-semibold text-white">Paste text</h3>
                  </div>
                  
                  <div className="space-y-3">
                    <button 
                      className="flex items-center space-x-2 p-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors w-full"
                      onClick={() => setActiveTab('text')}
                    >
                      <FileText className="h-4 w-4 text-gray-300" />
                      <span className="text-sm text-gray-300">Copied text</span>
                    </button>
                    
                    {activeTab === 'text' && (
                      <div className="space-y-3">
                        <textarea
                          placeholder="Paste your text content here..."
                          value={pasteText}
                          onChange={(e) => setPasteText(e.target.value)}
                          rows={6}
                          className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                        />
                        <div className="flex items-center justify-between text-xs text-gray-400">
                          <span>{pasteText.length} characters</span>
                          <span>1 / 50</span>
                        </div>
                        <Button
                          onClick={handleTextUpload}
                          disabled={!pasteText.trim()}
                          className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                        >
                          Upload Text
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* File Preview Modal */}
      <FilePreview
        source={previewSource}
        isOpen={isPreviewOpen}
        onClose={handleClosePreview}
      />
    </div>
  );
});

export default SourcesList;