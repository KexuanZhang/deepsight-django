import React, { useEffect, useState, useRef } from 'react';
import { Podcast, PodcastDetailProps, PodcastAudio } from '../types/type';
import { PodcastService } from '../services/PodcastService';

const PodcastDetail: React.FC<PodcastDetailProps> = ({
  podcast,
  audio,
  isLoading,
  onDownload,
  onDelete,
  onPlay,
  onEdit,
  onBack
}) => {
  const [podcastAudio, setPodcastAudio] = useState<PodcastAudio | null>(audio || null);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [refreshAttempts, setRefreshAttempts] = useState(0);
  const [currentPodcast, setCurrentPodcast] = useState<Podcast>(podcast);
  const pollingIntervalRef = useRef<number | null>(null);

  // Update current podcast when prop changes
  useEffect(() => {
    setCurrentPodcast(podcast);
  }, [podcast]);

  // Poll for podcast updates if status is generating or pending
  useEffect(() => {
    if (currentPodcast.status === 'generating' || currentPodcast.status === 'pending') {
      const pollForUpdates = async () => {
        try {
          const podcastService = new PodcastService();
          const updatedPodcast = await podcastService.getPodcast(currentPodcast.id);
          setCurrentPodcast(updatedPodcast);
          
          // If status changed to completed, clear the interval
          if (updatedPodcast.status === 'completed' || updatedPodcast.status === 'failed' || updatedPodcast.status === 'cancelled') {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }
          }
        } catch (error) {
          console.error('Failed to poll for podcast updates:', error);
        }
      };

      // Start polling every 2 seconds
      pollingIntervalRef.current = window.setInterval(pollForUpdates, 2000);

      // Cleanup on unmount or when status changes
      return () => {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      };
    }
  }, [currentPodcast.status, currentPodcast.id]);

  useEffect(() => {
    const loadAudio = async () => {
      if (currentPodcast.status === 'completed') {
        try {
          setIsLoadingAudio(true);
          const podcastService = new PodcastService();
          
          // First try to get audio URL from the podcast object itself
          let url = podcastService.getAudioUrl(currentPodcast);
          
          // If no URL from podcast object and we don't have audio data, fetch it
          if (!url && !audio) {
            try {
              const fetchedAudio = await podcastService.getPodcastAudio(currentPodcast.id);
              setPodcastAudio(fetchedAudio);
              url = podcastService.getAudioUrl(fetchedAudio as any);
            } catch (error) {
              console.error('Failed to load podcast audio:', error);
              // If fetching audio fails, retry a few times with delay
              if (refreshAttempts < 3) {
                setTimeout(() => {
                  setRefreshAttempts(prev => prev + 1);
                }, 2000); // Retry after 2 seconds
              }
            }
          } else if (audio) {
            // If audio is provided, use it
            setPodcastAudio(audio);
            url = podcastService.getAudioUrl(audio as any) || url;
          }
          
          setAudioUrl(url);
        } catch (error) {
          console.error('Error loading audio:', error);
        } finally {
          setIsLoadingAudio(false);
        }
      }
    };
    
    loadAudio();
  }, [currentPodcast, audio, refreshAttempts]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100';
      case 'failed': return 'text-red-600 bg-red-100';
      case 'generating': return 'text-blue-600 bg-blue-100';
      case 'pending': return 'text-yellow-600 bg-yellow-100';
      case 'cancelled': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={onBack}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  {currentPodcast.title || 'Untitled Podcast'}
                </h1>
                <p className="text-gray-600 mt-1">
                  Created on {formatDate(currentPodcast.created_at)}
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(currentPodcast.status)}`}>
                {currentPodcast.status}
              </span>
              
              {currentPodcast.status === 'completed' && onPlay && (
                <button
                  onClick={() => onPlay(currentPodcast)}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700"
                >
                  <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Play
                </button>
              )}
              
              {currentPodcast.status === 'completed' && (
                <button
                  onClick={() => onDownload(currentPodcast)}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                  <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download
                </button>
              )}
              
              {onEdit && (
                <button
                  onClick={() => onEdit(currentPodcast)}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  Edit
                </button>
              )}
              
              <button
                onClick={() => onDelete(currentPodcast)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
              >
                <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete
              </button>
            </div>
          </div>
        </div>

        {/* Podcast Metadata */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Podcast Details</h2>
          </div>
          <div className="px-6 py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-sm font-medium text-gray-500">Topic</h3>
                <p className="mt-1 text-sm text-gray-900">{currentPodcast.topic || "No topic specified"}</p>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500">Description</h3>
                <p className="mt-1 text-sm text-gray-900">{currentPodcast.description || "No description"}</p>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500">Duration</h3>
                <p className="mt-1 text-sm text-gray-900">
                  {currentPodcast.duration ? formatDuration(currentPodcast.duration) : 'Not available'}
                </p>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500">Created</h3>
                <p className="mt-1 text-sm text-gray-900">{formatDate(currentPodcast.created_at)}</p>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500">Last Updated</h3>
                <p className="mt-1 text-sm text-gray-900">{formatDate(currentPodcast.updated_at)}</p>
              </div>
            </div>
            
            {/* Expert Names */}
            {currentPodcast.expert_names && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-gray-500">Participants</h3>
                <div className="mt-2 grid grid-cols-1 md:grid-cols-3 gap-4">
                  {currentPodcast.expert_names.host && (
                    <div className="bg-gray-50 p-3 rounded-lg">
                      <p className="text-xs text-gray-500">Host</p>
                      <p className="text-sm font-medium text-gray-900">{currentPodcast.expert_names.host}</p>
                    </div>
                  )}
                  {currentPodcast.expert_names.expert1 && (
                    <div className="bg-gray-50 p-3 rounded-lg">
                      <p className="text-xs text-gray-500">Expert 1</p>
                      <p className="text-sm font-medium text-gray-900">{currentPodcast.expert_names.expert1}</p>
                    </div>
                  )}
                  {currentPodcast.expert_names.expert2 && (
                    <div className="bg-gray-50 p-3 rounded-lg">
                      <p className="text-xs text-gray-500">Expert 2</p>
                      <p className="text-sm font-medium text-gray-900">{currentPodcast.expert_names.expert2}</p>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {currentPodcast.progress && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-gray-500">Progress</h3>
                <p className="mt-1 text-sm text-gray-900">{currentPodcast.progress}</p>
              </div>
            )}
            
            {currentPodcast.error_message && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-red-500">Error</h3>
                <p className="mt-1 text-sm text-red-600">{currentPodcast.error_message}</p>
              </div>
            )}
          </div>
        </div>

        {/* Audio Player */}
        {currentPodcast.status === 'completed' && podcastAudio && (
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Audio Player</h2>
            </div>
            <div className="px-6 py-4">
              {isLoadingAudio ? (
                <div className="animate-pulse space-y-4">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
              ) : audioUrl ? (
                <div className="space-y-4">
                  <audio 
                    controls 
                    className="w-full"
                    src={audioUrl}
                  >
                    Your browser does not support the audio element.
                  </audio>
                  
                  {podcastAudio.duration && (
                    <div className="flex items-center text-sm text-gray-500">
                      <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Duration: {formatDuration(podcastAudio.duration)}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-4 text-gray-500">
                  Audio not available
                </div>
              )}
            </div>
          </div>
        )}

        {/* Conversation Text */}
        {currentPodcast.conversation_text && (
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Conversation Transcript</h2>
            </div>
            <div className="px-6 py-4">
              <div className="prose max-w-none">
                <pre className="whitespace-pre-wrap text-sm text-gray-900 bg-gray-50 p-4 rounded-lg">
                  {currentPodcast.conversation_text}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PodcastDetail; 