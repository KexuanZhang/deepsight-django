import { config } from "@/config";

const API_BASE_URL = config.API_BASE_URL;

// Function to process report markdown content and fix image URLs
export const processReportMarkdownContent = (content: string, notebookId: string, useMinIOUrls = false): string => {
  if (!content) return content;
  
  console.log('processReportMarkdownContent called with:', { notebookId, contentLength: content.length, useMinIOUrls });
  
  // If using MinIO URLs, content should already have direct MinIO URLs from backend
  if (useMinIOUrls) {
    console.log('Using MinIO URLs - content should already have direct URLs');
    return content;
  }
  
  // Legacy processing for API URLs
  // Convert HTML img tags with knowledge_base_item paths to markdown syntax
  // Pattern: <img src="../../../../knowledge_base_item/2025-06/f_3/images/_page_6_Figure_0.jpeg" alt="Figure 2" style="max-height: 500px;">
  const htmlImagePattern = /<img\s+src="([^"]*knowledge_base_item[^"]*)"(?:\s+alt="([^"]*)")?[^>]*>/g;
  
  let processedContent = content.replace(htmlImagePattern, (match, imagePath, altText = '') => {
    console.log('Processing HTML image:', { imagePath, altText, fullMatch: match });
    
    // Extract file ID from path pattern: knowledge_base_item/yyyy-mm/f_ID/images/filename
    const fileIdMatch = imagePath.match(/f_(\d+)\/images\//);
    if (!fileIdMatch) {
      console.warn('Could not extract file ID from path:', imagePath);
      return match;
    }
    
    const fileId = fileIdMatch[1];
    const imageName = imagePath.split('/').pop();
    
    // Use correct API endpoint format
    const imageUrl = `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/images/${imageName}`;
    console.log('Generated image URL for HTML->Markdown conversion:', imageUrl);
    
    // Convert to markdown syntax so it gets processed by AuthenticatedImage component
    return `![${altText}](${imageUrl})`;
  });
  
  // Also handle markdown image syntax: ![alt text](image_path)
  const markdownImagePattern = /!\[([^\]]*)\]\(([^)]*knowledge_base_item[^)]*)\)/g;
  
  processedContent = processedContent.replace(markdownImagePattern, (match, altText, imagePath) => {
    console.log('Processing markdown image:', { altText, imagePath });
    
    // Extract file ID from path pattern: knowledge_base_item/yyyy-mm/f_ID/images/filename
    const fileIdMatch = imagePath.match(/f_(\d+)\/images\//);
    if (!fileIdMatch) {
      console.warn('Could not extract file ID from path:', imagePath);
      return match;
    }
    
    const fileId = fileIdMatch[1];
    const imageName = imagePath.split('/').pop();
    
    // Use correct API endpoint format
    const imageUrl = `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/images/${imageName}`;
    console.log('Generated markdown image URL:', imageUrl);
    
    return `![${altText}](${imageUrl})`;
  });
  
  // Additionally convert HTML img tags that already have the API /files/{id}/images/ path
  const htmlImageFilesPattern = /<img\s+src="([^"\s]*\/files\/(\d+)\/images\/[^"\s]+)"(?:\s+alt="([^"]*)")?[^>]*>/g;

  processedContent = processedContent.replace(htmlImageFilesPattern, (match, imagePath, fileId, altText = '') => {
    const imageName = imagePath.split('/').pop();
    const imageUrl = `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/images/${imageName}`;
    console.log('Converted existing API HTML image to markdown:', { imageUrl });
    return `![${altText}](${imageUrl})`;
  });

  // Also handle markdown images that already contain the /files/{id}/images/ path (ensure correct notebook)
  const markdownImageFilesPattern = /!\[([^\]]*)\]\(([^)]+\/files\/(\d+)\/images\/[^)]+)\)/g;

  processedContent = processedContent.replace(markdownImageFilesPattern, (match, altText, imagePath, fileId) => {
    const imageName = imagePath.split('/').pop();
    const imageUrl = `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/images/${imageName}`;
    console.log('Normalising existing API markdown image URL:', { imageUrl });
    return `![${altText}](${imageUrl})`;
  });

  return processedContent;
};

// Function to get file content with MinIO URLs
export const getFileContentWithMinIOUrls = async (fileId: string, notebookId: string, expires = 86400) => {
  try {
    const response = await fetch(`${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/content/?expires=${expires}`, {
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    if (data.success) {
      return data.data;
    } else {
      throw new Error(data.error || 'Failed to fetch content with MinIO URLs');
    }
  } catch (error) {
    console.error('Error fetching content with MinIO URLs:', error);
    throw error;
  }
};