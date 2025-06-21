import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Eye, FileText, Globe, Music, Video, File, HardDrive, Calendar, ExternalLink, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { generatePreview, supportsPreview, PREVIEW_TYPES, formatDate } from '@/lib/filePreview';
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github.css";

// API Base URL for raw file access
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Memoized markdown content component (same as StudioPanel)
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

const FilePreview = ({ source, isOpen, onClose }) => {
  // Consolidate all state into a single object to avoid hook order issues
  const [state, setState] = useState({
    preview: null,
    isLoading: false,
    error: null,
    audioError: false,
    audioLoaded: false,
    videoError: false,
    videoLoaded: false
  });

  // Helper function to update state
  const updateState = (updates) => {
    setState(prevState => ({ ...prevState, ...updates }));
  };

  // Helper function to get raw file URL
  const getRawFileUrl = (fileId) => {
    return `${API_BASE_URL}/files/${fileId}/raw`;
  };

  useEffect(() => {
    if (isOpen && source && supportsPreview(source.metadata?.file_extension, source.metadata)) {
      loadPreview();
    }
  }, [isOpen, source]);

  const loadPreview = async () => {
    if (!source) return;
    
    updateState({
      isLoading: true,
      error: null,
      audioError: false,
      audioLoaded: false,
      videoError: false,
      videoLoaded: false
    });
    
    try {
      const previewData = await generatePreview(source);
      updateState({ preview: previewData, isLoading: false });
    } catch (err) {
      updateState({ error: err.message, isLoading: false });
    }
  };

  const getPreviewIcon = (type) => {
    switch (type) {
      case PREVIEW_TYPES.TEXT_CONTENT:
        return FileText;
      case PREVIEW_TYPES.URL_INFO:
        return Globe;
      case PREVIEW_TYPES.AUDIO_INFO:
        return Music;
      case PREVIEW_TYPES.VIDEO_INFO:
        return Video;
      default:
        return File;
    }
  };

  const renderPreviewContent = () => {
    if (state.isLoading) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-4" />
            <p className="text-gray-500">Loading preview...</p>
          </div>
        </div>
      );
    }

    if (state.error) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <File className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-red-600 mb-2">Preview Error</p>
            <p className="text-gray-500 text-sm">{state.error}</p>
          </div>
        </div>
      );
    }

    if (!state.preview) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Eye className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No preview available</p>
          </div>
        </div>
      );
    }

    switch (state.preview.type) {
      case PREVIEW_TYPES.TEXT_CONTENT:
        // Check if this is a PDF with parsed content
        return state.preview.isPdfPreview ? renderPdfContentPreview() : renderTextPreview();
      case PREVIEW_TYPES.URL_INFO:
        return renderUrlPreview();
      case PREVIEW_TYPES.AUDIO_INFO:
        return renderAudioPreview();
      case PREVIEW_TYPES.VIDEO_INFO:
        return renderVideoPreview();
      case PREVIEW_TYPES.METADATA:
        // Check if this is a PDF that failed to load content
        return state.preview.isPdfPreview ? renderPdfMetadataPreview() : renderMetadataPreview();
      default:
        return renderMetadataPreview();
    }
  };

  const renderTextPreview = () => (
    <div className="space-y-4">
      <div className="flex items-center space-x-2 mb-4">
        <FileText className="h-5 w-5 text-blue-500" />
        <h3 className="font-medium text-gray-900">{state.preview.title}</h3>
      </div>
      
      <div className="flex flex-wrap gap-2 mb-4">
        <Badge variant="secondary">
          <HardDrive className="h-3 w-3 mr-1" />
          {state.preview.wordCount} words
        </Badge>
        <Badge variant="secondary">
          <FileText className="h-3 w-3 mr-1" />
          {state.preview.lines} lines
        </Badge>
      </div>

      <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
        <MarkdownContent content={state.preview.content} />
      </div>
    </div>
  );

  const renderUrlPreview = () => (
    <div className="space-y-4">
      <div className="flex items-center space-x-2 mb-4">
        <Globe className="h-5 w-5 text-green-500" />
        <h3 className="font-medium text-gray-900">{state.preview.title}</h3>
      </div>
      
      <div className="flex flex-wrap gap-2 mb-4">
        <Badge variant="secondary">
          {state.preview.processingType === 'media' ? 'Media' : 'Website'}
        </Badge>
        <Badge variant="secondary">
          <HardDrive className="h-3 w-3 mr-1" />
          {Math.round(state.preview.contentLength / 1000)}k chars
        </Badge>
        {state.preview.extractedAt && (
          <Badge variant="secondary">
            <Calendar className="h-3 w-3 mr-1" />
            {formatDate(state.preview.extractedAt)}
          </Badge>
        )}
      </div>

      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-gray-700">Source URL:</span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => window.open(state.preview.url, '_blank')}
            className="h-6 px-2 text-xs"
          >
            <ExternalLink className="h-3 w-3 mr-1" />
            Open
          </Button>
        </div>
        <p className="text-sm text-blue-600 break-all">{state.preview.url}</p>
        
        {state.preview.content && (
          <div className="mt-4">
            <span className="text-sm font-medium text-gray-700">Description:</span>
            <p className="text-sm text-gray-600 mt-1">{state.preview.content}</p>
          </div>
        )}
      </div>
    </div>
  );

  const renderAudioPreview = () => (
    <div className="space-y-6">
      {/* Audio Player Section */}
      <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
        <div className="flex items-center space-x-3 mb-3">
          <div className="w-10 h-10 bg-purple-500 rounded-full flex items-center justify-center">
            <Music className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1">
            <h4 className="text-sm font-medium text-gray-900">Audio Player</h4>
            <p className="text-xs text-gray-600">Click play to listen to the audio file</p>
          </div>
        </div>
        
        {/* Audio Element */}
        <audio 
          controls 
          className="w-full h-10 rounded-lg"
          preload="metadata"
          controlsList="nodownload"
          onError={(e) => {
            console.log('Audio load error:', e);
            updateState({ audioError: true });
          }}
          onLoadedMetadata={() => {
            updateState({ audioLoaded: true, audioError: false });
          }}
          onCanPlay={() => {
            updateState({ audioLoaded: true, audioError: false });
          }}
        >
          <source 
            src={preview.audioUrl || getRawFileUrl(source?.file_id)} 
            // type={`audio/${preview.format.toLowerCase()}`} 
          />
          Your browser does not support the audio element.
        </audio>
        
        <div className="mt-2 text-xs text-center">
          {audioError ? (
            <span className="text-red-500">⚠️ Audio file could not be loaded</span>
          ) : audioLoaded ? (
            <span className="text-green-600">✅ Audio ready for playback</span>
          ) : (
            <span className="text-gray-500">🔄 Loading audio...</span>
          )}
        </div>
      </div>
      
      {/* File Information */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-900 mb-3">File Information</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-sm font-medium text-gray-700">Format:</span>
            <p className="text-sm text-gray-600">{preview.format}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-700">File Size:</span>
            <p className="text-sm text-gray-600">{preview.fileSize}</p>
          </div>
          {preview.duration !== 'Unknown' && (
            <div>
              <span className="text-sm font-medium text-gray-700">Duration:</span>
              <p className="text-sm text-gray-600">{preview.duration}</p>
            </div>
          )}
          {preview.sampleRate !== 'Unknown' && (
            <div>
              <span className="text-sm font-medium text-gray-700">Sample Rate:</span>
              <p className="text-sm text-gray-600">{preview.sampleRate}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const renderVideoPreview = () => (
    <div className="space-y-6">
      {/* Video Player Section */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
        <div className="flex items-center space-x-3 mb-3">
          <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
            <Video className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1">
            <h4 className="text-sm font-medium text-gray-900">Video Player</h4>
            <p className="text-xs text-gray-600">Click play to watch the video file</p>
          </div>
        </div>
        
        {/* Video Element */}
        <video 
          controls 
          className="w-full rounded-lg bg-black"
          preload="metadata"
          controlsList="nodownload"
          style={{ maxHeight: '400px' }}
          onError={(e) => {
            console.log('Video load error:', e);
            setVideoError(true);
          }}
          onLoadedMetadata={() => {
            setVideoLoaded(true);
            setVideoError(false);
          }}
          onCanPlay={() => {
            setVideoLoaded(true);
            setVideoError(false);
          }}
        >
          <source 
            src={preview.videoUrl || getRawFileUrl(source?.file_id)} 
            // type={`video/${preview.format.toLowerCase()}`} 
          />
          Your browser does not support the video element.
        </video>
        
        <div className="mt-2 text-xs text-center">
          {videoError ? (
            <span className="text-red-500">⚠️ Video file could not be loaded</span>
          ) : videoLoaded ? (
            <span className="text-green-600">✅ Video ready for playback</span>
          ) : (
            <span className="text-gray-500">🔄 Loading video...</span>
          )}
        </div>
      </div>
      
      {/* Video Information */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Video Information</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-sm font-medium text-gray-700">Format:</span>
            <p className="text-sm text-gray-600">{preview.format}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-700">File Size:</span>
            <p className="text-sm text-gray-600">{preview.fileSize}</p>
          </div>
          {preview.duration !== 'Unknown' && (
            <div>
              <span className="text-sm font-medium text-gray-700">Duration:</span>
              <p className="text-sm text-gray-600">{preview.duration}</p>
            </div>
          )}
          {preview.resolution !== 'Unknown' && (
            <div>
              <span className="text-sm font-medium text-gray-700">Resolution:</span>
              <p className="text-sm text-gray-600">{preview.resolution}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const renderPdfPreview = () => (
    <div className="space-y-6">
      {/* PDF Viewer Section */}
      <div className="bg-gradient-to-r from-red-50 to-orange-50 rounded-lg p-4 border border-red-200">
        <div className="flex items-center space-x-3 mb-3">
          <div className="w-10 h-10 bg-red-500 rounded-full flex items-center justify-center">
            <FileText className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1">
            <h4 className="text-sm font-medium text-gray-900">PDF Viewer</h4>
            <p className="text-xs text-gray-600">View the PDF document directly in your browser</p>
          </div>
        </div>
        
        {/* PDF Embed */}
        <div className="relative bg-white rounded-lg border-2 border-gray-200" style={{ height: '700px' }}>
          {!pdfError ? (
            <>
              <iframe
                src={`${preview.pdfUrl || getRawFileUrl(source?.file_id)}#toolbar=1&navpanes=1&scrollbar=1`}
                className="w-full h-full rounded-lg"
                title="PDF Preview"
                onLoad={() => {
                  setPdfLoaded(true);
                  setPdfError(false);
                }}
                onError={() => {
                  console.log('PDF load error');
                  setPdfError(true);
                }}
              />
              
              {/* Alternative embed for better compatibility */}
              <object
                data={preview.pdfUrl || getRawFileUrl(source?.file_id)}
                type="application/pdf"
                className="w-full h-full rounded-lg"
                style={{ display: 'none' }}
              >
                <embed
                  src={preview.pdfUrl || getRawFileUrl(source?.file_id)}
                  type="application/pdf"
                  className="w-full h-full rounded-lg"
                />
              </object>
            </>
          ) : (
            /* Fallback for browsers that don't support PDF viewing */
            <div className="flex items-center justify-center bg-gray-50 rounded-lg h-full">
              <div className="text-center">
                <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-600 mb-4">PDF preview not available in this browser</p>
                <div className="space-y-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => window.open(preview.pdfUrl || getRawFileUrl(source?.file_id), '_blank')}
                    className="text-xs mr-2"
                  >
                    <ExternalLink className="h-3 w-3 mr-1" />
                    Open PDF in new tab
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      const downloadUrl = (preview.pdfUrl || getRawFileUrl(source?.file_id)) + '?download=true';
                      const link = document.createElement('a');
                      link.href = downloadUrl;
                      link.download = preview.title || 'document.pdf';
                      link.click();
                    }}
                    className="text-xs"
                  >
                    <HardDrive className="h-3 w-3 mr-1" />
                    Download PDF
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
        

      </div>
      
      {/* PDF Information */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Document Information</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-sm font-medium text-gray-700">Format:</span>
            <p className="text-sm text-gray-600">{preview.format}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-700">File Size:</span>
            <p className="text-sm text-gray-600">{preview.fileSize}</p>
          </div>
          {preview.pageCount !== 'Unknown' && (
            <div>
              <span className="text-sm font-medium text-gray-700">Pages:</span>
              <p className="text-sm text-gray-600">{preview.pageCount}</p>
            </div>
          )}
          {preview.uploadedAt && (
            <div>
              <span className="text-sm font-medium text-gray-700">Uploaded:</span>
              <p className="text-sm text-gray-600">{formatDate(preview.uploadedAt)}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const renderMetadataPreview = () => (
    <div className="space-y-6">
      {/* File Information */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-center space-x-2 mb-3">
          <File className="h-5 w-5 text-gray-500" />
          <h4 className="text-sm font-medium text-gray-900">File Information</h4>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-sm font-medium text-gray-700">Format:</span>
            <p className="text-sm text-gray-600">{preview.format}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-700">File Size:</span>
            <p className="text-sm text-gray-600">{preview.fileSize}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-700">Status:</span>
            <p className="text-sm text-gray-600 capitalize">{preview.processingStatus}</p>
          </div>
          {preview.uploadedAt && (
            <div>
              <span className="text-sm font-medium text-gray-700">Uploaded:</span>
              <p className="text-sm text-gray-600">{formatDate(preview.uploadedAt)}</p>
            </div>
          )}
        </div>
        
        {preview.featuresAvailable && preview.featuresAvailable.length > 0 && (
          <div className="mt-4">
            <span className="text-sm font-medium text-gray-700">Available Features:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {preview.featuresAvailable.map((feature) => (
                <Badge key={feature} variant="outline" className="text-xs">
                  {feature}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          transition={{ type: "spring", duration: 0.3 }}
          className="bg-white rounded-xl shadow-xl max-w-5xl w-full max-h-[95vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              {preview && React.createElement(getPreviewIcon(preview.type), {
                className: "h-6 w-6 text-gray-700"
              })}
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Preview</h2>
                <p className="text-sm text-gray-500">{source?.title || 'Unknown file'}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(95vh-120px)]">
            {renderPreviewContent()}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default FilePreview; 