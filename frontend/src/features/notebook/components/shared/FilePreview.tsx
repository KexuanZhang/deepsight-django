import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Eye, FileText, Globe, Music, Video, File, HardDrive, Calendar, ExternalLink, Loader2, AlertCircle, RefreshCw, Trash2, Plus, ChevronLeft, CheckCircle, Clock, Upload, Link2, Youtube, Group, Presentation } from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { generatePreview, supportsPreview, PREVIEW_TYPES, formatDate, getVideoMimeType, getAudioMimeType, generateTextPreviewWithMinIOUrls } from "@/features/notebook/utils/filePreview";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import rehypeRaw from "rehype-raw";
import "highlight.js/styles/github.css";
import GallerySection from "@/features/notebook/components/shared/GallerySection";
import { Source, PreviewState, VideoErrorEvent, FileSource } from '@/shared/types';

// API Base URL for raw file access
import { config } from "@/config";

const API_BASE_URL = config.API_BASE_URL;

// Authenticated Image component for handling images with credentials
interface AuthenticatedImageProps {
  src: string;
  alt?: string;
  title?: string;
}

const AuthenticatedImage: React.FC<AuthenticatedImageProps> = ({ src, alt, title }) => {
  const [imgSrc, setImgSrc] = useState(src);
  const [imgError, setImgError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // If the src is a blob URL or already a data URL, use it directly
    if (src.startsWith('blob:') || src.startsWith('data:')) {
      setImgSrc(src);
      setIsLoading(false);
      return;
    }

    // Check if it's a MinIO URL (pre-signed URLs with X-Amz-Signature or minio host)
    const isMinIOUrl = src.includes('X-Amz-Signature') || 
                       src.includes('X-Amz-Algorithm') ||
                       (src.includes('minio') && src.includes(':9000')) ||
                       (src.includes('localhost:9000'));
    
    if (isMinIOUrl) {
      console.log('Using MinIO pre-signed URL directly (no auth needed):', src);
      setImgSrc(src);
      setIsLoading(false);
      return;
    }

    // If it's an API URL, fetch it with credentials and handle redirects
    if (src.includes('/api/v1/notebooks/') && src.includes('/images/')) {
      const fetchImageWithCredentials = async () => {
        try {
          console.log('Fetching image with credentials:', src);
          const response = await fetch(src, {
            credentials: 'include',
            headers: {
              'Accept': 'image/*,*/*'
            },
            redirect: 'manual' // Handle redirects manually
          });

          // Check if response is a redirect (status 302/301)
          if (response.status === 302 || response.status === 301) {
            const redirectUrl = response.headers.get('location');
            if (redirectUrl) {
              console.log('API returned redirect to:', redirectUrl);
              // Use the redirect URL directly (it's a pre-signed MinIO URL)
              setImgSrc(redirectUrl);
              setIsLoading(false);
              return;
            }
          }

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          const blob = await response.blob();
          const blobUrl = URL.createObjectURL(blob);
          setImgSrc(blobUrl);
          setIsLoading(false);
          console.log('Image blob URL created:', blobUrl);
        } catch (error) {
          console.error('Failed to fetch image with credentials:', error);
          setImgError(true);
          setIsLoading(false);
        }
      };

      fetchImageWithCredentials();
    } else {
      // For external URLs, use directly
      setImgSrc(src);
      setIsLoading(false);
    }
  }, [src]);

  return (
    <div className="my-4">
      {isLoading && (
        <div className="bg-gray-100 border border-gray-200 rounded-lg p-4 text-center text-gray-500">
          <div className="flex items-center justify-center space-x-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span className="text-sm">Loading image...</span>
          </div>
        </div>
      )}
      
      {!isLoading && !imgError && (
        <img 
          src={imgSrc} 
          alt={alt || 'Image'} 
          title={title}
          className="max-w-full h-auto rounded-lg border border-gray-200 shadow-sm"
          style={{ maxHeight: '500px' }}
          onError={(e) => {
            console.error('Image failed to load:', { src: imgSrc, alt, title });
            setImgError(true);
          }}
          onLoad={(e) => {
            console.log('Image loaded successfully:', { src: imgSrc, alt });
          }}
        />
      )}

      {!isLoading && imgError && (
        <div className="bg-gray-100 border border-gray-200 rounded-lg p-4 text-center text-gray-500">
          <div className="flex items-center justify-center space-x-2">
            <File className="h-5 w-5" />
            <span className="text-sm">Image could not be loaded</span>
          </div>
          {alt && <p className="text-xs mt-1 text-gray-400">{alt}</p>}
          <p className="text-xs mt-1 text-gray-400 break-all">URL: {src}</p>
        </div>
      )}
    </div>
  );
};

