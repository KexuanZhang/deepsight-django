import React from 'react';
import { Podcast, PodcastListProps } from '../types/type';
import PodcastCard from './PodcastCard';

const PodcastList: React.FC<PodcastListProps> = ({
  podcasts,
  isLoading,
  onSelectPodcast,
  onDownloadPodcast,
  onDeletePodcast,
  onPlayPodcast,
  onEditPodcast,
  selectedPodcastId,
  viewMode
}) => {
  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-gray-200 rounded"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (viewMode === 'grid') {
    return (
      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {podcasts.map((podcast) => (
            <PodcastCard
              key={podcast.id}
              podcast={podcast}
              onSelect={onSelectPodcast}
              onDownload={onDownloadPodcast}
              onDelete={onDeletePodcast}
              onPlay={onPlayPodcast}
              onEdit={onEditPodcast}
              isSelected={selectedPodcastId === podcast.id}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-hidden">
      <div className="min-w-full divide-y divide-gray-200">
        {podcasts.map((podcast) => (
          <div
            key={podcast.id}
            className={`p-6 hover:bg-gray-50 cursor-pointer ${
              selectedPodcastId === podcast.id ? 'bg-blue-50' : ''
            }`}
            onClick={() => onSelectPodcast(podcast)}
          >
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    <div className="h-10 w-10 bg-purple-100 rounded-lg flex items-center justify-center">
                      <svg className="h-6 w-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {podcast.title || 'Untitled Podcast'}
                    </p>
                    <p className="text-sm text-gray-500 truncate">
                      {podcast.topic || podcast.description || 'No description'}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                {/* Status Badge */}
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  podcast.status === 'completed' ? 'bg-green-100 text-green-800' :
                  podcast.status === 'failed' ? 'bg-red-100 text-red-800' :
                  podcast.status === 'generating' ? 'bg-blue-100 text-blue-800' :
                  podcast.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {podcast.status}
                </span>
                
                {/* Duration */}
                {podcast.duration && (
                  <span className="text-sm text-gray-500">
                    {Math.floor(podcast.duration / 60)}:{(podcast.duration % 60).toString().padStart(2, '0')}
                  </span>
                )}
                
                {/* Date */}
                <span className="text-sm text-gray-500">
                  {new Date(podcast.created_at).toLocaleDateString()}
                </span>
                
                {/* Actions */}
                <div className="flex items-center space-x-1">
                  {podcast.status === 'completed' && onPlayPodcast && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onPlayPodcast(podcast);
                      }}
                      className="p-1 text-gray-400 hover:text-green-600"
                      title="Play"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </button>
                  )}
                  
                  {podcast.status === 'completed' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDownloadPodcast(podcast);
                      }}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Download"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </button>
                  )}
                  
                  {onEditPodcast && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onEditPodcast(podcast);
                      }}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Edit"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                  )}
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeletePodcast(podcast);
                    }}
                    className="p-1 text-gray-400 hover:text-red-600"
                    title="Delete"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
            
            {/* Progress for generating podcasts */}
            {podcast.status === 'generating' && podcast.progress && (
              <div className="mt-3">
                <div className="flex items-center space-x-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div className="bg-purple-600 h-2 rounded-full animate-pulse" style={{ width: "60%" }}></div>
                  </div>
                  <span className="text-xs text-gray-500">{podcast.progress}</span>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default PodcastList; 