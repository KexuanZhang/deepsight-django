import React from "react";
import { Podcast, PodcastCardProps } from "../types/type";

export default function PodcastCard({ 
  podcast, 
  onSelect, 
  onDownload, 
  onDelete, 
  onPlay, 
  onEdit, 
  isSelected 
}: PodcastCardProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelect(podcast);
  };

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDownload(podcast);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(podcast);
  };

  const handlePlay = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onPlay) onPlay(podcast);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onEdit) onEdit(podcast);
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '';
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div 
      className={`border rounded-lg overflow-hidden shadow hover:shadow-lg transition-shadow cursor-pointer ${
        isSelected ? 'ring-2 ring-purple-500' : ''
      }`}
      onClick={handleClick}
    >
      {/* Cover Image or Placeholder */}
      <div className="h-40 bg-gradient-to-br from-purple-50 to-indigo-100 flex items-center justify-center">
        <svg className="h-16 w-16 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
      </div>
      
      <div className="p-4">
        {/* Title */}
        <h3 className="font-semibold mb-2 text-gray-900 line-clamp-2">
          {podcast.title || 'Untitled Podcast'}
        </h3>
        
        {/* Topic/Description */}
        <p className="text-gray-500 text-sm mb-2">
          {podcast.topic || podcast.description || 'No description'}
        </p>
        
        {/* Status Badge */}
        <div className="flex items-center justify-between mb-3">
          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
            podcast.status === 'completed' ? 'bg-green-100 text-green-800' :
            podcast.status === 'failed' ? 'bg-red-100 text-red-800' :
            podcast.status === 'generating' ? 'bg-blue-100 text-blue-800' :
            podcast.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {podcast.status}
          </span>
          
          <span className="text-xs text-gray-500">
            {new Date(podcast.created_at).toLocaleDateString()}
          </span>
        </div>
        
        {/* Duration */}
        {podcast.duration && (
          <div className="flex items-center text-sm text-gray-500 mb-3">
            <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {formatDuration(podcast.duration)}
          </div>
        )}
        
        {/* Actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {podcast.status === 'completed' && onPlay && (
              <button
                onClick={handlePlay}
                className="text-purple-600 hover:text-purple-800 text-sm font-medium"
                title="Play Podcast"
              >
                Play
              </button>
            )}
            
            {podcast.status === 'completed' && (
              <button
                onClick={handleDownload}
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                title="Download Podcast"
              >
                Download
              </button>
            )}
            
            {onEdit && (
              <button
                onClick={handleEdit}
                className="text-gray-600 hover:text-gray-800 text-sm"
                title="Edit Podcast"
              >
                Edit
              </button>
            )}
          </div>
          
          <button
            onClick={handleDelete}
            className="text-red-600 hover:text-red-800 text-sm"
            title="Delete Podcast"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
} 