// Function to process markdown content and resolve image URLs
const processMarkdownContent = (content: string, fileId: string, notebookId: string, useMinIOUrls = false): string => {
  if (!content) return content;
  
  console.log('processMarkdownContent called with:', { fileId, notebookId, contentLength: content.length, useMinIOUrls });
  
  // If using MinIO URLs, the content should already have direct MinIO URLs
  // No processing needed as backend already converted them
  if (useMinIOUrls) {
    console.log('Using MinIO URLs - no processing needed');
    return content;
  }
  
  // Legacy processing for API URLs
  // Pattern to match markdown image syntax: ![alt text](image_path)
  const imagePattern = /!\[([^\]]*)\]\(([^)]+)\)/g;
  
  return content.replace(imagePattern, (match: string, altText: string, imagePath: string) => {
    console.log('Processing image:', { altText, imagePath });
    
    // Skip if it's already a full URL (http/https)
    if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
      return match;
    }
    
    // Handle relative paths that start with ../images/ or contain /images/
    if (imagePath.startsWith('../images/') || imagePath.includes('/images/')) {
      const imageName = imagePath.split('/').pop();
      const imageUrl = `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/images/${imageName}`;
      console.log('Generated image URL from relative path:', imageUrl);
      return `![${altText}](${imageUrl})`;
    }
    
    // Handle direct image filenames (like _page_0_Figure_10.jpeg)
    if (imagePath.match(/\.(jpg|jpeg|png|gif|bmp|webp)$/i) && !imagePath.includes('/')) {
      const imageUrl = `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/images/${imagePath}`;
      console.log('Generated image URL from filename:', imageUrl);
      return `![${altText}](${imageUrl})`;
    }
    
    // Return original if not an image path we can process
    return match;
  });
};

// Memoized markdown content component (same as StudioPanel)
interface MarkdownContentProps {
  content: string;
}

const MarkdownContent = React.memo<MarkdownContentProps>(({ content }) => (
  <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900">
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight, rehypeRaw]}
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
        img: ({ src, alt, title, ...props }) => {
          if (!src) return null;
          return <AuthenticatedImage src={src} alt={alt} title={title} />;
        },
        a: ({href, children}) => (
          <a 
            href={href} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 underline"
          >
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  </div>
));

MarkdownContent.displayName = 'MarkdownContent';

interface FilePreviewState {
  preview: PreviewState | null;
  isLoading: boolean;
  error: string | null;
  audioError: boolean;
  audioLoaded: boolean;
  videoError: boolean;
  videoLoaded: boolean;
  modals: {
    [key: string]: React.ReactNode;
  };
}

interface FilePreviewComponentProps {
  source: Source;
  isOpen: boolean;
  onClose: () => void;
  notebookId: string;
  useMinIOUrls?: boolean;
}

