import sourceService from "@/features/notebook/services/SourceService";

// API Base URL for raw file access (should match the one in api.js)
import { config } from "@/config";

const API_BASE_URL = config.API_BASE_URL;

// Type definitions
interface FileMetadata {
  textContent?: string;
  source_url?: string;
  file_extension?: string;
  original_filename?: string;
  content_type?: string;
  upload_timestamp?: string;
  processing_type?: string;
  source_type?: string;
  [key: string]: any;
}

interface FilePreviewOptions {
  showThumbnail?: boolean;
  maxTextLength?: number;
}

interface VideoFormat {
  [key: string]: string;
}

interface AudioFormat {
  [key: string]: string;
}

interface FileSource {
  metadata: FileMetadata;
  file_id: string;
  textContent?: string;
  [key: string]: any;
}

/**
 * File preview utilities for different file types
 */

// File type categories for preview handling
export const FILE_CATEGORIES = {
  TEXT: ['txt', 'md'],
  PDF: ['pdf'],
  PRESENTATION: ['ppt', 'pptx'],
  DOCUMENT: ['docx'],
  AUDIO: ['mp3', 'wav', 'm4a'],
  VIDEO: ['mp4', 'avi', 'mov', 'mkv', 'webm', 'wmv', 'm4v'],
  URL: ['url']
};

// Preview types
export const PREVIEW_TYPES = {
  TEXT_CONTENT: 'text_content',
  PDF_VIEWER: 'pdf_viewer',
  METADATA: 'metadata',
  THUMBNAIL: 'thumbnail',
  AUDIO_INFO: 'audio_info',
  VIDEO_INFO: 'video_info',
  URL_INFO: 'url_info'
};

/**
 * Determine the appropriate preview type for a file
 */
export function getPreviewType(fileExtension: string, metadata: FileMetadata = {}): string {
  const ext = fileExtension.toLowerCase().replace('.', '');
  
  if (FILE_CATEGORIES.TEXT.includes(ext)) {
    return PREVIEW_TYPES.TEXT_CONTENT;
  }
  
  if (FILE_CATEGORIES.PDF.includes(ext)) {
    return PREVIEW_TYPES.PDF_VIEWER;
  }
  
  if (FILE_CATEGORIES.PRESENTATION.includes(ext)) {
    return PREVIEW_TYPES.TEXT_CONTENT;
  }
  
  if (FILE_CATEGORIES.DOCUMENT.includes(ext)) {
    return PREVIEW_TYPES.TEXT_CONTENT;
  }
  
  if (FILE_CATEGORIES.AUDIO.includes(ext)) {
    return PREVIEW_TYPES.AUDIO_INFO;
  }
  
  if (FILE_CATEGORIES.VIDEO.includes(ext)) {
    return PREVIEW_TYPES.VIDEO_INFO;
  }
  
  if (FILE_CATEGORIES.URL.includes(ext) || metadata.source_url) {
    return PREVIEW_TYPES.URL_INFO;
  }
  
  return PREVIEW_TYPES.METADATA;
}

/**
 * Get proper MIME type for video formats
 */
export function getVideoMimeType(format: string): string {
  const mimeTypeMap: Record<string, string> = {
    'mp4': 'video/mp4',
    'avi': 'video/x-msvideo',
    'mov': 'video/quicktime',
    'mkv': 'video/mp4', // Use video/mp4 MIME type for MKV to improve browser compatibility
    'webm': 'video/webm',
    'flv': 'video/x-flv',
    'wmv': 'video/x-ms-wmv',
    '3gp': 'video/3gpp',
    'ogv': 'video/ogg',
    'm4v': 'video/x-m4v'
  };
  
  const normalizedFormat = format.toLowerCase().replace('.', '');
  return mimeTypeMap[normalizedFormat] || `video/${normalizedFormat}`;
}

/**
 * Get proper MIME type for audio formats
 */
export function getAudioMimeType(format: string): string {
  const mimeTypeMap: Record<string, string> = {
    'mp3': 'audio/mpeg',
    'wav': 'audio/wav',
    'm4a': 'audio/mp4',
    'aac': 'audio/aac',
    'ogg': 'audio/ogg',
    'flac': 'audio/flac'
  };
  
  const normalizedFormat = format.toLowerCase().replace('.', '');
  return mimeTypeMap[normalizedFormat] || `audio/${normalizedFormat}`;
}

