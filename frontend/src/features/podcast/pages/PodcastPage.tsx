import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import type { AppDispatch } from '@/app/store';
import { 
  fetchPodcasts, 
  fetchPodcast,
  selectFilteredPodcasts, 
  selectPodcastLoading, 
  selectPodcastError,
  selectViewMode,
  selectSortOrder,
  selectSearchTerm,
  selectFilters,
  selectPodcastStats,
  setSearchTerm,
  setSortOrder,
  setViewMode,
  setFilters,
  clearError
} from "@/features/podcast/podcastSlice";
import PodcastList from "@/features/podcast/components/PodcastList";
import PodcastFilters from "@/features/podcast/components/PodcastFilters";
import PodcastStats from "@/features/podcast/components/PodcastStats";
import PodcastDetail from "@/features/podcast/components/PodcastDetail";
import { Podcast } from "@/features/podcast/types/type";

const PodcastPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const podcasts = useSelector(selectFilteredPodcasts);
  const isLoading = useSelector(selectPodcastLoading);
  const error = useSelector(selectPodcastError);
  const viewMode = useSelector(selectViewMode);
  const sortOrder = useSelector(selectSortOrder);
  const searchTerm = useSelector(selectSearchTerm);
  const filters = useSelector(selectFilters);
  const stats = useSelector(selectPodcastStats);

  const [selectedPodcast, setSelectedPodcast] = useState<Podcast | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  useEffect(() => {
    dispatch(fetchPodcasts(filters));
  }, [dispatch, filters]);

  // Refresh podcasts when navigating back from detail view
  useEffect(() => {
    if (!showDetail && selectedPodcast) {
      // When returning from detail view, refresh the list to get latest data
      dispatch(fetchPodcasts(filters));
    }
  }, [showDetail, dispatch, filters]);

  useEffect(() => {
    if (error) {
      // Auto-clear error after 5 seconds
      const timer = setTimeout(() => {
        dispatch(clearError());
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, dispatch]);

  const handleSelectPodcast = async (podcast: Podcast) => {
    // If the podcast is completed, fetch the latest data to ensure we have the audio URL
    if (podcast.status === 'completed') {
      try {
        const updatedPodcast = await dispatch(fetchPodcast(podcast.id)).unwrap();
        setSelectedPodcast(updatedPodcast);
      } catch (error) {
        console.error('Failed to fetch podcast details:', error);
        // Still show the detail page with the data we have
        setSelectedPodcast(podcast);
      }
    } else {
      setSelectedPodcast(podcast);
    }
    setShowDetail(true);
  };

  const handleBackToList = () => {
    setShowDetail(false);
    setSelectedPodcast(null);
  };

  const handleSearchChange = (term: string) => {
    dispatch(setSearchTerm(term));
  };

  const handleSortChange = (order: 'recent' | 'oldest' | 'title') => {
    dispatch(setSortOrder(order));
  };

  const handleViewModeChange = (mode: 'grid' | 'list') => {
    dispatch(setViewMode(mode));
  };

  const handleFiltersChange = (newFilters: any) => {
    dispatch(setFilters(newFilters));
  };

  const handleDownloadPodcast = async (podcast: Podcast) => {
    if (!podcast.notebook_id) {
      console.error('No notebook ID found for podcast');
      return;
    }
    
    try {
      // Directly navigate to the download endpoint, let browser handle the download
      const downloadUrl = `/api/v1/notebooks/${podcast.notebook_id}/podcast-jobs/${podcast.id}/download/`;
      window.open(downloadUrl, '_blank');
    } catch (error) {
      console.error('Failed to download podcast:', error);
      // You could show a toast notification here
    }
  };

  const handleDeletePodcast = (podcast: Podcast) => {
    // This would be implemented with the delete action
    console.log('Deleting podcast:', podcast.id);
  };

  const handlePlayPodcast = (podcast: Podcast) => {
    // This would be implemented with audio playback
    console.log('Playing podcast:', podcast.id);
  };

  const handleEditPodcast = (podcast: Podcast) => {
    // This would navigate to edit mode
    console.log('Editing podcast:', podcast.id);
  };

  if (showDetail && selectedPodcast) {
    return (
      <PodcastDetail
        podcast={selectedPodcast}
        audio={selectedPodcast.audioUrl ? { audioUrl: selectedPodcast.audioUrl } : undefined}
        isLoading={isLoading}
        onDownload={handleDownloadPodcast}
        onDelete={handleDeletePodcast}
        onPlay={handlePlayPodcast}
        onEdit={handleEditPodcast}
        onBack={handleBackToList}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">AI Podcasts</h1>
          <p className="mt-2 text-gray-600">
            Generate and manage your AI-powered podcast discussions
          </p>
        </div>

        {/* Stats */}
        <div className="mb-6">
          <PodcastStats stats={stats} />
        </div>

        {/* Filters and Controls */}
        <div className="mb-6 bg-white rounded-lg shadow p-6">
          <PodcastFilters
            filters={filters}
            onFiltersChange={handleFiltersChange}
            stats={stats}
          />
          
          {/* Search and View Controls */}
          <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex-1 max-w-md">
              <input
                type="text"
                placeholder="Search podcasts..."
                value={searchTerm}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div className="flex items-center gap-4">
              {/* Sort Order */}
              <select
                value={sortOrder}
                onChange={(e) => handleSortChange(e.target.value as 'recent' | 'oldest' | 'title')}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="recent">Most Recent</option>
                <option value="oldest">Oldest First</option>
                <option value="title">Title A-Z</option>
              </select>

              {/* View Mode */}
              <div className="flex border border-gray-300 rounded-md">
                <button
                  onClick={() => handleViewModeChange('grid')}
                  className={`px-3 py-2 ${
                    viewMode === 'grid' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  } rounded-l-md`}
                >
                  Grid
                </button>
                <button
                  onClick={() => handleViewModeChange('list')}
                  className={`px-3 py-2 ${
                    viewMode === 'list' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  } rounded-r-md`}
                >
                  List
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Podcasts List */}
        <div className="bg-white rounded-lg shadow">
          <PodcastList
            podcasts={podcasts}
            isLoading={isLoading}
            onSelectPodcast={handleSelectPodcast}
            onDownloadPodcast={handleDownloadPodcast}
            onDeletePodcast={handleDeletePodcast}
            onPlayPodcast={handlePlayPodcast}
            onEditPodcast={handleEditPodcast}
            selectedPodcastId={selectedPodcast?.id}
            viewMode={viewMode}
          />
        </div>

        {/* Empty State */}
        {!isLoading && podcasts.length === 0 && (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No podcasts found</h3>
            <p className="mt-1 text-sm text-gray-500">
              {searchTerm || Object.keys(filters).length > 0 
                ? 'Try adjusting your search or filters.'
                : 'Get started by creating your first AI podcast discussion.'
              }
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PodcastPage; 