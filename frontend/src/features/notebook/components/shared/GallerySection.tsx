import React, { useState, useEffect } from 'react';
import { Button } from "@/shared/components/ui/button";
import { Settings, Image as ImageIcon, Loader2, X, ZoomIn, ChevronDown, ChevronUp, Camera } from 'lucide-react';
import sourceService from "@/features/notebook/services/SourceService";
import { config } from "@/config";
// Define the missing types locally
interface GalleryImage {
  name: string;
  caption: string;
  blobUrl?: string;
  loading?: boolean;
  imageUrl?: string | null;
}

interface ExtractResult {
  success: boolean;
  message?: string;
  images?: string[];
  result?: {
    statistics?: {
      final_frames?: number;
    };
  };
}

interface GallerySectionProps {
  videoFileId: string;
  notebookId: string;
  onOpenModal: (modalType: string, content: React.ReactNode) => void;
  onCloseModal: (modalType: string) => void;
}

/**
 * GallerySection component renders a placeholder gallery box beneath the video player.
 * It provides a gear icon to adjust extraction parameters and a button to trigger the
 * /notebooks/{id}/extraction/video_image_extraction backend endpoint.
 */
const GallerySection: React.FC<GallerySectionProps> = ({ videoFileId, notebookId, onOpenModal, onCloseModal }) => {

  const [extractInterval, setExtractInterval] = useState(8); // seconds
  const [minWords, setMinWords] = useState(5);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [extractResult, setExtractResult] = useState<ExtractResult | null>(null);
  const [images, setImages] = useState<GalleryImage[]>([]);
  const [visibleCount, setVisibleCount] = useState(40);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const API_BASE_URL = config.API_BASE_URL;

  // Handle settings modal
  const handleSettingsSave = () => {
    setShowSettings(false);
    onCloseModal('gallerySettings');
  };

  const handleSettingsCancel = () => {
    setShowSettings(false);
    onCloseModal('gallerySettings');
  };

  // Create settings content as a function that will be re-evaluated on each render
  const createSettingsContent = () => (
    <div 
      className="bg-white rounded-lg shadow-lg w-96 p-6" 
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Settings className="h-5 w-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">Gallery Settings</h3>
        </div>
        <button onClick={handleSettingsCancel} className="text-gray-400 hover:text-gray-600">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="space-y-4">
        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">Extraction Interval (s)</label>
          <input
            type="number"
            min={1}
            step={1}
            value={extractInterval}
            onChange={(e) => setExtractInterval(Number(e.target.value) || 1)}
            onKeyDown={(e) => e.stopPropagation()}
            onClick={(e) => e.stopPropagation()}
            autoComplete="off"
            className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">Min Words</label>
          <input
            type="number"
            min={0}
            step={1}
            value={minWords}
            onChange={(e) => setMinWords(Number(e.target.value) || 0)}
            onKeyDown={(e) => e.stopPropagation()}
            onClick={(e) => e.stopPropagation()}
            autoComplete="off"
            className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      <div className="flex justify-end space-x-3 mt-6 pt-4 border-t">
        <Button variant="outline" onClick={handleSettingsCancel} className="text-gray-600 hover:text-gray-800">
          Cancel
        </Button>
        <Button onClick={handleSettingsSave} className="bg-blue-600 hover:bg-blue-700 text-white">
          Save
        </Button>
      </div>
    </div>
  );

  // Use effect to handle modal state
  useEffect(() => {
    if (showSettings) {
      onOpenModal('gallerySettings', createSettingsContent());
    }
  }, [showSettings, extractInterval, minWords]); // Re-create when state changes

  // Attempt to load gallery images when extraction completes or component mounts
  useEffect(() => {
    if (!notebookId || !videoFileId) return;

    // Auto-load if extraction result already exists or on component mount (user reloads page)
    loadImages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [extractResult, notebookId, videoFileId]);

  const loadImages = async () => {
    try {
      // Use new REST API endpoint to fetch images from database instead of figure_data.json
      const cacheBuster = Date.now();
      const url = `${API_BASE_URL}/notebooks/${notebookId}/files/${videoFileId}/images/?t=${cacheBuster}`;
      
      let imageList = [];
      try {
        const res = await fetch(url, { 
          credentials: 'include',
          cache: 'no-cache' // Ensure fresh data from server
        });
        if (res.ok && res.headers.get('content-type')?.includes('application/json')) {
          const data = await res.json();
          // data.images should be an array from the new REST API
          imageList = Array.isArray(data.images) ? data.images : [];
        }
      } catch (err) {
        console.log('Images API not accessible, gallery will be empty');
      }

      // Build filenames list from new REST API response
      const files = imageList.map((item: any) => {
        if (typeof item === 'string') {
          return { name: item, caption: '' };
        }
        
        // New API returns objects with image_caption, image_url, minio_object_key, etc.
        let filename = item.file_name || item.filename || item.name;
        
        // Try to extract filename from minio_object_key (best option)
        if (!filename && item.minio_object_key) {
          filename = item.minio_object_key.split('/').pop();
        }
        
        // Fallback to image_path
        if (!filename && item.image_path) {
          filename = item.image_path.split('/').pop();
        }
        
        return {
          name: filename,
          caption: item.image_caption || item.caption || '',
          imageUrl: item.image_url || null // Pre-signed URL if available
        };
      });
      setImages(files);
    } catch (error) {
      console.error('Failed to load images:', error);
    }
  };

  const handleLoadMore = () => {
    setVisibleCount((prev) => Math.min(prev + 40, images.length));
  };

  // Calculate how many images to display based on expand/collapse state
  const getDisplayCount = () => {
    if (isExpanded) {
      return visibleCount; // Show all loaded images when expanded
    } else {
      // Show only first row (approximately 6 images for 140px grid)
      return Math.min(6, images.length);
    }
  };

  // Fetch blobs lazily for visible images
  useEffect(() => {
    const fetchBlobs = async () => {
      const subset = images.slice(0, getDisplayCount());
      const needFetch = subset.filter((img) => !img.blobUrl && !img.loading);

      await Promise.all(
        needFetch.map(async (img) => {
          img.loading = true;
          try {
            // Use pre-signed URL if available, otherwise fetch through API
            let imageUrl;
            if (img.imageUrl) {
              imageUrl = img.imageUrl;
            } else {
              // Fallback to original API endpoint for direct file serving
              const cacheBuster = Date.now();
              imageUrl = `${API_BASE_URL}/notebooks/${notebookId}/files/${videoFileId}/images/${img.name}?t=${cacheBuster}`;
            }
            
            const res = await fetch(imageUrl, { 
              credentials: 'include',
              cache: 'no-cache'
            });
            if (res.ok) {
              const blob = await res.blob();
              img.blobUrl = URL.createObjectURL(blob);
            }
          } catch (e) {
            console.error('Image fetch failed', img.name, e);
          } finally {
            img.loading = false;
            setImages((prev) => [...prev]); // trigger re-render
          }
        })
      );
    };

    if (images.length) {
      fetchBlobs();
    }
  }, [visibleCount, images, API_BASE_URL, notebookId, videoFileId, isExpanded]);

  const handleExtract = async () => {
    if (!videoFileId || !notebookId) return;
    setIsExtracting(true);
    setExtractError(null);
    try {
      const payload = {
        video_file_id: videoFileId,
        extract_interval: extractInterval,
        min_words: minWords,
      };
      const response = await sourceService.extractVideoImages(notebookId, payload);
      setExtractResult(response);
      
      // Clear existing images and reload to ensure fresh data
      setImages([]);
      
      // Add a small delay to ensure backend has processed the new images
      setTimeout(() => {
        loadImages();
      }, 1000);
    } catch (error) {
      console.error('Image extraction failed:', error);
      setExtractError(error instanceof Error ? error.message : 'Extraction failed');
    } finally {
      setIsExtracting(false);
    }
  };



  return (
    <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg p-4 border border-indigo-200">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-indigo-500 rounded-full flex items-center justify-center">
            <ImageIcon className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1">
            <h4 className="text-sm font-medium text-gray-900">Gallery</h4>
            <p className="text-xs text-gray-600">Extract representative images from the video</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {/* Settings Button - gear icon only */}
          <button 
            onClick={() => setShowSettings(true)} 
            className="text-gray-500 hover:text-gray-700 p-1 rounded"
            title="Settings"
          >
            <Settings className="h-5 w-5" />
          </button>
          {/* Extract Image Button - white background */}
          <Button
            size="sm"
            variant="outline"
            onClick={handleExtract}
            disabled={isExtracting}
            className="text-xs font-medium bg-white hover:bg-gray-50"
          >
            {isExtracting ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin mr-1" />
                Extracting...
              </>
            ) : (
              <>
                <Camera className="h-3 w-3 mr-1" />
                Extract Image
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Extraction banners */}
      {extractError && (
        <div className="bg-red-50 border-l-4 border-red-400 p-3 rounded mb-3 text-sm text-red-700">
          {extractError}
        </div>
      )}
      {extractResult && extractResult.success && (
        <div className="bg-green-50 border-l-4 border-green-400 p-3 rounded mb-3 text-sm text-green-700">
          Extraction completed. {extractResult.result?.statistics?.final_frames ?? ''} images saved.
        </div>
      )}

      {/* Gallery grid */}
      {images.length === 0 ? (
        <p className="text-xs text-gray-500">No images yet. Run extraction or reload to view gallery.</p>
      ) : (
        <div>
          <div className="grid gap-2" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))" }}>
            {images.slice(0, getDisplayCount()).map((img, idx) => (
              <div
                key={idx}
                className="relative group border rounded overflow-hidden bg-white shadow-sm cursor-zoom-in"
                onClick={() => img.blobUrl && setSelectedImage(img.blobUrl)}
              >
                <img
                  src={img.blobUrl || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='128' viewBox='0 0 140 128'%3E%3Crect width='140' height='128' fill='%23f3f4f6'/%3E%3Cg transform='translate(60, 54)'%3E%3Cpath fill='%23d1d5db' d='M10.5 2.5A1.5 1.5 0 0 0 9 4v8a1.5 1.5 0 0 0 1.5 1.5h8a1.5 1.5 0 0 0 1.5-1.5V4a1.5 1.5 0 0 0-1.5-1.5h-8zM12 5.5a1 1 0 1 1 2 0 1 1 0 0 1-2 0zm-1 4l1.5-1.5L15 10.5h-4V9.5z'/%3E%3C/g%3E%3C/svg%3E"}
                  alt="thumbnail"
                  loading="lazy"
                  className="object-cover w-full h-32 group-hover:opacity-90 transition-opacity"/>
                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40">
                  <ZoomIn className="h-5 w-5 text-white" />
                </div>
              </div>
            ))}
          </div>
          
          {/* Expand/Collapse Button at gallery bottom edge */}
          {images.length > 6 && (
            <div className="flex justify-center mt-2">
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-gray-400 hover:text-gray-600 transition-colors p-1"
                title={isExpanded ? "Show less" : "Show all"}
              >
                {isExpanded ? (
                  <ChevronUp className="h-5 w-5" />
                ) : (
                  <ChevronDown className="h-5 w-5" />
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Load more button for large galleries - only show when expanded */}
      {isExpanded && visibleCount < images.length && (
        <div className="flex justify-center mt-4">
          <Button variant="outline" size="sm" onClick={handleLoadMore}>Load More</Button>
        </div>
      )}



      {/* Image Modal */}
      {selectedImage && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center" onClick={() => setSelectedImage(null)}>
          <div className="relative max-w-[90vw] max-h-[90vh]">
            <img src={selectedImage} alt="full" className="object-contain max-w-full max-h-full" />
            <button
              className="absolute top-2 right-2 text-white hover:text-gray-200"
              onClick={(e) => { e.stopPropagation(); setSelectedImage(null); }}
            >
              <X className="h-6 w-6" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default GallerySection; 