/**
 * Check if a file type supports preview
 */
export function supportsPreview(fileExtension: string, metadata: FileMetadata = {}): boolean {
  // Ensure we have a safe string to operate on
  const ext = (fileExtension || '').toString().toLowerCase().replace('.', '');
  const allSupportedTypes = [
    ...FILE_CATEGORIES.TEXT,
    ...FILE_CATEGORIES.PDF,
    ...FILE_CATEGORIES.PRESENTATION,
    ...FILE_CATEGORIES.DOCUMENT,
    ...FILE_CATEGORIES.AUDIO,
    ...FILE_CATEGORIES.VIDEO,
    ...FILE_CATEGORIES.URL
  ];
  
  return allSupportedTypes.includes(ext) || Boolean(metadata.source_url);
}

/**
 * Generate preview data for different file types
 */
export async function generatePreview(source: FileSource, notebookId: string | null = null, useMinIOUrls: boolean = false): Promise<any> {
  try {
    const { metadata, file_id } = source;
    const previewType = getPreviewType(metadata.file_extension || '', metadata);
    
    switch (previewType) {
      case PREVIEW_TYPES.TEXT_CONTENT:
        return await generateTextPreview(file_id, metadata, source, useMinIOUrls);
      
      case PREVIEW_TYPES.PDF_VIEWER:
        return await generatePdfPreview(file_id, metadata, notebookId, source, useMinIOUrls);
      
      case PREVIEW_TYPES.URL_INFO:
        return await generateUrlPreview(metadata);
      
      case PREVIEW_TYPES.AUDIO_INFO:
        return await generateAudioPreview(file_id, metadata, notebookId);
      
      case PREVIEW_TYPES.VIDEO_INFO:
        return await generateVideoPreview(file_id, metadata, notebookId);
      
      case PREVIEW_TYPES.METADATA:
      default:
        return await generateMetadataPreview(metadata);
    }
  } catch (error) {
    console.error('Error generating preview:', error);
    return {
      type: 'error',
      title: 'Preview Error',
      content: 'Unable to generate preview for this file.',
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

/**
 * Generate text content preview
 */
async function generateTextPreview(fileId: string, metadata: FileMetadata, source: FileSource | null = null, useMinIOUrls: boolean = false): Promise<any> {
  try {
    let content = '';
    
    // Check if text content is stored directly in the source (for pasted text)
    if (source && source.textContent) {
      content = source.textContent;
    } else if (useMinIOUrls) {
      // Use MinIO content endpoint if available (for files with images like PPTX)
      try {
        const response = await sourceService.getFileContentWithMinIOUrls(fileId, 'default-notebook', 86400);
        if (response.success && response.data.content) {
          content = response.data.content;
          console.log('Text content: Using MinIO URLs for content with images');
        } else {
          throw new Error('MinIO content not available');
        }
      } catch (minioError) {
        console.log('MinIO content not available, trying regular endpoint:', minioError);
        // Fall back to regular endpoint
        const response = await sourceService.getParsedFile(fileId, 'default-notebook');
        if (!response.success) {
          throw new Error('Failed to fetch file content');
        }
        content = response.data.content || '';
      }
    } else {
      // Fetch from API for regular files
      const response = await sourceService.getParsedFile(fileId, 'default-notebook');
      if (!response.success) {
        throw new Error('Failed to fetch file content');
      }
      content = response.data.content || '';
    }
    
    return {
      type: PREVIEW_TYPES.TEXT_CONTENT,
      title: metadata.original_filename || 'Text Content',
      content: content,
      fullLength: content.length,
      wordCount: content.split(/\s+/).filter((word: string) => word.length > 0).length,
      lines: content.split('\n').length,
      fileSize: formatFileSize(metadata.file_size),
      format: (metadata.file_extension || '').toUpperCase().replace('.', ''),
      uploadedAt: metadata.upload_timestamp,
      usesMinIOUrls: useMinIOUrls
    };
  } catch (error) {
    throw new Error(`Failed to load text preview: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Generate URL preview
 */
async function generateUrlPreview(metadata: FileMetadata): Promise<any> {
  const sourceUrl = metadata.source_url || 'Unknown URL';
  const processingType = metadata.processing_method || 'website';
  
  try {
    // Try to get additional metadata from processing results
    const urlInfo = metadata.processing_metadata?.url_info || {};
    const structuredData = metadata.processing_metadata?.structured_data || {};
    
    return {
      type: PREVIEW_TYPES.URL_INFO,
      title: structuredData.title || urlInfo.domain || 'Website',
      content: structuredData.description || 'No description available',
      url: sourceUrl,
      domain: urlInfo.domain || extractDomain(sourceUrl),
      processingType: processingType,
      contentLength: metadata.content_length || 0,
      extractedAt: metadata.processing_timestamp || metadata.upload_timestamp
    };
  } catch (error) {
    return {
      type: PREVIEW_TYPES.URL_INFO,
      title: extractDomain(sourceUrl) || 'Website',
      content: 'Website content extracted',
      url: sourceUrl,
      domain: extractDomain(sourceUrl),
      processingType: processingType,
      contentLength: metadata.content_length || 0
    };
  }
}

/**
 * Generate audio file preview
 */
async function generateAudioPreview(fileId: string, metadata: FileMetadata, notebookId: string | null = null): Promise<any> {
  console.log('Generating audio preview for fileId:', fileId, 'metadata:', metadata, 'notebookId:', notebookId);
  
  // Validate required data
  if (!fileId) {
    throw new Error('File ID is required for audio preview');
  }
  
  // Create a blob URL for the audio file to handle authentication properly
  let audioUrl = null;
  try {
    const rawUrl = notebookId ? 
      `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/raw/` : 
      `${API_BASE_URL}/notebooks/files/${fileId}/raw/`;
    
    // Fetch the audio file with credentials
    const response = await fetch(rawUrl, {
      credentials: 'include',
      headers: {
        'Accept': 'audio/*,*/*'
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch audio file: ${response.status}`);
    }
    
    const blob = await response.blob();
    audioUrl = URL.createObjectURL(blob);
    console.log('Audio blob URL created:', audioUrl);
  } catch (error) {
    console.error('Failed to create audio blob URL:', error);
    // Fallback to direct URL (might not work in Chrome due to authentication issues)
    audioUrl = notebookId ? 
      `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/raw/` : 
      `${API_BASE_URL}/notebooks/files/${fileId}/raw/`;
  }
  
  // Check if we have parsed transcript content
  let transcriptContent = null;
  let hasTranscript = false;
  let wordCount = 0;
  
  try {
    const response = await sourceService.getParsedFile(fileId, 'default-notebook');
    if (response.success && response.data.content) {
      transcriptContent = response.data.content;
      hasTranscript = transcriptContent.trim().length > 0;
      wordCount = transcriptContent.split(/\s+/).filter((word: string) => word.length > 0).length;
      console.log('Audio transcript loaded successfully, word count:', wordCount);
    } else {
      console.log('No transcript content in response:', response);
    }
  } catch (error) {
    console.log('No transcript available for audio file:', error);
  }
  
  const previewData = {
    type: PREVIEW_TYPES.AUDIO_INFO,
    title: metadata.original_filename || 'Audio File',
    content: hasTranscript ? transcriptContent : 'Audio file ready for playback',
    hasTranscript: hasTranscript,
    wordCount: wordCount,
    fileSize: formatFileSize(metadata.file_size),
    format: (metadata.file_extension || '').toUpperCase().replace('.', ''),
    uploadedAt: metadata.upload_timestamp,
    duration: metadata.duration || 'Unknown',
    sampleRate: metadata.sample_rate || 'Unknown',
    language: metadata.language || 'Unknown',
    audioUrl: audioUrl,
    fileId: fileId
  };
  
  console.log('Audio preview data generated:', previewData);
  return previewData;
}

/**
 * Generate video file preview
 */
async function generateVideoPreview(fileId: string, metadata: FileMetadata, notebookId: string | null = null): Promise<any> {
  console.log('Generating video preview for fileId:', fileId, 'metadata:', metadata, 'notebookId:', notebookId);
  
  // Validate required data
  if (!fileId) {
    throw new Error('File ID is required for video preview');
  }
  
  // Create a blob URL for the video file to handle authentication properly
  let videoUrl = null;
  try {
    const rawUrl = notebookId ? 
      `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/raw/` : 
      `${API_BASE_URL}/notebooks/files/${fileId}/raw/`;
    
    // Fetch the video file with credentials
    const response = await fetch(rawUrl, {
      credentials: 'include',
      headers: {
        'Accept': 'video/*,*/*'
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch video file: ${response.status}`);
    }
    
    const blob = await response.blob();
    videoUrl = URL.createObjectURL(blob);
    console.log('Video blob URL created:', videoUrl);
  } catch (error) {
    console.error('Failed to create video blob URL:', error);
    // Fallback to direct URL (might not work in Chrome due to authentication issues)
    videoUrl = notebookId ? 
      `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/raw/` : 
      `${API_BASE_URL}/notebooks/files/${fileId}/raw/`;
  }
  
  // Check if we have parsed transcript content
  let transcriptContent = null;
  let hasTranscript = false;
  let wordCount = 0;
  
  try {
    const response = await sourceService.getParsedFile(fileId, 'default-notebook');
    if (response.success && response.data.content) {
      transcriptContent = response.data.content;
      hasTranscript = transcriptContent.trim().length > 0;
      wordCount = transcriptContent.split(/\s+/).filter((word: string) => word.length > 0).length;
      console.log('Video transcript loaded successfully, word count:', wordCount);
    } else {
      console.log('No transcript content in response:', response);
    }
  } catch (error) {
    console.log('No transcript available for video file:', error);
  }
  
  const previewData = {
    type: PREVIEW_TYPES.VIDEO_INFO,
    title: metadata.original_filename || 'Video File',
    content: hasTranscript ? transcriptContent : 'Video file ready for playback',
    hasTranscript: hasTranscript,
    wordCount: wordCount,
    fileSize: formatFileSize(metadata.file_size),
    format: (metadata.file_extension || '').toUpperCase().replace('.', ''),
    uploadedAt: metadata.upload_timestamp,
    duration: metadata.duration || 'Unknown',
    resolution: metadata.resolution || 'Unknown',
    language: metadata.language || 'Unknown',
    videoUrl: videoUrl,
    fileId: fileId
  };
  
  console.log('Video preview data generated:', previewData);
  return previewData;
}

/**
 * Generate PDF file preview
 */
async function generatePdfPreview(fileId: string, metadata: FileMetadata, notebookId: string | null = null, source: FileSource | null = null, useMinIOUrls: boolean = false): Promise<any> {
  // Generate PDF URL - use the raw endpoint which will redirect to MinIO if enabled
  const pdfUrl = notebookId ? 
    `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/raw/` : 
    `${API_BASE_URL}/notebooks/files/${fileId}/raw/`;
  
  console.log('PDF: Generated PDF URL:', pdfUrl, 'useMinIOUrls:', useMinIOUrls);
  
  // Check if we have parsed PDF content
  let pdfContent = null;
  let hasParsedContent = false;
  let wordCount = 0;
  let error = null;
  
  try {
    // Check if content is stored directly in the source (for consistency)
    if (source && source.textContent) {
      pdfContent = source.textContent;
      hasParsedContent = pdfContent.trim().length > 0;
      wordCount = pdfContent.split(/\s+/).filter((word: string) => word.length > 0).length;
    } else if (useMinIOUrls) {
      // Use MinIO content endpoint if available
      try {
        const response = await sourceService.getFileContentWithMinIOUrls(fileId, 'default-notebook', 86400);
        if (response.success && response.data.content) {
          pdfContent = response.data.content;
          hasParsedContent = pdfContent.trim().length > 0;
          wordCount = pdfContent.split(/\s+/).filter((word: string) => word.length > 0).length;
          console.log('PDF: Using MinIO content for PDF text');
        }
      } catch (minioError) {
        console.log('MinIO content not available for PDF, trying regular endpoint:', minioError);
        // Fall back to regular endpoint
        const response = await sourceService.getParsedFile(fileId, 'default-notebook');
        if (response.success && response.data.content) {
          pdfContent = response.data.content;
          hasParsedContent = pdfContent.trim().length > 0;
          wordCount = pdfContent.split(/\s+/).filter((word: string) => word.length > 0).length;
        }
      }
    } else {
      const response = await sourceService.getParsedFile(fileId, 'default-notebook');
      if (response.success && response.data.content) {
        pdfContent = response.data.content;
        hasParsedContent = pdfContent.trim().length > 0;
        wordCount = pdfContent.split(/\s+/).filter((word: string) => word.length > 0).length;
      }
    }
  } catch (err) {
    console.log('No parsed content available for PDF file:', err);
    error = 'PDF content extraction failed or not available';
  }
  
  // Return appropriate preview type based on content availability
  if (hasParsedContent) {
    return {
      type: PREVIEW_TYPES.TEXT_CONTENT,
      isPdfPreview: true,
      title: metadata.original_filename || 'PDF Document',
      content: pdfContent,
      fullLength: pdfContent.length,
      wordCount: wordCount,
      fileSize: formatFileSize(metadata.file_size),
      format: 'PDF',
      uploadedAt: metadata.upload_timestamp,
      pageCount: metadata.page_count || 'Unknown',
      pdfUrl: pdfUrl,
      fileId: fileId,
      usesMinIOUrls: useMinIOUrls
    };
  } else {
    return {
      type: PREVIEW_TYPES.METADATA,
      isPdfPreview: true,
      title: metadata.original_filename || 'PDF Document',
      content: 'PDF document ready for viewing',
      fileSize: formatFileSize(metadata.file_size),
      format: 'PDF',
      uploadedAt: metadata.upload_timestamp,
      pageCount: metadata.page_count || 'Unknown',
      pdfUrl: pdfUrl,
      fileId: fileId,
      error: error,
      usesMinIOUrls: useMinIOUrls
    };
  }
}

/**
 * Generate metadata preview for other file types
 */
async function generateMetadataPreview(metadata: FileMetadata): Promise<any> {
  return {
    type: PREVIEW_TYPES.METADATA,
    title: metadata.original_filename || 'File',
    content: `${(metadata.file_extension || '').toUpperCase().replace('.', '')} file uploaded and processed`,
    fileSize: formatFileSize(metadata.file_size),
    format: (metadata.file_extension || '').toUpperCase().replace('.', ''),
    uploadedAt: metadata.upload_timestamp,
    processingStatus: metadata.parsing_status || 'unknown',
    featuresAvailable: metadata.features_available || []
  };
}

/**
 * Helper function to extract domain from URL
 */
function extractDomain(url: string): string {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname.replace('www.', '');
  } catch (error) {
    const match = url.match(/^https?:\/\/(?:www\.)?([^\/]+)/);
    return match && match[1] ? match[1] : url;
  }
}

/**
 * Helper function to format file size
 */
function formatFileSize(bytes: number): string {
  if (!bytes || bytes === 0) return 'Unknown size';
  
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Helper function to format date
 */
export function formatDate(dateString: string): string {
  if (!dateString) return 'Unknown date';
  
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (error) {
    return 'Invalid date';
  }
} 

/**
 * Fetch file content with direct MinIO URLs for images
 */
export async function getFileContentWithMinIOUrls(fileId: string, expires: number = 86400): Promise<any> {
  try {
    const response = await sourceService.getFileContentWithMinIOUrls(fileId, 'default-notebook', expires);
    if (response.success) {
      return response.data;
    } else {
      throw new Error('Failed to fetch content with MinIO URLs');
    }
  } catch (error) {
    console.error('Error fetching content with MinIO URLs:', error);
    throw error;
  }
}

/**
 * Generate text content preview with MinIO URLs
 */
export async function generateTextPreviewWithMinIOUrls(fileId: string, metadata: FileMetadata, source: FileSource | null = null): Promise<any> {
  try {
    let content = '';
    
    // Check if text content is stored directly in the source (for pasted text)
    if (source && source.textContent) {
      content = source.textContent;
    } else {
      // Fetch content with MinIO URLs from API
      const contentData = await getFileContentWithMinIOUrls(fileId);
      content = contentData.content || '';
    }
    
    return {
      type: PREVIEW_TYPES.TEXT_CONTENT,
      title: metadata.original_filename || 'Text Content',
      content: content,
      fullLength: content.length,
      wordCount: content.split(/\s+/).filter((word: string) => word.length > 0).length,
      lines: content.split('\n').length,
      fileSize: formatFileSize(metadata.file_size),
      format: (metadata.file_extension || '').toUpperCase().replace('.', ''),
      uploadedAt: metadata.upload_timestamp,
      usesMinIOUrls: true
    };
  } catch (error) {
    throw new Error(`Failed to load text preview with MinIO URLs: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
} 