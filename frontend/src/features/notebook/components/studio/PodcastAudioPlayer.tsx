// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Simple podcast item with native audio player

import React, { useState, useEffect } from 'react';
import { 
  Download,
  Trash2,
  Loader2
} from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import { PodcastService } from "@/features/podcast/services/PodcastService";
import type { Podcast } from "@/features/podcast/types/type";

interface PodcastAudioPlayerProps {
  podcast: Podcast;
  onDownload: (podcast: Podcast) => void;
  onDelete: (podcast: Podcast) => void;
  notebookId?: string;
}

const PodcastAudioPlayer: React.FC<PodcastAudioPlayerProps> = ({
  podcast,
  onDownload,
  onDelete,
  notebookId
}) => {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [retryAttempts, setRetryAttempts] = useState(0);
  const [currentPodcast, setCurrentPodcast] = useState<Podcast>(podcast);

  const formatDate = (dateString?: string): string => {
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

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return '';
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Update current podcast when prop changes
  useEffect(() => {
    setCurrentPodcast(podcast);
    setRetryAttempts(0); // Reset retry attempts when podcast changes
  }, [podcast]);

  // Load audio URL with retry logic
  useEffect(() => {
    const loadAudio = async () => {
      setIsLoading(true);
      
      try {
        const podcastService = new PodcastService(notebookId);
        let url = podcastService.getAudioUrl(currentPodcast);
        
        // If no URL found, try to fetch fresh podcast data
        if (!url && currentPodcast.id) {
          try {
            console.log('No audio URL found, fetching fresh podcast data for:', currentPodcast.id);
            const freshPodcast = await podcastService.getPodcast(currentPodcast.id);
            url = podcastService.getAudioUrl(freshPodcast);
            
            if (url) {
              // Update the current podcast with fresh data
              setCurrentPodcast(freshPodcast);
            }
          } catch (fetchError) {
            console.error('Failed to fetch fresh podcast data:', fetchError);
            
            // Retry with exponential backoff if we haven't exceeded max attempts
            if (retryAttempts < 5) {
              const delay = Math.min(1000 * Math.pow(2, retryAttempts), 10000); // Max 10 seconds
              console.log(`Retrying audio load in ${delay}ms (attempt ${retryAttempts + 1}/5)`);
              setTimeout(() => {
                setRetryAttempts(prev => prev + 1);
              }, delay);
            }
          }
        }
        
        setAudioUrl(url);
      } catch (error) {
        console.error('Error getting audio URL:', error);
        setAudioUrl(null);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadAudio();
  }, [currentPodcast, notebookId, retryAttempts]);

  return (
    <div className="p-4 border border-gray-200 rounded-lg bg-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-gray-900 truncate">
            {currentPodcast.title || 'Untitled Panel Discussion'}
          </h4>
          <div className="flex items-center space-x-3 text-xs text-gray-500 mt-1">
            <span>{formatDate(currentPodcast.created_at)}</span>
            {(currentPodcast as any).file_size && (
              <>
                <span>•</span>
                <span>{formatFileSize((currentPodcast as any).file_size)}</span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDownload(currentPodcast)}
            className="h-8 w-8 p-0 text-gray-500 hover:text-gray-700"
            title="Download audio"
          >
            <Download className="h-4 w-4" />
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(currentPodcast)}
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
          <span className="text-sm">
            {retryAttempts > 0 ? `Retrying audio load... (${retryAttempts}/5)` : 'Loading audio...'}
          </span>
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
          {retryAttempts >= 5 ? 'Audio not available after retries' : 'Audio not available'}
        </div>
      )}
    </div>
  );
};

export default React.memo(PodcastAudioPlayer);