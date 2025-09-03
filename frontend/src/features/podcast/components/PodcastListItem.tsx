import React, { useState } from 'react';
import { Podcast } from '../types/type';

interface PodcastListItemProps {
  podcast: Podcast;
  onSelect: (podcast: Podcast) => void;
}

const PodcastListItem: React.FC<PodcastListItemProps> = ({ podcast, onSelect }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleClick = () => {
    if (isExpanded) {
      setIsExpanded(false);
    } else {
      setIsExpanded(true);
    }
  };

  // Generate preview text from description or topic
  const getPreviewText = () => {
    if (podcast.description) {
      return podcast.description.length > 100 
        ? podcast.description.substring(0, 100) + '...' 
        : podcast.description;
    }
    if (podcast.topic) {
      return podcast.topic.length > 100 
        ? podcast.topic.substring(0, 100) + '...' 
        : podcast.topic;
    }
    return '1. 什么是平衡短期和长期回报的最优策略? 在许多实际应用中,决策者需要同时考虑短期和长...';
  };

  return (
    <div className="mb-4">
      {/* Main item */}
      <div 
        className="flex items-start space-x-3 cursor-pointer hover:bg-gray-50 p-2 rounded transition-colors"
        onClick={handleClick}
      >
        {/* Yellow square icon with three lines */}
        <div className="w-8 h-8 bg-yellow-400 rounded flex items-center justify-center flex-shrink-0">
          <div className="flex flex-col space-y-0.5">
            <div className="w-3 h-0.5 bg-white rounded"></div>
            <div className="w-3 h-0.5 bg-white rounded"></div>
            <div className="w-3 h-0.5 bg-white rounded"></div>
          </div>
        </div>
        
        <div className="flex-1 min-w-0">
          {/* Title */}
          <h3 className="font-bold text-gray-900 mb-2">
            {podcast.title || '新兴人工智能研究进展:从对齐到场景理解'}
          </h3>
          
          {/* Preview text */}
          <p className="text-sm text-gray-700 leading-relaxed">
            {getPreviewText()}
          </p>
        </div>
      </div>

      {/* Expanded audio player */}
      {isExpanded && podcast.status === 'completed' && (
        <div className="mt-3 ml-11 p-4 bg-gray-50 rounded-lg">
          <audio 
            controls 
            className="w-full"
            src={podcast.audioUrl || podcast.audio_file}
          >
            Your browser does not support the audio element.
          </audio>
          {podcast.duration && (
            <p className="text-xs text-gray-500 mt-2">
              Duration: {Math.floor(podcast.duration / 60)}:{(podcast.duration % 60).toString().padStart(2, '0')}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default PodcastListItem; 