const FilePreview: React.FC<FilePreviewComponentProps> = ({ source, isOpen, onClose, notebookId, useMinIOUrls = false }) => {
  // Consolidate all state into a single object to avoid hook order issues
  const [state, setState] = useState<FilePreviewState>({
    preview: null,
    isLoading: false,
    error: null,
    audioError: false,
    audioLoaded: false,
    videoError: false,
    videoLoaded: false,
    modals: {}
  });

  // Helper function to update state
  const updateState = (updates: Partial<FilePreviewState>) => {
    setState(prevState => ({ ...prevState, ...updates }));
  };

  // Modal handlers
  const openModal = (modalType: string, content: React.ReactNode) => {
    updateState({
      modals: { ...state.modals, [modalType]: content }
    });
  };

  const closeModal = (modalType: string) => {
    const newModals = { ...state.modals };
    delete newModals[modalType];
    updateState({ modals: newModals });
  };

  // Helper function to get raw file URL
  const getRawFileUrl = (fileId: string) => {
    return notebookId ? 
      `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/raw/` : 
      `${API_BASE_URL}/files/${fileId}/raw`;
  };

  useEffect(() => {
    if (isOpen && source && source.metadata?.file_extension && supportsPreview(source.metadata.file_extension, source.metadata)) {
      loadPreview();
    }
    
    // Cleanup function to revoke blob URLs
    return () => {
      if (state.preview?.audioUrl && state.preview.audioUrl.startsWith('blob:')) {
        URL.revokeObjectURL(state.preview.audioUrl);
      }
      if (state.preview?.videoUrl && state.preview.videoUrl.startsWith('blob:')) {
        URL.revokeObjectURL(state.preview.videoUrl);
      }
    };
  }, [isOpen, source, notebookId, useMinIOUrls]);

  const loadPreview = async () => {
    if (!source) return;
    
    console.log('FilePreview: Loading preview for source:', source);
    console.log('FilePreview: Notebook ID:', notebookId, 'Use MinIO URLs:', useMinIOUrls);
    
    updateState({
      isLoading: true,
      error: null,
      audioError: false,
      audioLoaded: false,
      videoError: false,
      videoLoaded: false
    });
    
    try {
      let previewData;
      
      // Check if we should use MinIO URLs for text content (but NOT for PDFs)
      if (useMinIOUrls && source.metadata?.file_extension && source.file_id && source.metadata &&
          ['.md', '.txt', '.ppt', '.pptx', '.doc', '.docx'].includes(source.metadata.file_extension.toLowerCase())) {
        console.log('FilePreview: Using MinIO URLs for text preview generation');
        const fileSource: FileSource = source as FileSource;
        previewData = await generateTextPreviewWithMinIOUrls(source.file_id, source.metadata, fileSource);
      } else {
        console.log('FilePreview: Using regular preview generation');
        // Pass useMinIOUrls flag to generatePreview so PDFs and other files can use MinIO URLs properly
        previewData = await generatePreview(source as FileSource, notebookId, useMinIOUrls);
      }
      
      console.log('FilePreview: Preview data loaded:', previewData);
      updateState({ preview: previewData, isLoading: false });
    } catch (err) {
      console.error('FilePreview: Error loading preview:', err);
      updateState({ error: err instanceof Error ? err.message : 'Unknown error', isLoading: false });
    }
  };

  const getPreviewIcon = (type: string) => {
    switch (type) {
      case PREVIEW_TYPES.TEXT_CONTENT:
        // Check if this is a presentation file
        const fileExt = source?.metadata?.file_extension?.toLowerCase() || '';
        if (['.ppt', '.pptx'].includes(fileExt)) {
          return Presentation;
        }
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

  const renderTextPreview = () => {
    if (!state.preview) return null;
    
    // Debug: show processed content and image URLs
    const processedContent = processMarkdownContent(state.preview.content, source.file_id || '', notebookId, useMinIOUrls);
    
    // Determine the appropriate icon based on file extension
    const fileExt = source?.metadata?.file_extension?.toLowerCase() || '';
    const isPresentation = ['.ppt', '.pptx'].includes(fileExt);
    const IconComponent = isPresentation ? Presentation : FileText;
    const iconColor = isPresentation ? 'text-orange-500' : 'text-blue-500';
    
    return (
      <div className="space-y-4">
        <div className="flex items-center space-x-2 mb-4">
          <IconComponent className={`h-5 w-5 ${iconColor}`} />
          <h3 className="font-medium text-gray-900">{state.preview.title}</h3>
        </div>
        
        
        <div className="flex flex-wrap gap-2 mb-4">
          <Badge variant="secondary">
            <HardDrive className="h-3 w-3 mr-1" />
            {state.preview.wordCount} words
          </Badge>
          <Badge variant="secondary">
            <FileText className="h-3 w-3 mr-1" />
            {state.preview.lines || 0} lines
          </Badge>
          {state.preview.fileSize && (
            <Badge variant="secondary">
              <HardDrive className="h-3 w-3 mr-1" />
              {state.preview.fileSize}
            </Badge>
          )}
          {state.preview.format && (
            <Badge variant="secondary">
              {state.preview.format}
            </Badge>
          )}
        </div>

        <div className="bg-gray-50 rounded-lg p-6 max-h-[600px] overflow-y-auto">
          <MarkdownContent content={processedContent} />
        </div>
      </div>
    );
  };

  const renderUrlPreview = () => {
    if (!state.preview) return null;
    
    return (
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
            {Math.round((state.preview.contentLength || 0) / 1000)}k chars
          </Badge>
          {state.preview.extractedAt && (
            <Badge variant="secondary">
              <Calendar className="h-3 w-3 mr-1" />
              {formatDate(state.preview.extractedAt)}
            </Badge>
          )}
          {state.preview.domain && (
            <Badge variant="secondary">
              <Globe className="h-3 w-3 mr-1" />
              {state.preview.domain}
            </Badge>
          )}
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-700">Source URL:</span>
            <Button
              size="sm"
              variant="outline"
              onClick={() => window.open(state.preview?.url, '_blank')}
              className="h-6 px-2 text-xs"
            >
              <ExternalLink className="h-3 w-3 mr-1" />
              Open
            </Button>
          </div>
          <p className="text-sm text-blue-600 break-all">{state.preview?.url}</p>
          
          {state.preview?.content && (
            <div className="mt-4">
              <span className="text-sm font-medium text-gray-700">Description:</span>
              <p className="text-sm text-gray-600 mt-1">{state.preview?.content}</p>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderAudioPreview = () => {
    if (!state.preview) return null;
    
    return (
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
          onError={(e: React.SyntheticEvent<HTMLAudioElement>) => {
            console.error('Audio load error:', e);
            const audioElement = e.target as HTMLAudioElement;
            console.error('Audio error details:', {
              error: audioElement.error,
              networkState: audioElement.networkState,
              readyState: audioElement.readyState,
              src: audioElement.src
            });
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
            src={state.preview.audioUrl} 
            type={getAudioMimeType(state.preview.format)} 
          />
          {/* Fallback source with generic MIME type */}
          <source 
            src={state.preview.audioUrl} 
            type={`audio/${state.preview.format.toLowerCase()}`} 
          />
          Your browser does not support the audio element.
        </audio>
        
        {state.audioError && (
          <div className="mt-2 text-xs text-center">
            <span className="text-red-500">⚠️ Audio file could not be loaded</span>
          </div>
        )}
      </div>
      
      {/* Transcript Content Display */}
      {state.preview.hasTranscript && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <FileText className="h-4 w-4 text-white" />
                </div>
                <div className="flex-1">
                  <h4 className="text-base font-semibold text-gray-900">Audio Transcript</h4>
                  {/* Document Stats */}
                  <div className="flex flex-wrap gap-2 mt-2 -ml-1">
                    <Badge variant="secondary">
                      <FileText className="h-3 w-3 mr-1" />
                      {state.preview.wordCount} words
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="p-6 max-h-[600px] overflow-y-auto">
            <MarkdownContent content={state.preview.content} />
          </div>
        </div>
      )}

      {/* File Information */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-900 mb-3">File Information</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-sm font-medium text-gray-700">Format:</span>
            <p className="text-sm text-gray-600">{state.preview.format}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-700">File Size:</span>
            <p className="text-sm text-gray-600">{state.preview.fileSize}</p>
          </div>
          {state.preview.duration !== 'Unknown' && (
            <div>
              <span className="text-sm font-medium text-gray-700">Duration:</span>
              <p className="text-sm text-gray-600">{state.preview.duration}</p>
            </div>
          )}
          {state.preview.sampleRate !== 'Unknown' && (
            <div>
              <span className="text-sm font-medium text-gray-700">Sample Rate:</span>
              <p className="text-sm text-gray-600">{state.preview.sampleRate}</p>
            </div>
          )}
          {state.preview.language && state.preview.language !== 'Unknown' && (
            <div>
              <span className="text-sm font-medium text-gray-700">Language:</span>
              <p className="text-sm text-gray-600 capitalize">{state.preview.language}</p>
            </div>
          )}
        </div>
      </div>
      </div>
    );
  };

  const renderVideoPreview = () => {
    if (!state.preview) return null;
    
    // Format-specific compatibility info
    const getFormatCompatibility = (format: string) => {
      const formatLower = format.toLowerCase();
      const compatibilityInfo: Record<string, {
        supported: boolean | string;
        reason: string;
        suggestion?: string;
      }> = {
        'mkv': {
          supported: true,
          reason: 'MKV files have limited browser support',
          suggestion: 'If playback fails, try downloading the file and playing in VLC or another media player'
        },
        'flv': {
          supported: false,
          reason: 'FLV format is no longer supported by modern browsers',
          suggestion: 'Consider converting to MP4 format for web playback'
        },
        'wmv': {
          supported: false,
          reason: 'WMV files are not supported in most browsers',
          suggestion: 'Try downloading the file and playing in a Windows media player'
        },
        'avi': {
          supported: 'partial',
          reason: 'AVI support depends on the internal codecs used',
          suggestion: 'If playback fails, download and use a dedicated media player'
        },
        'webm': {
          supported: true,
          reason: 'WebM is well-supported in modern browsers'
        },
        'mp4': {
          supported: true,
          reason: 'MP4 is universally supported'
        },
        'mov': {
          supported: 'partial',
          reason: 'MOV support varies by browser and codec',
          suggestion: 'If playback fails, try Safari or download the file'
        }
      };
      
      return compatibilityInfo[formatLower] || {
        supported: 'unknown',
        reason: 'Browser support for this format may vary'
      };
    };

    const compatibility = getFormatCompatibility(state.preview.format);
    const isUnsupported = compatibility.supported === false;

    return (
      <div className="space-y-6">
        {/* Video Section */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
                <Video className="h-5 w-5 text-white" />
              </div>
              <div className="flex-1">
                <h4 className="text-sm font-medium text-gray-900">
                  {isUnsupported ? 'Video File' : 'Video Player'}
                </h4>
                <p className="text-xs text-gray-600">
                  {isUnsupported 
                    ? 'Preview not available in browser' 
                    : compatibility.supported === true 
                      ? 'Click play to watch the video file'
                      : 'Browser compatibility may be limited'}
                </p>
              </div>
            </div>
            {/* Download Button */}
            <Button
              size="sm"
              variant={isUnsupported ? "default" : "outline"}
              onClick={async () => {
                try {
                  if (!state.preview?.videoUrl) return;
                  const response = await fetch(state.preview.videoUrl, {
                    credentials: 'include'
                  });
                  const blob = await response.blob();
                  const url = window.URL.createObjectURL(blob);
                  const link = document.createElement('a');
                  link.href = url;
                  // Remove existing extension if present before adding the format extension
                  const title = state.preview?.title || 'video';
                  const cleanTitle = title.replace(/\.[^/.]+$/, ''); // Remove any existing extension
                  link.download = `${cleanTitle}.${state.preview?.format?.toLowerCase()}`;
                  document.body.appendChild(link);
                  link.click();
                  document.body.removeChild(link);
                  window.URL.revokeObjectURL(url);
                } catch (error) {
                  console.error('Download failed:', error);
                }
              }}
              className="text-xs"
            >
              <HardDrive className="h-3 w-3 mr-1" />
              Download
            </Button>
          </div>

          {/* Format Not Supported Message */}
          {isUnsupported ? (
            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded">
              <div className="flex">
                <AlertCircle className="h-5 w-5 text-blue-400 mr-3 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm text-blue-800 font-medium">
                    {compatibility.reason}
                  </p>
                  <p className="text-xs text-blue-700 mt-1">
                    {compatibility.suggestion}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            /* Show video player for supported/partially supported formats */
            <>
              {/* Format Compatibility Warning for partial support */}
              {compatibility.supported === 'partial' && !state.videoError && (
                <div className="mb-3 bg-yellow-50 border-l-4 border-yellow-400 p-3 rounded">
                  <div className="flex">
                    <AlertCircle className="h-4 w-4 text-yellow-400 mr-2 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm text-yellow-800 font-medium">{compatibility.reason}</p>
                      {compatibility.suggestion && (
                        <p className="text-xs text-yellow-700 mt-1">{compatibility.suggestion}</p>
                      )}
                    </div>
                  </div>
                </div>
              )}
              
              {/* Video Element */}
              <video 
                controls 
                className="w-full rounded-lg bg-black"
                preload="metadata"
                controlsList="nodownload"
                style={{ maxHeight: '400px' }}
                onError={(e: React.SyntheticEvent<HTMLVideoElement>) => {
                  console.error('Video load error:', e);
                  const videoElement = e.target as HTMLVideoElement;
                  console.error('Video error details:', {
                    error: videoElement.error,
                    networkState: videoElement.networkState,
                    readyState: videoElement.readyState,
                    src: videoElement.src,
                    format: state.preview?.format
                  });
                  updateState({ videoError: true });
                }}
                onLoadedMetadata={() => {
                  updateState({ videoLoaded: true, videoError: false });
                }}
                onCanPlay={() => {
                  updateState({ videoLoaded: true, videoError: false });
                }}
              >
                <source 
                  src={state.preview.videoUrl} 
                  type={getVideoMimeType(state.preview.format)} 
                />
                {/* Fallback source with generic MIME type */}
                <source 
                  src={state.preview.videoUrl} 
                  type={`video/${state.preview.format.toLowerCase()}`} 
                />
                Your browser does not support the video element.
              </video>
              
              {/* Enhanced Error Display */}
              {state.videoError && (
                <div className="mt-3 bg-red-50 border-l-4 border-red-400 p-3 rounded">
                  <div className="flex">
                    <AlertCircle className="h-4 w-4 text-red-400 mr-2 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm text-red-800 font-medium">
                        Video file could not be loaded
                      </p>
                      <p className="text-xs text-red-700 mt-1">
                        {compatibility.reason}
                        {compatibility.suggestion && ` ${compatibility.suggestion}`}
                      </p>
                      <div className="mt-2 flex space-x-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => window.open(state.preview?.videoUrl, '_blank')}
                          className="text-xs bg-white hover:bg-gray-50"
                        >
                          <HardDrive className="h-3 w-3 mr-1" />
                          Download Video
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            updateState({ videoError: false });
                            // Force video reload by recreating the element
                            const video = document.querySelector('video');
                            if (video) {
                              video.load();
                            }
                          }}
                          className="text-xs"
                        >
                          <RefreshCw className="h-3 w-3 mr-1" />
                          Retry
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
        
        {/* Gallery (Image Extraction) */}
        {source.file_id && <GallerySection videoFileId={source.file_id} notebookId={notebookId} onOpenModal={openModal} onCloseModal={closeModal} />}

        {/* Transcript Content Display */}
        {state.preview.hasTranscript && (
          <div className="bg-gradient-to-r from-slate-50 to-gray-50 rounded-lg p-4 border border-slate-200">
            <div className="flex items-center space-x-3 mb-3">
              <div className="w-10 h-10 bg-slate-500 rounded-full flex items-center justify-center">
                <FileText className="h-5 w-5 text-white" />
              </div>
              <div className="flex-1">
                <h4 className="text-sm font-medium text-gray-900">Video Transcript</h4>
                <p className="text-xs text-gray-600">{state.preview.wordCount} words</p>
              </div>
            </div>
            <div className="bg-white rounded-lg p-4 max-h-[400px] overflow-y-auto">
              <MarkdownContent content={state.preview.content} />
            </div>
          </div>
        )}

        {/* File Information */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Video Information</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm font-medium text-gray-700">Format:</span>
              <p className="text-sm text-gray-600">{state.preview.format}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-700">File Size:</span>
              <p className="text-sm text-gray-600">{state.preview.fileSize}</p>
            </div>
            {state.preview.duration !== 'Unknown' && (
              <div>
                <span className="text-sm font-medium text-gray-700">Duration:</span>
                <p className="text-sm text-gray-600">{state.preview.duration}</p>
              </div>
            )}
            {state.preview.resolution !== 'Unknown' && (
              <div>
                <span className="text-sm font-medium text-gray-700">Resolution:</span>
                <p className="text-sm text-gray-600">{state.preview.resolution}</p>
              </div>
            )}
            {state.preview.language && state.preview.language !== 'Unknown' && (
              <div>
                <span className="text-sm font-medium text-gray-700">Language:</span>
                <p className="text-sm text-gray-600 capitalize">{state.preview.language}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderPdfContentPreview = () => {
    if (!state.preview) return null;
    
    return (
      <div className="space-y-6">
      {/* PDF Header with Action Buttons */}
      <div className="bg-gradient-to-r from-red-50 to-orange-50 rounded-lg p-4 border border-red-200">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-red-500 rounded-full flex items-center justify-center flex-shrink-0">
              <FileText className="h-5 w-5 text-white" />
            </div>
            <div className="flex-1">
              <h4 className="text-base font-semibold text-gray-900 mb-3">PDF Document</h4>
              {/* Document Stats - aligned with title */}
              <div className="flex flex-wrap gap-2 -ml-1">
                <Badge variant="secondary">
                  <FileText className="h-3 w-3 mr-1" />
                  {state.preview.wordCount} words
                </Badge>
                <Badge variant="secondary">
                  <HardDrive className="h-3 w-3 mr-1" />
                  {state.preview.fileSize}
                </Badge>
              </div>
            </div>
          </div>
          <div className="flex items-center h-full pt-2">
            <Button
              size="sm"
              variant="default"
              onClick={async () => {
                try {
                  if (!state.preview?.pdfUrl) return;
                  console.log('Opening PDF with URL:', state.preview.pdfUrl);
                  
                  // Open PDF in browser instead of downloading
                  const response = await fetch(state.preview.pdfUrl, {
                    credentials: 'include'
                  });
                  
                  if (!response.ok) {
                    throw new Error(`Failed to load PDF: ${response.status}`);
                  }
                  
                  const blob = await response.blob();
                  // Create blob with explicit PDF MIME type
                  const pdfBlob = new Blob([blob], { type: 'application/pdf' });
                  const url = window.URL.createObjectURL(pdfBlob);
                  
                  // Open PDF in new tab/window
                  window.open(url, '_blank');
                  
                  // Clean up the blob URL after a short delay
                  setTimeout(() => {
                    window.URL.revokeObjectURL(url);
                  }, 1000);
                  
                } catch (error) {
                  console.error('PDF open failed:', error);
                  // Fallback to opening URL directly
                  window.open(state.preview?.pdfUrl, '_blank');
                }
              }}
              className="text-xs font-medium"
            >
              <ExternalLink className="h-3 w-3 mr-1.5" />
              Open PDF
            </Button>
          </div>
        </div>
      </div>
      
      {/* Parsed Content Display */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-6 max-h-[600px] overflow-y-auto">
          <MarkdownContent content={processMarkdownContent(state.preview.content, source.file_id || '', notebookId, useMinIOUrls)} />
        </div>
      </div>
      </div>
    );
  };

  const renderPdfMetadataPreview = () => {
    if (!state.preview) return null;
    
    return (
    <div className="space-y-6">
      {/* PDF Error State */}
      <div className="bg-gradient-to-r from-red-50 to-orange-50 rounded-lg p-4 border border-red-200">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-red-500 rounded-full flex items-center justify-center">
              <FileText className="h-5 w-5 text-white" />
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-gray-900">PDF Document</h4>
              <p className="text-xs text-gray-600">Content extraction unavailable</p>
            </div>
          </div>
          <Button
            size="sm"
            variant="default"
            onClick={async () => {
              try {
                if (!state.preview?.pdfUrl) return;
                console.log('Opening PDF with URL:', state.preview.pdfUrl);
                
                // Open PDF in browser instead of downloading
                const response = await fetch(state.preview.pdfUrl, {
                  credentials: 'include'
                });
                
                if (!response.ok) {
                  throw new Error(`Failed to load PDF: ${response.status}`);
                }
                
                const blob = await response.blob();
                // Create blob with explicit PDF MIME type
                const pdfBlob = new Blob([blob], { type: 'application/pdf' });
                const url = window.URL.createObjectURL(pdfBlob);
                
                // Open PDF in new tab/window
                window.open(url, '_blank');
                
                // Clean up the blob URL after a short delay
                setTimeout(() => {
                  window.URL.revokeObjectURL(url);
                }, 1000);
                
              } catch (error) {
                console.error('PDF open failed:', error);
                // Fallback to opening URL directly
                window.open(state.preview?.pdfUrl, '_blank');
              }
            }}
            className="text-xs"
          >
            <ExternalLink className="h-3 w-3 mr-1" />
            Open PDF
          </Button>
        </div>
        
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-3 rounded">
          <p className="text-sm text-yellow-800">
            {state.preview.error || "PDF content could not be extracted. Click 'Download' to view the original document."}
          </p>
        </div>
      </div>
      
      {/* PDF Information */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Document Information</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-sm font-medium text-gray-700">Format:</span>
            <p className="text-sm text-gray-600">{state.preview.format}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-700">File Size:</span>
            <p className="text-sm text-gray-600">{state.preview.fileSize}</p>
          </div>
          {state.preview.pageCount !== 'Unknown' && (
            <div>
              <span className="text-sm font-medium text-gray-700">Pages:</span>
              <p className="text-sm text-gray-600">{state.preview.pageCount}</p>
            </div>
          )}
          {state.preview.uploadedAt && (
            <div>
              <span className="text-sm font-medium text-gray-700">Uploaded:</span>
              <p className="text-sm text-gray-600">{formatDate(state.preview.uploadedAt)}</p>
            </div>
          )}
        </div>
      </div>
    </div>
    );
  };

  const renderMetadataPreview = () => {
    if (!state.preview) return null;
    
    return (
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
            <p className="text-sm text-gray-600">{state.preview.format}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-700">File Size:</span>
            <p className="text-sm text-gray-600">{state.preview.fileSize}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-700">Status:</span>
            <p className="text-sm text-gray-600 capitalize">{state.preview.processingStatus}</p>
          </div>
          {state.preview.uploadedAt && (
            <div>
              <span className="text-sm font-medium text-gray-700">Uploaded:</span>
              <p className="text-sm text-gray-600">{formatDate(state.preview.uploadedAt)}</p>
            </div>
          )}
        </div>
        
        {state.preview.featuresAvailable && state.preview.featuresAvailable.length > 0 && (
          <div className="mt-4">
            <span className="text-sm font-medium text-gray-700">Available Features:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {state.preview.featuresAvailable.map((feature: string) => (
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
  };

  // Clean up blob URLs when component closes
  useEffect(() => {
    if (!isOpen && state.preview) {
      if (state.preview.audioUrl && state.preview.audioUrl.startsWith('blob:')) {
        URL.revokeObjectURL(state.preview.audioUrl);
      }
      if (state.preview.videoUrl && state.preview.videoUrl.startsWith('blob:')) {
        URL.revokeObjectURL(state.preview.videoUrl);
      }
    }
  }, [isOpen, state.preview]);

  if (!isOpen) return null;

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-gray-200">
        <div className="flex items-center space-x-3">
          {state.preview && React.createElement(getPreviewIcon(state.preview.type), {
            className: "h-6 w-6 text-gray-700"
          })}
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Preview</h2>
            <p className="text-sm text-gray-500">{source?.title || "Unknown file"}</p>
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

      {/* Render modals */}
      {Object.entries(state.modals).map(([modalType, content]) => (
        <div
          key={modalType}
          className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              closeModal(modalType);
            }
          }}
        >
          {content}
        </div>
      ))}
    </>
  );
};

export default FilePreview;