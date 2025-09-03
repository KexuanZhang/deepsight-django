// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on displaying podcast list

import React from 'react';
import { 
  Play,
  ChevronDown, 
  ChevronUp
} from 'lucide-react';
import { COLORS } from '@/features/notebook/config/uiConfig';
import PodcastAudioPlayer from './PodcastAudioPlayer';
import { Podcast } from '@/features/podcast/types/type';


interface PodcastListSectionProps {
  podcasts: Podcast[];
  loading: boolean;
  error?: string;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onDownloadPodcast: (podcast: Podcast) => void;
  onDeletePodcast: (podcast: Podcast) => void;
  notebookId?: string;
}

// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Focused props interface for podcast list display
const PodcastListSection: React.FC<PodcastListSectionProps> = ({
  podcasts,
  loading,
  error,
  isCollapsed,
  onToggleCollapse,
  onDownloadPodcast,
  onDeletePodcast,
  notebookId
}) => {
  const podcastCount = podcasts.length;

  return (
    <div className="bg-transparent">
      {/* ====== SINGLE RESPONSIBILITY: Header rendering ====== */}
      <div 
        className={`px-6 py-5 ${COLORS.panels.commonBackground}/80 backdrop-blur-sm cursor-pointer hover:${COLORS.panels.commonBackground}/90 transition-all duration-200 border-b border-gray-100/50`}
        onClick={onToggleCollapse}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-red-500 to-red-600 rounded-lg flex items-center justify-center shadow-sm">
              <Play className="h-4 w-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">
                Panel Discussions
                {podcastCount > 0 && (
                  <span className="ml-2 text-sm font-normal text-gray-600">
                    ({podcastCount})
                  </span>
                )}
              </h3>
              <p className="text-xs text-gray-600">Generated panel discussions</p>
            </div>
          </div>
          {isCollapsed ? 
            <ChevronDown className="h-4 w-4 text-gray-500" /> : 
            <ChevronUp className="h-4 w-4 text-gray-500" />
          }
        </div>
      </div>

      {/* ====== SINGLE RESPONSIBILITY: Content rendering ====== */}
      {!isCollapsed && (
        <div className={`px-6 py-5 ${COLORS.panels.commonBackground}/50 backdrop-blur-sm`}>
          {loading && (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-600 mx-auto"></div>
              <p className="text-sm text-gray-500 mt-2">Loading podcasts...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {!loading && !error && podcastCount === 0 && (
            <div className="text-center py-8">
              <Play className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-gray-900 mb-2">No panel discussions yet</h4>
              <p className="text-sm text-gray-500">
                Generate your first panel discussion using the form above.
              </p>
            </div>
          )}

          {!loading && !error && podcastCount > 0 && (
            <div className="space-y-3">
              {podcasts.map((podcast, index) => (
                <PodcastAudioPlayer
                  key={podcast.id || podcast.job_id || `podcast-${index}`}
                  podcast={podcast}
                  onDownload={onDownloadPodcast}
                  onDelete={onDeletePodcast}
                  notebookId={notebookId}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default React.memo(PodcastListSection); // Performance optimization