import React, { useState, useRef, useCallback } from "react";
import { X, Upload, Link2, FileText, Globe, Youtube, Loader2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import sourceService from "@/features/notebook/services/SourceService";
import { COLORS } from "@/features/notebook/config/uiConfig";


interface AddSourceModalProps {
  onClose: () => void;
  notebookId: string;
  onSourcesAdded: () => void;
  onUploadStarted?: (uploadFileId: string, filename: string, fileType: string, oldUploadFileId?: string) => void;
  onKnowledgeBaseItemsDeleted?: () => void;
}

const AddSourceModal: React.FC<AddSourceModalProps> = ({
  onClose,
  notebookId,
  onSourcesAdded,
  onUploadStarted,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [linkUrl, setLinkUrl] = useState('');
  const [pasteText, setPasteText] = useState('');
  const [activeTab, setActiveTab] = useState('file');
  const [urlProcessingType, setUrlProcessingType] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  
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
      errors.push(`File type "${extension}" is not supported. Allowed types: ${allowedExtensions.join(", ")}`);
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
          // Notify parent component that upload started IMMEDIATELY
      // This makes the item show up in processing state right away (like URLs do)
      if (onUploadStarted) {
        onUploadStarted(uploadFileId, file.name, validation.extension);
      }
          const response = await sourceService.parseFile(file, uploadFileId, notebookId);
          if (response.success) {
        // Update temp source with real file_id from API for proper tracking
        if (onUploadStarted && response.file_id && response.file_id !== uploadFileId) {
          console.log(`Updating file tracking from upload_id ${uploadFileId} to real file_id ${response.file_id}`);
          // Call onUploadStarted again with the real file_id to update the temp source
          onUploadStarted(response.file_id, file.name, validation.extension, uploadFileId);
        } else {
          console.log(`File upload response:`, response, `uploadFileId: ${uploadFileId}`);
        }
        // Close modal and refresh sources list on success
        handleClose();
        onSourcesAdded();
      } else {
        throw new Error(response.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
          const errorMessage = error instanceof Error ? error.message : 'Unknown error';
          // Check if this is a validation error (duplicate file)
      if (errorMessage.includes('already exists')) {
        // This is a validation error - keep modal open and show error
        // The item will show as "failed" in the processing list, which is appropriate
        setError(`File "${file.name}" already exists in this workspace. Please choose a different file or rename it.`);
        // Don't close modal, let user try again or cancel
      } else {
        // This is a processing error - close modal and let processing system handle it
        handleClose();
        // The processing system will show the error state in the processing list
        console.error(`Processing error for ${file.name}:`, errorMessage);
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
          
      // Show temp processing item BEFORE API call
      if (onUploadStarted) {
        onUploadStarted(uploadFileId, displayName, 'url');
      }
      
      let response;
      if (urlProcessingType === 'media') {
        response = await sourceService.parseUrlWithMedia(linkUrl, notebookId, 'cosine', uploadFileId);
      } else if (urlProcessingType === 'document') {
        response = await sourceService.parseDocumentUrl(linkUrl, notebookId, 'cosine', uploadFileId);
      } else {
        response = await sourceService.parseUrl(linkUrl, notebookId, 'cosine', uploadFileId);
      }
          if (response.success) {
        // Update temp source with real file_id from API for proper tracking
        if (onUploadStarted && response.file_id && response.file_id !== uploadFileId) {
          // Call onUploadStarted again with the real file_id to update the temp source
          onUploadStarted(response.file_id, displayName, 'url', uploadFileId);
        }
        // Close modal - DON'T refresh sources list immediately
        // The URL will be processed asynchronously and appear when ready
        handleClose();
        // Note: We don't call onSourcesAdded() here because:
        // 1. We already called onUploadStarted() to show the processing item
        // 2. The URL processing happens asynchronously via Celery
        // 3. Real-time updates will show when processing is complete
      } else {
        throw new Error(response.error || 'URL parsing failed');
      }
    } catch (error) {
      console.error('Error processing URL:', error);
          // Parse the error message to check for duplicate URL detection
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
          // Check if this is a duplicate URL validation error
      if (errorMessage.includes('already exists')) {
        // This is a validation error - keep modal open and show error
        // The item will show as "failed" in the processing list, which is appropriate
        setError(`This URL already exists in your workspace. Please use a different URL.`);
        // Don't close modal, let user try again or cancel
      } else {
        // This is a processing error - close modal and let processing system handle it
        handleClose();
        // The processing system will show the error state in the processing list
        console.error(`Processing error for ${linkUrl}:`, errorMessage);
      }
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
          const blob = new Blob([pasteText], { type: 'text/markdown' });
      const file = new File([blob], filename, { type: 'text/markdown' });
          
      // Notify parent component that upload started IMMEDIATELY
      if (onUploadStarted) {
        onUploadStarted(uploadFileId, filename, 'md');
      }
      
          const response = await sourceService.parseFile(file, uploadFileId, notebookId);
          if (response.success) {
        // Update temp source with real file_id from API for proper tracking
        if (onUploadStarted && response.file_id && response.file_id !== uploadFileId) {
          // Call onUploadStarted again with the real file_id to update the temp source
          onUploadStarted(response.file_id, filename, 'md', uploadFileId);
        }
              // Close modal and refresh sources list
        handleClose();
        onSourcesAdded();
      } else {
        throw new Error(response.error || 'Text upload failed');
      }
    } catch (error) {
      console.error('Error processing text:', error);
          // Parse the error message to check for duplicate content detection
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
          // Check if this is a duplicate content validation error
      if (errorMessage.includes('already exists') || errorMessage.includes('Duplicate content detected')) {
        setError(`This text content already exists in your workspace. Please modify the text or use different content.`);
      } else {
        setError(`Failed to upload text: ${errorMessage}`);
      }
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
      const file = files[0];
      if (file) {
        handleFileUpload(file);
      }
    }
  }, []);

  // Handle modal close
  const handleClose = () => {
    setActiveTab('file');
    setLinkUrl('');
    setPasteText('');
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
          >
            <X className="h-6 w-6" />
          </Button>
        </div>

        {/* Header - Sources are now notebook-specific */}
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Add Source</h2>
          <p className="text-gray-600 text-sm">Add files, links, or text to this notebook</p>
        </div>

        {/* Custom Error Display - Now in header for better visibility */}
        {error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                {/* Custom error icon SVG */}
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3 flex-1">
                <div className="text-sm text-red-700">
                  {error}
                </div>
              </div>
              <div className="ml-4 flex-shrink-0">
                <button
                  type="button"
                  className="inline-flex text-red-400 hover:text-red-600 focus:outline-none"
                  onClick={() => setError(null)}
                >
                  {/* Custom dismiss icon SVG */}
                  <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>



      {/* Main Upload Area */}
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
          {/* Upload Options */}
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
                     urlProcessingType === 'document' ? 'Process Document' : 
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

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          handleFileUpload(file);
        }}
        style={{ display: 'none' }}
        accept=".pdf,.txt,.md,.ppt,.pptx,.docx,.mp3,.mp4,.wav,.m4a,.avi,.mov,.mkv,.webm,.wmv,.m4v"
      />
    </>
  );
};

export default AddSourceModal;