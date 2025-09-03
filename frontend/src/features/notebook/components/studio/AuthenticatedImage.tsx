import React, { useState, useEffect } from 'react';
import { Loader2, FileText } from 'lucide-react';
import { config } from "@/config";

const API_BASE_URL = config.API_BASE_URL;

interface AuthenticatedImageProps {
  src: string;
  alt?: string;
  title?: string;
}

// Enhanced Authenticated Image component that handles both MinIO URLs and API URLs
const AuthenticatedImage: React.FC<AuthenticatedImageProps> = ({ src, alt, title }) => {
  const [imgSrc, setImgSrc] = useState(src);
  const [imgError, setImgError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [attemptCount, setAttemptCount] = useState(0);

  useEffect(() => {
    console.log('AuthenticatedImage: Processing image with src:', src);
    setImgError(false);
    setIsLoading(true);
    setAttemptCount(0);
    
    // If the src is a blob URL or already a data URL, use it directly
    if (src.startsWith('blob:') || src.startsWith('data:')) {
      console.log('AuthenticatedImage: Using blob/data URL directly');
      setImgSrc(src);
      setIsLoading(false);
      return;
    }

    // Check if this is a direct MinIO URL (contains presigned URL patterns)
    if (isMinIOUrl(src)) {
      // For MinIO URLs, use directly without authentication
      console.log('AuthenticatedImage: Detected MinIO URL, using directly');
      setImgSrc(src);
      setIsLoading(false);
      return;
    }

    // If it's an API URL, try multiple strategies to fetch the image
    if (src.includes('/api/v1/notebooks/') && src.includes('/images/')) {
      console.log('AuthenticatedImage: Detected API URL, fetching with credentials');
      fetchImageWithFallbacks(src);
    } else {
      // For external URLs, use directly
      console.log('AuthenticatedImage: Using external URL directly');
      setImgSrc(src);
      setIsLoading(false);
    }
  }, [src]);

  const isMinIOUrl = (url: string): boolean => {
    // Check if URL looks like a MinIO pre-signed URL
    const isMinIO = (
      url.includes('X-Amz-Algorithm') ||
      url.includes('X-Amz-Credential') ||
      url.includes('X-Amz-Signature') ||
      url.includes('?AWSAccessKeyId=') ||
      url.includes('&Signature=') ||
      (url.includes('localhost:9000') || url.includes('minio')) && url.includes('?')
    );
    
    console.log('AuthenticatedImage: isMinIOUrl check for', url.substring(0, 100), '... Result:', isMinIO);
    return isMinIO;
  };

  const fetchImageWithFallbacks = async (originalSrc: string) => {
    const strategies = [
      // Strategy 1: Try the original URL with credentials
      async () => {
        console.log('Strategy 1: Fetching image with credentials:', originalSrc);
        const response = await fetch(originalSrc, {
          credentials: 'include',
          headers: {
            'Accept': 'image/*,*/*'
          }
        });

        if (!response.ok) {
          const errorText = await response.text();
          console.log('Strategy 1 failed:', response.status, errorText);
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        console.log('Strategy 1 succeeded: Image blob URL created:', blobUrl);
        return blobUrl;
      },

      // Strategy 2: Try alternative path formats
      async () => {
        console.log('Strategy 2: Trying alternative path formats');
        
        // Extract components from URL: /api/v1/notebooks/{id}/files/{file_id}/images/{image_name}
        const urlMatch = originalSrc.match(/\/notebooks\/(\d+)\/files\/([^\/]+)\/images\/([^\/]+)$/);
        if (!urlMatch) throw new Error('Could not parse URL components');
        
        const [, notebookId, fileId, imageName] = urlMatch;
        
        // Try different API paths that might exist
        const alternativePaths = [
          `/files/${fileId}/images/${imageName}`,
          `/notebooks/${notebookId}/images/${imageName}`,
          `/images/${fileId}/${imageName}`,
          `/media/Users/u_1/knowledge_base_item/2025-07/f_${fileId}/images/${imageName}`,
        ];

        for (const altPath of alternativePaths) {
          try {
            const altUrl = `${API_BASE_URL}${altPath}`;
            console.log('Trying alternative path:', altUrl);
            
            const response = await fetch(altUrl, {
              credentials: 'include',
              headers: { 'Accept': 'image/*,*/*' }
            });

            if (response.ok) {
              const blob = await response.blob();
              const blobUrl = URL.createObjectURL(blob);
              console.log('Strategy 2 succeeded with path:', altUrl);
              return blobUrl;
            }
                  } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Unknown error';
          console.log('Alternative path failed:', altPath, errorMessage);
        }
        }
        
        throw new Error('All alternative paths failed');
      },

      // Strategy 3: Try to generate a placeholder data URL
      async () => {
        console.log('Strategy 3: Generating placeholder image');
        
        // Create a canvas-based placeholder with the figure information
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          throw new Error('Could not get canvas context');
        }
        
        canvas.width = 400;
        canvas.height = 300;

        // Draw placeholder background
        ctx.fillStyle = '#f8f9fa';
        ctx.fillRect(0, 0, 400, 300);

        // Draw border
        ctx.strokeStyle = '#dee2e6';
        ctx.lineWidth = 2;
        ctx.strokeRect(1, 1, 398, 298);

        // Draw icon
        ctx.fillStyle = '#6c757d';
        ctx.font = '24px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('🖼️', 200, 120);

        // Draw alt text
        if (alt) {
          ctx.fillStyle = '#495057';
          ctx.font = '16px Arial';
          ctx.fillText(alt, 200, 160);
        }

        // Draw "Image not available" text
        ctx.fillStyle = '#6c757d';
        ctx.font = '14px Arial';
        ctx.fillText('Image not available', 200, 190);
        
        // Extract image name from URL for display
        const imageName = originalSrc.split('/').pop();
        ctx.font = '12px Arial';
        ctx.fillText(imageName || 'unknown', 200, 220);

        // Convert canvas to data URL
        const dataUrl = canvas.toDataURL('image/png');
        console.log('Strategy 3 succeeded: Generated placeholder image');
        return dataUrl;
      }
    ];

    // Try each strategy in sequence
    for (let i = 0; i < strategies.length; i++) {
      try {
        setAttemptCount(i + 1);
        const fn = strategies[i]!;
        const result = await fn();
        setImgSrc(result);
        setIsLoading(false);
        setImgError(false);
        return; // Success!
      } catch (error) {
        console.error(`Strategy ${i + 1} failed:`, error);
        if (i === strategies.length - 1) {
          // All strategies failed
          console.error('All image loading strategies failed for:', originalSrc);
          setImgError(true);
          setIsLoading(false);
        }
      }
    }
  };

  // Cleanup blob URLs when component unmounts
  useEffect(() => {
    return () => {
      if (imgSrc && imgSrc.startsWith('blob:')) {
        URL.revokeObjectURL(imgSrc);
      }
    };
  }, [imgSrc]);

  return (
    <div className="my-4">
      {isLoading && (
        <div className="bg-gray-100 border border-gray-200 rounded-lg p-4 text-center text-gray-500">
          <div className="flex items-center justify-center space-x-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span className="text-sm">
              Loading image... {attemptCount > 0 && `(Attempt ${attemptCount})`}
            </span>
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
            console.error('Image failed to load after processing:', { src: imgSrc, alt, title });
            // For MinIO URLs, if they fail, mark as error since they should work directly
            if (isMinIOUrl(imgSrc)) {
              setImgError(true);
            }
          }}
          onLoad={(e) => {
            console.log('Image loaded successfully:', { src: imgSrc, alt });
          }}
        />
      )}

      {!isLoading && imgError && (
        <div className="bg-gray-100 border border-gray-200 rounded-lg p-4 text-center text-gray-500">
          <div className="flex items-center justify-center space-x-2">
            <FileText className="h-5 w-5" />
            <span className="text-sm">Image could not be loaded</span>
          </div>
          {alt && <p className="text-xs mt-1 text-gray-400">{alt}</p>}
          <p className="text-xs mt-1 text-gray-400 break-all">URL: {src}</p>
          <p className="text-xs mt-1 text-gray-400">
            {isMinIOUrl(src) ? 'MinIO URL may have expired' : `Tried ${attemptCount} loading strategies`}
          </p>
        </div>
      )}
    </div>
  );
};

export default AuthenticatedImage;