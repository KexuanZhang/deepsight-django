import React, { useState } from 'react';
import { Button } from '@/common/components/ui/button';
import { Settings, Image as ImageIcon, Loader2, X } from 'lucide-react';
import apiService from '@/common/utils/api';

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

      {/* Placeholder content or extraction result info */}
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

      <p className="text-xs text-gray-500">Images will appear here after extraction.</p>

      {/* Settings Modal */}
      <SettingsModal />
    </div>
  );
};

export default GallerySection; 