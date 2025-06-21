import apiService from './api';

// API Base URL for raw file access (should match the one in api.js)
const API_BASE_URL = 'http://localhost:8000/api/v1';

/**
 * File preview utilities for different file types
 */

// File type categories for preview handling
export const FILE_CATEGORIES = {
  TEXT: ['txt', 'md'],
  PDF: ['pdf'],
  PRESENTATION: ['ppt', 'pptx'],
  AUDIO: ['mp3', 'wav'],
  VIDEO: ['mp4'],
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
export function getPreviewType(fileExtension, metadata = {}) {
  const ext = fileExtension.toLowerCase().replace('.', '');
  
  if (FILE_CATEGORIES.TEXT.includes(ext)) {
    return PREVIEW_TYPES.TEXT_CONTENT;
  }
  
  if (FILE_CATEGORIES.PDF.includes(ext)) {
    return PREVIEW_TYPES.PDF_VIEWER;
  }
  
  if (FILE_CATEGORIES.PRESENTATION.includes(ext)) {
    return PREVIEW_TYPES.METADATA;
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
 * Check if a file type supports preview
 */
export function supportsPreview(fileExtension, metadata = {}) {
  const ext = fileExtension.toLowerCase().replace('.', '');
  const allSupportedTypes = [
    ...FILE_CATEGORIES.TEXT,
    ...FILE_CATEGORIES.PDF,
    ...FILE_CATEGORIES.PRESENTATION,
    ...FILE_CATEGORIES.AUDIO,
    ...FILE_CATEGORIES.VIDEO,
    ...FILE_CATEGORIES.URL
  ];
  
  return allSupportedTypes.includes(ext) || metadata.source_url;
}

/**
 * Generate preview data for different file types
 */
export async function generatePreview(source) {
  try {
    const { metadata, file_id } = source;
    const previewType = getPreviewType(metadata.file_extension || '', metadata);
    
    switch (previewType) {
      case PREVIEW_TYPES.TEXT_CONTENT:
        return await generateTextPreview(file_id, metadata);
      
      case PREVIEW_TYPES.PDF_VIEWER:
        return await generatePdfPreview(file_id, metadata);
      
      case PREVIEW_TYPES.URL_INFO:
        return await generateUrlPreview(metadata);
      
      case PREVIEW_TYPES.AUDIO_INFO:
        return await generateAudioPreview(metadata);
      
      case PREVIEW_TYPES.VIDEO_INFO:
        return await generateVideoPreview(metadata);
      
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
      error: error.message
    };
  }
}

/**
 * Generate text content preview
 */
async function generateTextPreview(fileId, metadata) {
  try {
    const response = await apiService.getParsedFile(fileId);
    if (!response.success) {
      throw new Error('Failed to fetch file content');
    }
    
    const content = response.data.content || '';
    
    return {
      type: PREVIEW_TYPES.TEXT_CONTENT,
      title: metadata.original_filename || 'Text Content',
      content: content,
      fullLength: content.length,
      wordCount: content.split(/\s+/).filter(word => word.length > 0).length,
      lines: content.split('\n').length,
      fileSize: formatFileSize(metadata.file_size),
      format: (metadata.file_extension || '').toUpperCase().replace('.', ''),
      uploadedAt: metadata.upload_timestamp
    };
  } catch (error) {
    throw new Error(`Failed to load text preview: ${error.message}`);
  }
}

/**
 * Generate URL preview
 */
async function generateUrlPreview(metadata) {
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
async function generateAudioPreview(metadata) {
  // Use the raw endpoint to serve the actual audio binary file
  const fileId = metadata.file_id;
  const audioUrl = `${API_BASE_URL}/files/${fileId}/raw`;
  
  // Check if we have parsed transcript content
  let transcriptContent = null;
  let hasTranscript = false;
  let wordCount = 0;
  
  try {
    const response = await apiService.getParsedFile(fileId);
    if (response.success && response.data.content) {
      transcriptContent = response.data.content;
      hasTranscript = transcriptContent.trim().length > 0;
      wordCount = transcriptContent.split(/\s+/).filter(word => word.length > 0).length;
    }
  } catch (error) {
    console.log('No transcript available for audio file:', error);
  }
  
  return {
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
}

/**
 * Generate video file preview
 */
async function generateVideoPreview(metadata) {
  // Use the raw endpoint to serve the actual video binary file
  const fileId = metadata.file_id;
  const videoUrl = `${API_BASE_URL}/files/${fileId}/raw`;
  
  // Check if we have parsed transcript content
  let transcriptContent = null;
  let hasTranscript = false;
  let wordCount = 0;
  
  try {
    const response = await apiService.getParsedFile(fileId);
    if (response.success && response.data.content) {
      transcriptContent = response.data.content;
      hasTranscript = transcriptContent.trim().length > 0;
      wordCount = transcriptContent.split(/\s+/).filter(word => word.length > 0).length;
    }
  } catch (error) {
    console.log('No transcript available for video file:', error);
  }
  
  return {
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
}

/**
 * Generate PDF file preview
 */
async function generatePdfPreview(fileId, metadata) {
  // Use the raw endpoint to serve the actual PDF binary file
  const pdfUrl = `${API_BASE_URL}/files/${fileId}/raw`;
  
  // Check if we have parsed PDF content
  let pdfContent = null;
  let hasParsedContent = false;
  let wordCount = 0;
  let error = null;
  
  try {
    const response = await apiService.getParsedFile(fileId);
    if (response.success && response.data.content) {
      pdfContent = response.data.content;
      hasParsedContent = pdfContent.trim().length > 0;
      wordCount = pdfContent.split(/\s+/).filter(word => word.length > 0).length;
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
      fileId: fileId
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
      error: error
    };
  }
}

/**
 * Generate metadata preview for other file types
 */
async function generateMetadataPreview(metadata) {
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
function extractDomain(url) {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname.replace('www.', '');
  } catch (error) {
    const match = url.match(/^https?:\/\/(?:www\.)?([^\/]+)/);
    return match ? match[1] : url;
  }
}

/**
 * Helper function to format file size
 */
function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return 'Unknown size';
  
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Helper function to format date
 */
export function formatDate(dateString) {
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