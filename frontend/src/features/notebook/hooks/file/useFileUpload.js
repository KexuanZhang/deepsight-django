import { useState, useCallback } from 'react';
import { VALIDATION_CONFIG } from '@/features/notebook/config/fileConfig';

/**
 * Custom hook for file upload and validation
 * Handles file validation, upload progress, and drag & drop functionality
 */
export const useFileUpload = () => {
  const [uploadProgress, setUploadProgress] = useState({});
  const [isDragOver, setIsDragOver] = useState(false);

  // Validate file
  const validateFile = useCallback((file) => {
    const extension = file.name.split(".").pop()?.toLowerCase() || "";
    const errors = [];
    const warnings = [];
    
    // Check file extension
    if (!extension) {
      errors.push("File must have an extension");
    } else if (!VALIDATION_CONFIG.allowedExtensions.includes(extension)) {
      errors.push(`File type "${extension}" is not supported. Allowed types: ${VALIDATION_CONFIG.allowedExtensions.join(', ')}`);
    }
    
    // Check file size
    if (file.size > VALIDATION_CONFIG.maxSize) {
      errors.push(`File size (${(file.size / (1024 * 1024)).toFixed(1)}MB) exceeds maximum allowed size of 100MB`);
    } else if (file.size < VALIDATION_CONFIG.minSize) {
      warnings.push("File is very small and may be empty");
    }
    
    // Check filename for potentially dangerous characters
    if (/[<>:"|?*]/.test(file.name)) {
      errors.push("Filename contains invalid characters");
    }
    
    // Check MIME type if available
    if (file.type) {
      const expectedType = VALIDATION_CONFIG.expectedMimeTypes[extension];
      if (expectedType && !file.type.startsWith(expectedType.split('/')[0])) {
        warnings.push(`File type "${file.type}" may not match extension "${extension}"`);
      }
    }
    
    return { valid: errors.length === 0, errors, warnings, extension };
  }, []);

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

  const handleDrop = useCallback((e, onFileDrop) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0 && onFileDrop) {
      onFileDrop(files[0]);
    }
  }, []);

  // Upload progress management
  const updateUploadProgress = useCallback((uploadId, progress) => {
    setUploadProgress(prev => ({
      ...prev,
      [uploadId]: progress
    }));
  }, []);

  const clearUploadProgress = useCallback((uploadId) => {
    setUploadProgress(prev => {
      const newProgress = { ...prev };
      delete newProgress[uploadId];
      return newProgress;
    });
  }, []);

  const generateUploadId = useCallback((prefix = 'upload') => {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Create virtual file from text
  const createTextFile = useCallback((text, filename = 'pasted_text.txt') => {
    const blob = new Blob([text], { type: 'text/plain' });
    return new File([blob], filename, { type: 'text/plain' });
  }, []);

  return {
    uploadProgress,
    isDragOver,
    validateFile,
    handleDragEnter,
    handleDragLeave,
    handleDragOver,
    handleDrop,
    updateUploadProgress,
    clearUploadProgress,
    generateUploadId,
    createTextFile,
    VALIDATION_CONFIG,
  };
};