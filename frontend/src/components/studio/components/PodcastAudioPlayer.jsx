// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Simple podcast item with native audio player

import React, { useState, useEffect } from 'react';
import { 
  Download,
  Trash2,
  Loader2
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const PodcastAudioPlayer = ({
  podcast,
  onDownload,
  onDelete,
  studioService
}) => {
  const [audioUrl, setAudioUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const formatDate = (dateString) => {
    if (!dateString) return '';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return '';
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Load audio URL
  useEffect(() => {
    const loadAudio = async () => {
      setIsLoading(true);
      try {
        const podcastId = podcast.id || podcast.job_id;
        const url = await studioService.loadAudio(podcastId);
        setAudioUrl(url);
      } catch (error) {
        console.error('Failed to load audio:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadAudio();

    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, []);

  return (
    <div className="p-4 border border-gray-200 rounded-lg bg-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-gray-900 truncate">
            {podcast.title || 'Untitled Panel Discussion'}
          </h4>
          <div className="flex items-center space-x-3 text-xs text-gray-500 mt-1">
            <span>{formatDate(podcast.created_at)}</span>
            {podcast.file_size && (
              <>
                <span>•</span>
                <span>{formatFileSize(podcast.file_size)}</span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDownload(podcast)}
            className="h-8 w-8 p-0 text-gray-500 hover:text-gray-700"
            title="Download audio"
          >
            <Download className="h-4 w-4" />
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(podcast)}
            className="h-8 w-8 p-0 text-gray-500 hover:text-red-600"
            title="Delete podcast"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Audio Player */}
      {isLoading ? (
        <div className="flex items-center justify-center py-2 text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
          <span className="text-sm">Loading audio...</span>
        </div>
      ) : audioUrl ? (
        <audio 
          controls 
          className="w-full"
          preload="metadata"
          style={{ height: '40px' }}
        >
          <source src={audioUrl} type="audio/mpeg" />
          Your browser does not support the audio element.
        </audio>
      ) : (
        <div className="text-center py-2 text-gray-500 text-sm">
          Audio not available
        </div>
      )}
    </div>
  );
};

export default React.memo(PodcastAudioPlayer);