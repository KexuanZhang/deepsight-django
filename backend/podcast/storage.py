"""
Podcast storage service following the same pattern as reports storage.

This service handles audio file storage operations for podcasts,
providing a clean interface between the podcast service and MinIO storage.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PodcastStorageService:
    """Service responsible for managing podcast audio file storage operations"""
    
    def __init__(self):
        """Initialize the podcast storage service"""
        # Storage is handled by MinIO backend - no local setup needed
        pass
    
    def store_podcast_audio(self, audio_file_path: Path, user_id: int, podcast_id: str, notebook_id: Optional[int] = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Store generated podcast audio file and return storage information.
        
        Args:
            audio_file_path: Path to the generated audio file
            user_id: User ID for the podcast
            podcast_id: Podcast ID for the podcast
            notebook_id: Notebook ID (optional)
            metadata: Optional metadata about the podcast
            
        Returns:
            Dictionary with storage information including object key and metadata
        """
        try:
            # Get MinIO backend
            backend = self._get_minio_backend()
            
            # Read audio file content
            audio_content = self._read_audio_file(audio_file_path)
            
            # Generate object key for podcast storage following reports pattern
            object_key = self._generate_audio_object_key(user_id, podcast_id, notebook_id)
            
            # Store in MinIO
            storage_success = backend.store_file(
                object_key=object_key,
                file_content=audio_content,
                content_type="audio/mpeg"
            )
            
            # Clean up temporary file and directory
            self._cleanup_temporary_files(audio_file_path)
            
            if storage_success:
                logger.info(f"Successfully stored podcast audio: {object_key}")
                
                # Get file metadata
                file_metadata = self._get_audio_file_metadata(audio_content, object_key, metadata)
                
                return {
                    "audio_object_key": object_key,
                    "file_metadata": file_metadata,
                    "storage_success": True,
                    "error": None
                }
            else:
                logger.error(f"Failed to store podcast audio in MinIO: {object_key}")
                return {
                    "audio_object_key": None,
                    "file_metadata": {},
                    "storage_success": False,
                    "error": f"MinIO storage failed for {object_key}"
                }
                
        except Exception as e:
            logger.error(f"Error storing podcast audio file {audio_file_path}: {e}")
            return {
                "audio_object_key": None,
                "file_metadata": {},
                "storage_success": False,
                "error": str(e)
            }
    
    def get_audio_url(self, object_key: str, expires: int = 3600) -> Optional[str]:
        """
        Get pre-signed URL for audio access.
        
        Args:
            object_key: MinIO object key for the audio file
            expires: URL expiration time in seconds
            
        Returns:
            Pre-signed URL string or None if failed
        """
        try:
            backend = self._get_minio_backend()
            return backend.get_presigned_url(object_key, expires)
        except Exception as e:
            logger.error(f"Error getting audio URL for {object_key}: {e}")
            return None
    
    def delete_podcast_audio(self, object_key: str) -> bool:
        """
        Delete podcast audio file from storage.
        
        Args:
            object_key: MinIO object key for the audio file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            backend = self._get_minio_backend()
            success = backend.delete_file(object_key)
            
            if success:
                logger.info(f"Successfully deleted podcast audio: {object_key}")
            else:
                logger.error(f"Failed to delete podcast audio: {object_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting podcast audio {object_key}: {e}")
            return False
    
    def validate_storage_setup(self) -> bool:
        """
        Validate that MinIO storage is properly configured.
        
        Returns:
            True if storage is properly set up, False otherwise
        """
        try:
            backend = self._get_minio_backend()
            # Basic validation - try to get backend instance
            return backend is not None
        except Exception as e:
            logger.error(f"Storage validation failed: {e}")
            return False
    
    def _get_minio_backend(self):
        """Get MinIO backend instance"""
        from notebooks.utils.storage import get_minio_backend
        return get_minio_backend()
    
    def _read_audio_file(self, audio_file_path: Path) -> bytes:
        """
        Read audio file content.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Audio file content as bytes
            
        Raises:
            Exception: If file cannot be read
        """
        try:
            with open(audio_file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Failed to read audio file {audio_file_path}: {e}")
    
    def _generate_audio_object_key(self, user_id: int, podcast_id: str, notebook_id: Optional[int] = None) -> str:
        """
        Generate unique object key for audio file storage following reports pattern.
        
        Args:
            user_id: User ID for the podcast
            podcast_id: Podcast ID for the podcast
            notebook_id: Notebook ID (optional)
            
        Returns:
            MinIO object key string
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4()).replace('-', '')[:8]
        filename = f"podcast_{timestamp}_{unique_id}.mp3"
        
        # Follow reports pattern but use 'podcast' instead of 'report': 
        # {user_id}/notebook/{notebook_id}/podcast/{podcast_id}/filename
        notebook_path = f"notebook/{notebook_id}" if notebook_id else "notebook/standalone"
        return f"{user_id}/{notebook_path}/podcast/{podcast_id}/{filename}"
    
    def _get_audio_file_metadata(self, audio_content: bytes, object_key: str, 
                                metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate metadata for stored audio file.
        
        Args:
            audio_content: Audio file content bytes
            object_key: MinIO object key
            metadata: Additional metadata from podcast generation
            
        Returns:
            File metadata dictionary
        """
        file_metadata = {
            "filename": object_key.split('/')[-1],
            "object_key": object_key,
            "file_size": len(audio_content),
            "content_type": "audio/mpeg",
            "format": "mp3",
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Add additional metadata if provided
        if metadata:
            file_metadata.update({
                "podcast_metadata": metadata,
                "total_turns": metadata.get("total_turns"),
                "participants": metadata.get("participants"),
                "topic": metadata.get("topic")
            })
        
        return file_metadata
    
    def _cleanup_temporary_files(self, audio_file_path: Path):
        """
        Clean up temporary directory and files.
        
        Args:
            audio_file_path: Path to the temporary audio file
        """
        try:
            import shutil
            
            # Clean up temporary directory (parent of the audio file)
            temp_dir = audio_file_path.parent
            
            # Only remove if it looks like a temporary directory
            if temp_dir.name.startswith('tmp') or 'temp' in str(temp_dir).lower():
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            else:
                # Just remove the audio file if directory doesn't look temporary
                audio_file_path.unlink()
                logger.debug(f"Cleaned up temporary audio file: {audio_file_path}")
                
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up temporary files {audio_file_path}: {cleanup_error}")
    
    def get_file_info(self, object_key: str) -> Dict[str, Any]:
        """
        Get information about a specific audio file.
        
        Args:
            object_key: MinIO object key for the audio file
            
        Returns:
            Dictionary with file information
        """
        try:
            backend = self._get_minio_backend()
            
            # Try to get file metadata from MinIO
            # Note: This would need to be implemented in the MinIO backend
            # For now, return basic info based on object key
            
            return {
                "object_key": object_key,
                "filename": object_key.split('/')[-1],
                "content_type": "audio/mpeg",
                "format": "mp3",
                "exists": True  # Assume exists for now
            }
            
        except Exception as e:
            logger.error(f"Error getting file info for {object_key}: {e}")
            return {
                "object_key": object_key,
                "exists": False,
                "error": str(e)
            }