import React, { useState, useRef, useCallback } from "react";
import { Trash2, Plus, X, Upload, Link2, FileText, Globe, Youtube, Loader2, RefreshCw, FileIcon } from "lucide-react";
import { Button } from "@/common/components/ui/button";
import { Badge } from "@/common/components/ui/badge";
import { Alert, AlertDescription } from "@/common/components/ui/alert";
import apiService from "@/common/utils/api";
import { KnowledgeBaseItem } from "@/features/notebook/type";
import { COLORS } from "@/features/notebook/config/uiConfig";

interface AddSourceModalProps {
  onClose: () => void;
  notebookId: string;
  onSourcesAdded: () => void;
  onUploadStarted?: (uploadFileId: string, filename: string, fileType: string) => void;
  onKnowledgeBaseItemsDeleted?: (deletedItemIds: string[]) => void;
  onSourcesRemoved?: number;
}

const AddSourceModal: React.FC<AddSourceModalProps> = ({
  onClose,
  notebookId,
  onSourcesAdded,
  onUploadStarted,
  onKnowledgeBaseItemsDeleted,
  onSourcesRemoved
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [linkUrl, setLinkUrl] = useState('');
  const [pasteText, setPasteText] = useState('');
  const [activeTab, setActiveTab] = useState('file');
  const [urlProcessingType, setUrlProcessingType] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  
  // Knowledge base management state
  const [knowledgeBaseItems, setKnowledgeBaseItems] = useState<KnowledgeBaseItem[]>([]);
  const [isLoadingKnowledgeBase, setIsLoadingKnowledgeBase] = useState(false);
  const [selectedKnowledgeItems, setSelectedKnowledgeItems] = useState<Set<string>>(new Set());
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // File validation function
  const validateFile = (file: File) => {
    const allowedExtensions = ["pdf", "txt", "md", "ppt", "pptx", "docx", "mp3", "mp4", "wav", "m4a", "avi", "mov", "mkv", "webm", "wmv", "m4v"];
    const extension = file.name.split(".").pop()?.toLowerCase() || "";
    const maxSize = 100 * 1024 * 1024; // 100MB
    const minSize = 100; // 100 bytes minimum
    
    const errors = [];
    
    if (!extension) {
      errors.push("File must have an extension");
    } else if (!allowedExtensions.includes(extension)) {
      errors.push(`File type "${extension}" is not supported. Allowed types: ${allowedExtensions.join(', ')}`);
    }
    
    if (file.size > maxSize) {
      errors.push(`File size (${(file.size / (1024 * 1024)).toFixed(1)}MB) exceeds maximum allowed size of 100MB`);
    } else if (file.size < minSize) {
      errors.push("File is very small and may be empty");
    }
    
    if (/[<>:"|?*]/.test(file.name)) {
      errors.push("Filename contains invalid characters");
    }
    
    return { valid: errors.length === 0, errors, extension };
  };

  // Handle file upload
  const handleFileUpload = async (file: File) => {
    const validation = validateFile(file);
    
    if (!validation.valid) {
      setError(`File validation failed: ${validation.errors.join(', ')}`);
      return;
    }
    
    setError(null);
    setIsUploading(true);
    
    try {
      const uploadFileId = `upload_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
      
      const response = await apiService.parseFile(file, uploadFileId, notebookId);
      
      if (response.success) {
        // Notify parent component that upload started
        if (onUploadStarted) {
          onUploadStarted(uploadFileId, file.name, validation.extension);
        }
        
        // Close modal and refresh sources list
        handleClose();
        onSourcesAdded();
      } else {
        throw new Error(response.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      
      // Parse the error message to check for duplicate file detection
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      // Check if this is a validation error response with details
      if (errorMessage.includes('File validation failed') && errorMessage.includes('already exists')) {
        setError(`File "${file.name}" already exists in this workspace. Please choose a different file or rename it.`);
      } else {
        setError(`Failed to upload ${file.name}: ${errorMessage}`);
      }
    } finally {
      setIsUploading(false);
    }
  };

  // Handle link upload
  const handleLinkUpload = async () => {
    if (!linkUrl.trim()) {
      setError('Please enter a valid URL');
      return;
    }

    setError(null);
    setIsUploading(true);
    
    try {
      const uploadFileId = `link_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
      
      // Get display name for URL
      const urlDomain = linkUrl.replace(/^https?:\/\//, '').split('/')[0];
      const displayName = `${urlDomain} - ${urlProcessingType || 'website'}`;
      
      // Notify parent component that upload started
      if (onUploadStarted) {
        onUploadStarted(uploadFileId, displayName, 'url');
      }
      
      // Close modal immediately after upload starts
      handleClose();
      
      let response;
      if (urlProcessingType === 'media') {
        response = await apiService.parseUrlWithMedia(linkUrl, notebookId, 'cosine', uploadFileId);
      } else if (urlProcessingType === 'document') {
        response = await apiService.parseDocumentUrl(linkUrl, notebookId, 'cosine', uploadFileId);
      } else {
        response = await apiService.parseUrl(linkUrl, notebookId, 'cosine', uploadFileId);
      }
      
      if (response.success) {
        // Refresh sources list (modal is already closed)
        onSourcesAdded();
      } else {
        throw new Error(response.error || 'URL parsing failed');
      }
    } catch (error) {
      console.error('Error processing URL:', error);
      setError(`Failed to process URL: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUploading(false);
    }
  };

  // Handle text upload
  const handleTextUpload = async () => {
    if (!pasteText.trim()) {
      setError('Please enter some text content');
      return;
    }

    setError(null);
    setIsUploading(true);
    
    try {
      const uploadFileId = `text_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
      
      // Generate filename from first 5 words
      const words = pasteText.trim()
        .split(/\s+/)
        .slice(0, 5)
        .map((word: string) => word.replace(/[^a-zA-Z0-9]/g, ''))
        .filter((word: string) => word.length > 0);
      
      const filename = words.length > 0 ? `${words.join('_').toLowerCase()}.md` : 'pasted_text.md';
      
      // Notify parent component that upload started
      if (onUploadStarted) {
        onUploadStarted(uploadFileId, filename, 'md');
      }
      
      // Close modal immediately after upload starts
      handleClose();
      
      const blob = new Blob([pasteText], { type: 'text/markdown' });
      const file = new File([blob], filename, { type: 'text/markdown' });
      
      const response = await apiService.parseFile(file, uploadFileId, notebookId);
      
      if (response.success) {
        // Refresh sources list (modal is already closed)
        onSourcesAdded();
      } else {
        throw new Error(response.error || 'Text upload failed');
      }
    } catch (error) {
      console.error('Error processing text:', error);
      setError(`Failed to upload text: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUploading(false);
    }
  };

  // Load knowledge base items
  const loadKnowledgeBase = async () => {
    try {
      setIsLoadingKnowledgeBase(true);
      const response = await apiService.getKnowledgeBase(notebookId);
      
      if (response.success) {
        const items = response.data?.items || [];
        setKnowledgeBaseItems(items);
      } else {
        throw new Error(response.error || "Failed to load knowledge base");
      }
    } catch (error) {
      console.error('Error loading knowledge base:', error);
      setError(`Failed to load knowledge base: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsLoadingKnowledgeBase(false);
    }
  };

  // Listen for sources removal to refresh knowledge base
  React.useEffect(() => {
    if (onSourcesRemoved && onSourcesRemoved > 0 && activeTab === 'knowledge') {
      // Refresh knowledge base when sources are removed
      loadKnowledgeBase();
    }
  }, [onSourcesRemoved, activeTab]);

  // Handle knowledge item selection
  const handleKnowledgeItemSelect = (itemId: string) => {
    setSelectedKnowledgeItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  // Handle linking selected knowledge items
  const handleLinkSelectedKnowledgeItems = async () => {
    if (selectedKnowledgeItems.size === 0) {
      setError('Please select at least one knowledge base item to link');
      return;
    }

    setError(null);
    setIsUploading(true);

    try {
      const linkPromises = Array.from(selectedKnowledgeItems).map(itemId =>
        apiService.linkKnowledgeBaseItem(notebookId, itemId)
      );

      const results = await Promise.all(linkPromises);
      const failedLinks = results.filter(result => !result.success);

      if (failedLinks.length === 0) {
        // Refresh sources list and close modal immediately
        onSourcesAdded();
        handleClose();
      } else {
        throw new Error(`Failed to link ${failedLinks.length} item(s)`);
      }
    } catch (error) {
      console.error('Error linking knowledge base items:', error);
      setError(`Failed to link items: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUploading(false);
    }
  };

  // Handle deleting knowledge base items
  const handleDeleteKnowledgeBaseItems = async () => {
    if (selectedKnowledgeItems.size === 0) {
      setError('Please select at least one knowledge base item to delete');
      return;
    }

    if (!confirm(`Are you sure you want to permanently delete ${selectedKnowledgeItems.size} knowledge base item(s)? This action cannot be undone and will remove them from all notebooks.`)) {
      return;
    }

    setError(null);
    setIsUploading(true);

    try {
      const deletePromises = Array.from(selectedKnowledgeItems).map(itemId =>
        apiService.deleteKnowledgeBaseItem(notebookId, itemId)
      );

      const results = await Promise.all(deletePromises);
      const successfulDeletes = Array.from(selectedKnowledgeItems).filter((_, index) =>
        results[index].success !== false
      );

      setKnowledgeBaseItems(prev =>
        prev.filter(item => !successfulDeletes.includes(item.id))
      );

      setSelectedKnowledgeItems(new Set());

      // Notify parent component about deleted items
      if (onKnowledgeBaseItemsDeleted && successfulDeletes.length > 0) {
        onKnowledgeBaseItemsDeleted(successfulDeletes);
      }

      const failedDeletes = results.filter(result => result.success === false);
      if (failedDeletes.length > 0) {
        setError(`Failed to delete ${failedDeletes.length} item(s)`);
      }
    } catch (error) {
      console.error('Error deleting knowledge base items:', error);
      setError(`Failed to delete items: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUploading(false);
    }
  };

  // Drag and drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, []);

  // Handle modal close
  const handleClose = () => {
    setActiveTab('file');
    setLinkUrl('');
    setPasteText('');
    setSelectedKnowledgeItems(new Set());
    setError(null);
    setIsUploading(false);
    onClose();
  };

  return (
    <>
      {/* Header - Fixed at top */}
      <div className="sticky top-0 z-10 bg-white pt-4 pb-4 -mt-8 -mx-8 px-8">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-2xl font-bold text-gray-900">Upload sources</h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              handleClose();
            }}
            className="text-gray-500 hover:text-gray-700 hover:bg-gray-100"
            disabled={isUploading}
          >
            <X className="h-6 w-6" />
          </Button>
        </div>

        {/* Tab Navigation - Fixed at top */}
        <div className={`flex space-x-1 mb-2 ${COLORS.tw.secondary.bg[100]} p-1 rounded-lg`}>
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              // Only switch to 'file' if not already on an upload tab
              if (activeTab === 'knowledge') {
                setActiveTab('file');
                // Reset URL processing type selection when switching back to upload
                setUrlProcessingType('');
              }
            }}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              (activeTab === 'file' || activeTab === 'link' || activeTab === 'text')
                ? `${COLORS.tw.primary.bg[600]} text-white`
                : `${COLORS.tw.secondary.text[600]} ${COLORS.tw.secondary.text[900]} hover:bg-gray-200`
            }`}
            disabled={isUploading}
          >
            Upload Source
          </button>
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setActiveTab('knowledge');
              // Always reload knowledge base when switching to this tab to ensure fresh data
              loadKnowledgeBase();
            }}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'knowledge'
                ? `${COLORS.tw.primary.bg[600]} text-white`
                : `${COLORS.tw.secondary.text[600]} hover:${COLORS.tw.secondary.text[900]} hover:bg-gray-200`
            }`}
            disabled={isUploading}
          >
            知识库
          </button>
        </div>
      </div>



      {/* Main Upload Area - Only show when not in knowledge base mode */}
      {activeTab !== 'knowledge' && (
        <div
          className={`border-2 border-dashed rounded-xl p-6 mb-6 text-center transition-all duration-200 mt-10 ${
            isDragOver 
              ? 'border-red-400 bg-red-50' 
              : 'border-gray-300 bg-gray-50'
          }`}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          <div className="flex flex-col items-center space-y-2">
            <div className={`w-12 h-12 ${COLORS.tw.primary.bg[600]} rounded-full flex items-center justify-center`}>
              <Upload className="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-gray-900 mb-1">Upload sources</h3>
              <p className="text-sm text-gray-600">
                Drag & drop or{' '}
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                  className={`${COLORS.tw.primary.text[600]} ${COLORS.tw.primary.hover.text[700]} underline`}
                  disabled={isUploading}
                >
                  choose file to upload
                </button>
              </p>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-3">
            Supported file types: pdf, txt, markdown, pptx, docx, Audio (mp3, wav, m4a), Video (mp4, avi, mov, mkv, webm, wmv, m4v)
          </p>
        </div>
      )}

      {/* Upload Options */}
      {activeTab !== 'knowledge' && (
        <div className="space-y-6">
          {/* Link Section */}
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex items-center space-x-3 mb-4">
              <div className={`w-10 h-10 ${COLORS.tw.primary.bg[600]} rounded-lg flex items-center justify-center`}>
                <Link2 className="h-5 w-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Link</h3>
            </div>
            
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <button 
                  className={`flex items-center space-x-2 p-3 rounded-lg transition-colors ${
                    urlProcessingType === 'website' 
                      ? `${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]}` 
                      : `${COLORS.tw.secondary.bg[100]} hover:bg-gray-200`
                  }`}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setActiveTab('link');
                    setUrlProcessingType('website');
                  }}
                  disabled={isUploading}
                >
                  <Globe className={`h-4 w-4 ${
                    urlProcessingType === 'website' ? 'text-white' : 'text-gray-600'
                  }`} />
                  <span className={`text-sm ${
                    urlProcessingType === 'website' ? 'text-white' : 'text-gray-600'
                  }`}>Website</span>
                </button>
                <button 
                  className={`flex items-center space-x-2 p-3 rounded-lg transition-colors ${
                    urlProcessingType === 'document' 
                      ? `${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]}` 
                      : `${COLORS.tw.secondary.bg[100]} hover:bg-gray-200`
                  }`}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setActiveTab('link');
                    setUrlProcessingType('document');
                  }}
                  disabled={isUploading}
                >
                  <FileText className={`h-4 w-4 ${
                    urlProcessingType === 'document' ? 'text-white' : 'text-gray-600'
                  }`} />
                  <span className={`text-sm ${
                    urlProcessingType === 'document' ? 'text-white' : 'text-gray-600'
                  }`}>Document</span>
                </button>
                <button 
                  className={`flex items-center space-x-2 p-3 rounded-lg transition-colors ${
                    urlProcessingType === 'media' 
                      ? `${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]}` 
                      : `${COLORS.tw.secondary.bg[100]} hover:bg-gray-200`
                  }`}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setActiveTab('link');
                    setUrlProcessingType('media');
                  }}
                  disabled={isUploading}
                >
                  <Youtube className={`h-4 w-4 ${
                    urlProcessingType === 'media' ? 'text-white' : 'text-gray-600'
                  }`} />
                  <span className={`text-sm ${
                    urlProcessingType === 'media' ? 'text-white' : 'text-gray-600'
                  }`}>Video</span>
                </button>
              </div>
              
              {activeTab === 'link' && (
                <div className="space-y-3">
                  <input
                    type="url"
                    placeholder={
                      urlProcessingType === 'media' 
                        ? "Enter URL (YouTube, video links)" 
                        : urlProcessingType === 'document'
                        ? "Enter direct PDF/PowerPoint link"
                        : "Enter URL (website or blog)"
                    }
                    value={linkUrl}
                    onChange={(e) => setLinkUrl(e.target.value)}
                    className="w-full p-3 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    disabled={isUploading}
                  />
                  {urlProcessingType === 'document' && (
                    <p className="text-xs text-gray-600">
                      📄 Only PDF and PowerPoint links are supported. Use the "Website" option for HTML pages.
                    </p>
                  )}
                  <Button
                    onClick={handleLinkUpload}
                    disabled={!linkUrl.trim() || isUploading}
                    className={`w-full text-white ${
                      urlProcessingType === 'media' 
                        ? `${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]}` 
                        : urlProcessingType === 'document'
                        ? `${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]}`
                        : `${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]}`
                    }`}
                  >
                    {isUploading ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : null}
                    {urlProcessingType === 'media' ? 'Process Media' : 
                     urlProcessingType === 'document' ? 'Download Document' : 
                     'Process Website'}
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* Paste Text Section */}
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex items-center space-x-3 mb-4">
              <div className={`w-10 h-10 ${COLORS.tw.primary.bg[600]} rounded-lg flex items-center justify-center`}>
                <FileText className="h-5 w-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Paste text</h3>
            </div>
            
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <button 
                  className={`flex items-center space-x-2 p-3 rounded-lg transition-colors ${
                    activeTab === 'text'
                      ? `${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]}`
                      : `${COLORS.tw.secondary.bg[100]} hover:bg-gray-200`
                  }`}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setActiveTab('text');
                  setUrlProcessingType('');
                }}
                disabled={isUploading}
              >
                <FileText className={`h-4 w-4 ${
                  activeTab === 'text' ? 'text-white' : 'text-gray-600'
                }`} />
                <span className={`text-sm ${
                  activeTab === 'text' ? 'text-white' : 'text-gray-600'
                }`}>Copied text</span>
              </button>
              </div>
              
              {activeTab === 'text' && (
                <div className="space-y-3">
                  <textarea
                    placeholder="Paste your text content here..."
                    value={pasteText}
                    onChange={(e) => setPasteText(e.target.value)}
                    maxLength={10000}
                    rows={6}
                    className="w-full p-3 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
                    disabled={isUploading}
                  />
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>{pasteText.length} characters</span>
                    <span>{pasteText.length} / 10000</span>
                  </div>
                  <Button
                    onClick={handleTextUpload}
                    disabled={!pasteText.trim() || isUploading}
                    className={`w-full ${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]} text-white`}
                  >
                    {isUploading ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <FileText className="h-4 w-4 mr-2" />
                    )}
                    Upload Text
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Knowledge Base Management */}
      {activeTab === 'knowledge' && (
        <div className="space-y-6 mt-5">
          {/* Knowledge Base Header */}
          <div className="py-3">
            <div className="flex items-center space-x-3 mb-2">
              <div className={`w-10 h-10 ${COLORS.tw.primary.bg[600]} rounded-full flex items-center justify-center`}>
                <FileIcon className="h-5 w-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">知识库管理</h3>
            </div>
            <p className="text-gray-600 text-sm ml-13">
              管理您的知识库项目 • 链接到当前笔记本或永久删除
            </p>
          </div>
          
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-md font-medium text-gray-900">知识库项目</h4>
              <div className="flex items-center space-x-2">
                <Button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    loadKnowledgeBase();
                  }}
                  variant="outline"
                  size="sm"
                  className="border-gray-300 text-gray-600 hover:bg-gray-100"
                  disabled={isLoadingKnowledgeBase}
                >
                  {isLoadingKnowledgeBase ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* Knowledge Base Items List */}
            <div className="space-y-3">
              {isLoadingKnowledgeBase ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin text-gray-500" />
                  <span className="ml-2 text-gray-500">Loading knowledge base...</span>
                </div>
              ) : knowledgeBaseItems.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <FileIcon className="h-12 w-12 mx-auto mb-2 text-gray-400" />
                  <p>No items in knowledge base</p>
                </div>
              ) : (
                <>
                  {/* Select All */}
                  <div className="flex items-center justify-between p-3 bg-gray-100 rounded-lg">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedKnowledgeItems.size === knowledgeBaseItems.length && knowledgeBaseItems.length > 0}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedKnowledgeItems(new Set(knowledgeBaseItems.map(item => item.id)));
                          } else {
                            setSelectedKnowledgeItems(new Set());
                          }
                        }}
                        className={`h-4 w-4 rounded border-gray-400 ${COLORS.tw.primary.text[600]} focus:ring-red-500`}
                        disabled={isUploading}
                      />
                      <span className="text-sm text-gray-700">
                        Select All ({knowledgeBaseItems.length} items)
                      </span>
                    </label>
                    {selectedKnowledgeItems.size > 0 && (
                      <Badge variant="outline" className={`${COLORS.tw.primary.border[600]} ${COLORS.tw.primary.text[600]}`}>
                        {selectedKnowledgeItems.size} selected
                      </Badge>
                    )}
                  </div>

                  {/* Knowledge Base Items */}
                  <div className="max-h-64 overflow-y-auto space-y-2">
                    {knowledgeBaseItems.map((item) => (
                      <div
                        key={item.id}
                        className={`p-3 rounded-lg border transition-colors cursor-pointer ${
                          selectedKnowledgeItems.has(item.id)
                            ? 'bg-red-50 border-red-300'
                            : item.linked_to_notebook
                            ? 'bg-gray-50 border-gray-300 hover:border-gray-400'
                            : 'bg-gray-50 border-gray-300 hover:border-gray-400'
                        }`}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          if (!isUploading) {
                            handleKnowledgeItemSelect(item.id);
                          }
                        }}
                      >
                        <div className="flex items-center space-x-3">
                          <input
                            type="checkbox"
                            checked={selectedKnowledgeItems.has(item.id)}
                            onChange={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              if (!isUploading) {
                                handleKnowledgeItemSelect(item.id);
                              }
                            }}
                            className={`h-4 w-4 rounded border-gray-400 ${COLORS.tw.primary.text[600]} focus:ring-red-500`}
                            onClick={(e) => e.stopPropagation()}
                            disabled={isUploading}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2">
                              <h4 className="text-sm font-medium text-gray-900 truncate">
                                {item.title || item.filename || 'Untitled'}
                              </h4>
                              {item.linked_to_notebook && (
                                <Badge variant="outline" className="border-green-600 text-green-600 text-xs">
                                  Already linked
                                </Badge>
                              )}
                            </div>
                            <p className="text-xs text-gray-600 mt-1">
                              {item.metadata?.description || 'No description'}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Action Buttons */}
            {selectedKnowledgeItems.size > 0 && (
              <div className="flex space-x-3 mt-6 pt-4 border-t border-gray-300">
                <Button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleLinkSelectedKnowledgeItems();
                  }}
                  className={`flex-1 ${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]} text-white`}
                  disabled={selectedKnowledgeItems.size === 0 || Array.from(selectedKnowledgeItems).every(id => 
                    knowledgeBaseItems.find(item => item.id === id)?.linked_to_notebook
                  ) || isUploading}
                >
                  {isUploading ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4 mr-2" />
                  )}
                  Link to Notebook ({selectedKnowledgeItems.size})
                </Button>
                <Button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleDeleteKnowledgeBaseItems();
                  }}
                  variant="outline"
                  className={`${COLORS.tw.primary.border[600]} ${COLORS.tw.primary.text[600]} hover:bg-red-50`}
                  disabled={isUploading}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete ({selectedKnowledgeItems.size})
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mt-6">
          <Alert variant="destructive" className={`${COLORS.tw.primary.border[600]} ${COLORS.tw.primary.bg[50]}`}>
            <AlertDescription className="text-red-700">
              {error}
              <Button
                variant="ghost"
                size="sm"
                className={`ml-2 h-6 px-2 ${COLORS.tw.primary.text[600]} ${COLORS.tw.primary.hover.text[700]}`}
                onClick={() => setError(null)}
              >
                Dismiss
              </Button>
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            handleFileUpload(file);
          }
        }}
        style={{ display: 'none' }}
        accept=".pdf,.txt,.md,.ppt,.pptx,.docx,.mp3,.mp4,.wav,.m4a,.avi,.mov,.mkv,.webm,.wmv,.m4v"
      />
    </>
  );
};

export default AddSourceModal;