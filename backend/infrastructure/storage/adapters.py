"""
Storage adapter utilities and factory functions.
"""

import logging
from django.conf import settings
from typing import Optional
from .base import StorageInterface
from .minio import MinIOStorage


logger = logging.getLogger(__name__)


def get_storage_backend() -> StorageInterface:
    """
    Get the configured storage backend instance.
    
    Returns:
        Configured storage backend implementing StorageInterface
        
    Raises:
        ValueError: If no valid storage backend is configured
    """
    storage_type = getattr(settings, 'DEFAULT_STORAGE_BACKEND', 'minio')
    
    if storage_type.lower() == 'minio':
        return MinIOStorage()
    else:
        raise ValueError(f"Unsupported storage backend: {storage_type}")


class StorageAdapter:
    """
    Adapter class that provides a simplified interface to storage operations.
    
    This class acts as a facade over the storage backend, providing
    commonly needed operations with sensible defaults.
    """
    
    def __init__(self, storage_backend: Optional[StorageInterface] = None):
        self.storage = storage_backend or get_storage_backend()
        self.logger = logging.getLogger(__name__)
    
    def save_user_file(self, user_id: str, file_content: bytes, 
                      filename: str, content_type: str = None) -> str:
        """
        Save a file for a specific user.
        
        Args:
            user_id: ID of the user who owns the file
            file_content: Binary content of the file
            filename: Original filename
            content_type: MIME type of the file
            
        Returns:
            Object key of the saved file
        """
        from core.utils import generate_unique_filename, get_content_type
        
        object_key = generate_unique_filename(filename, user_id)
        
        if not content_type:
            content_type = get_content_type(filename)
        
        from django.utils import timezone
        
        metadata = {
            'original_filename': filename,
            'user_id': user_id,
            'uploaded_at': str(timezone.now())
        }
        
        try:
            self.storage.save_file(file_content, object_key, content_type, metadata)
            self.logger.info(f"User file saved: {object_key}")
            return object_key
        except Exception as e:
            self.logger.error(f"Failed to save user file {filename}: {e}")
            raise
    
    def get_file_content(self, object_key: str, user_id: str = None) -> Optional[bytes]:
        """
        Get file content with optional user verification.
        
        Args:
            object_key: Key of the file to retrieve
            user_id: Optional user ID for access verification
            
        Returns:
            File content as bytes, or None if not found/unauthorized
        """
        try:
            # If user_id is provided, verify the file belongs to the user
            if user_id and not object_key.startswith(f'users/{user_id}/'):
                self.logger.warning(f"Access denied: user {user_id} attempted to access {object_key}")
                return None
            
            return self.storage.get_file(object_key)
        except Exception as e:
            self.logger.error(f"Failed to get file content {object_key}: {e}")
            return None
    
    def get_file_url(self, object_key: str, expires: int = 3600) -> Optional[str]:
        """
        Get a pre-signed URL for file access.
        
        Args:
            object_key: Key of the file
            expires: URL expiration time in seconds
            
        Returns:
            Pre-signed URL or None if failed
        """
        try:
            return self.storage.get_file_url(object_key, expires)
        except Exception as e:
            self.logger.error(f"Failed to generate URL for {object_key}: {e}")
            return None
    
    def delete_user_file(self, object_key: str, user_id: str) -> bool:
        """
        Delete a file belonging to a specific user.
        
        Args:
            object_key: Key of the file to delete
            user_id: ID of the user who owns the file
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Verify the file belongs to the user
            if not object_key.startswith(f'users/{user_id}/'):
                self.logger.warning(f"Delete denied: user {user_id} attempted to delete {object_key}")
                return False
            
            return self.storage.delete_file(object_key)
        except Exception as e:
            self.logger.error(f"Failed to delete file {object_key}: {e}")
            return False
    
    def cleanup_orphaned_files(self, active_object_keys: list) -> int:
        """
        Clean up files that are no longer referenced in the database.
        
        Args:
            active_object_keys: List of object keys that should be kept
            
        Returns:
            Number of files cleaned up
        """
        try:
            all_files = self.storage.list_files(limit=10000)  # Adjust limit as needed
            active_keys_set = set(active_object_keys)
            
            deleted_count = 0
            for file_key in all_files:
                if file_key not in active_keys_set:
                    if self.storage.delete_file(file_key):
                        deleted_count += 1
                        self.logger.info(f"Cleaned up orphaned file: {file_key}")
            
            self.logger.info(f"Cleanup completed: {deleted_count} orphaned files removed")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup orphaned files: {e}")
            return 0


# Global storage adapter instance
_storage_adapter_instance = None


def get_storage_adapter() -> StorageAdapter:
    """
    Get a singleton instance of the storage adapter.
    
    Returns:
        StorageAdapter instance
    """
    global _storage_adapter_instance
    
    if _storage_adapter_instance is None:
        _storage_adapter_instance = StorageAdapter()
    
    return _storage_adapter_instance