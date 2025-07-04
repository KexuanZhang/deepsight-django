import React, { useState, useEffect } from 'react';
import { Button } from '@/common/components/ui/button';
import { Settings, Image as ImageIcon, Loader2, X, ZoomIn } from 'lucide-react';
import apiService from '@/common/utils/api';
import { config } from '@/config';

/**
 * GallerySection component renders a placeholder gallery box beneath the video player.
 * It provides a gear icon to adjust extraction parameters and a button to trigger the
 * /notebooks/{id}/extraction/video_image_extraction backend endpoint.
 */
const GallerySection = ({ videoFileId, notebookId }) => {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [extractInterval, setExtractInterval] = useState(8); // seconds
  const [minWords, setMinWords] = useState(5);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractError, setExtractError] = useState(null);
  const [extractResult, setExtractResult] = useState(null);
  const [images, setImages] = useState([]);
  const [visibleCount, setVisibleCount] = useState(40);
  const [selectedImage, setSelectedImage] = useState(null);
  const API_BASE_URL = config.API_BASE_URL;

  // Attempt to load gallery images when extraction completes or component mounts
  useEffect(() => {
    if (!notebookId || !videoFileId) return;

    // Auto-load if extraction result already exists or on component mount (user reloads page)
    loadImages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [extractResult, notebookId, videoFileId]);

  const loadImages = async () => {
    try {
      // Try to fetch captions / manifest JSON to get ordered list of images
      const possibleFiles = ['figure_data.json', 'captions.json', 'manifest.json'];
      
      // Add cache-busting timestamp to ensure fresh data
      const cacheBuster = Date.now();

      let imageList = [];
      for (const filename of possibleFiles) {
        const url = `${API_BASE_URL}/notebooks/${notebookId}/files/${videoFileId}/images/${filename}?t=${cacheBuster}`;
        try {
          const res = await fetch(url, { 
            credentials: 'include',
            cache: 'no-cache' // Ensure fresh data from server
          });
          if (res.ok && res.headers.get('content-type')?.includes('application/json')) {
            const data = await res.json();
            // data could be an array or object with images key
            imageList = Array.isArray(data) ? data : data.images || [];
            if (imageList.length) break;
          }
        } catch (err) {
          // continue trying next filename
        }
      }

      // Build filenames list only (blob fetched lazily)
      const files = imageList.map((item) => {
        if (typeof item === 'string') {
          return { name: item, caption: '' };
        }
        // If object, try various fields to resolve filename
        let filename = item.file_name || item.filename || item.name;
        if (!filename && item.image_path) {
          filename = item.image_path.split('/').pop();
        }
        if (!filename && item.figure_name) {
          // assume png extension if not provided
          filename = `${item.figure_name}.png`;
        }
        return {
          name: filename,
          caption: item.caption || ''
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

  // Fetch blobs lazily for visible images
  useEffect(() => {
    const fetchBlobs = async () => {
      const subset = images.slice(0, visibleCount);
      const needFetch = subset.filter((img) => !img.blobUrl && !img.loading);

      await Promise.all(
        needFetch.map(async (img) => {
          img.loading = true;
          try {
            // Add cache busting for image files to ensure fresh content
            const cacheBuster = Date.now();
            const res = await fetch(`${API_BASE_URL}/notebooks/${notebookId}/files/${videoFileId}/images/${img.name}?t=${cacheBuster}`, { 
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
  }, [visibleCount, images, API_BASE_URL, notebookId, videoFileId]);

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
      const response = await apiService.extractVideoImages(notebookId, payload);
      setExtractResult(response);
      
      // Clear existing images and reload to ensure fresh data
      setImages([]);
      
      // Add a small delay to ensure backend has processed the new images
      setTimeout(() => {
        loadImages();
      }, 1000);
    } catch (error) {
      console.error('Image extraction failed:', error);
      setExtractError(error.message || 'Extraction failed');
    } finally {
      setIsExtracting(false);
    }
  };

  const SettingsModal = () => {
    if (!isSettingsOpen) return null;
    return (
      <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg w-96 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Settings className="h-5 w-5 text-gray-600" />
              <h3 className="text-lg font-semibold text-gray-900">Gallery Settings</h3>
            </div>
            <button onClick={() => setIsSettingsOpen(false)} className="text-gray-400 hover:text-gray-600">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Extraction Interval (s)</label>
              <input
                type="number"
                min={1}
                value={extractInterval}
                onChange={(e) => setExtractInterval(Number(e.target.value))}
                className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Min Words</label>
              <input
                type="number"
                min={0}
                value={minWords}
                onChange={(e) => setMinWords(Number(e.target.value))}
                className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          <div className="flex justify-end space-x-3 mt-6 pt-4 border-t">
            <Button variant="outline" onClick={() => setIsSettingsOpen(false)} className="text-gray-600 hover:text-gray-800">
              Cancel
            </Button>
            <Button onClick={() => setIsSettingsOpen(false)} className="bg-blue-600 hover:bg-blue-700 text-white">
              Save
            </Button>
          </div>
        </div>
      </div>
    );
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
          <button onClick={() => setIsSettingsOpen(true)} className="text-gray-500 hover:text-gray-700" title="Settings">
            <Settings className="h-5 w-5" />
          </button>
          <Button size="sm" onClick={handleExtract} disabled={isExtracting}>
            {isExtracting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-1" /> Extracting...
              </>
            ) : (
              'Extract Image'
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
        <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
          {images.slice(0, visibleCount).map((img, idx) => (
            <div
              key={idx}
              className="relative group border rounded overflow-hidden bg-white shadow-sm cursor-zoom-in"
              onClick={() => img.blobUrl && setSelectedImage(img.blobUrl)}
            >
              <img
                src={img.blobUrl || `${API_BASE_URL}/static/placeholder.png`}
                alt="thumbnail"
                loading="lazy"
                className="object-cover w-full h-32 group-hover:opacity-90 transition-opacity"/>
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40">
                <ZoomIn className="h-5 w-5 text-white" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Load more button for large galleries */}
      {visibleCount < images.length && (
        <div className="flex justify-center mt-4">
          <Button variant="outline" size="sm" onClick={handleLoadMore}>Load More</Button>
        </div>
      )}

      {/* Settings Modal */}
      <SettingsModal />

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