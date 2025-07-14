"""
Storage adapter for MinIO file storage.
Provides a simplified interface for MinIO operations only.
"""

import logging
from typing import Dict, Any, Optional, List

from django.conf import settings

# Import MinIO storage service only
try:
    from .minio_file_storage import MinIOFileStorageService
except ImportError:
    MinIOFileStorageService = None


class StorageAdapter:
    """
    Adapter that provides MinIO storage operations only.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.storage_adapter")
        
        # Initialize MinIO storage service
        if MinIOFileStorageService is None:
            self.logger.error("MinIOFileStorageService not available")
            raise ImportError("MinIO storage backend not available")
        self.storage_service = MinIOFileStorageService()
        self.logger.info("Initialized MinIO storage backend")
    
    def is_minio_backend(self) -> bool:
        """Check if currently using MinIO backend."""
        return True  # Always MinIO now
    
    def store_processed_file(
        self,
        content: str,
        metadata: Dict[str, Any],
        processing_result: Dict[str, Any],
        user_id: int,
        notebook_id: int,
        source_id: Optional[int] = None,
        original_file_path: Optional[str] = None,
    ) -> str:
        """Store processed file content in user's knowledge base."""
        return self.storage_service.store_processed_file(
            content=content,
            metadata=metadata,
            processing_result=processing_result,
            user_id=user_id,
            notebook_id=notebook_id,
            source_id=source_id,
            original_file_path=original_file_path,
        )
    
    def get_file_content(self, file_id: str, user_id: int = None) -> Optional[str]:
        """Retrieve file content by knowledge base item ID."""
        return self.storage_service.get_file_content(file_id, user_id)
    
    def get_file_url(self, file_id: str, user_id: int = None, expires: int = 3600) -> Optional[str]:
        """Get URL for file access."""
        return self.storage_service.get_file_url(file_id, user_id, expires)
    
    def get_original_file_url(self, file_id: str, user_id: int = None, expires: int = 3600) -> Optional[str]:
        """Get URL for original file access."""
        return self.storage_service.get_original_file_url(file_id, user_id, expires)
    
    def get_user_knowledge_base(
        self, user_id: int, content_type: str = None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all knowledge base items for a user."""
        return self.storage_service.get_user_knowledge_base(user_id, content_type, limit, offset)
    
    def link_knowledge_item_to_notebook(
        self, kb_item_id: str, notebook_id: int, user_id: int, notes: str = ""
    ) -> bool:
        """Link an existing knowledge base item to a notebook."""
        return self.storage_service.link_knowledge_item_to_notebook(
            kb_item_id, notebook_id, user_id, notes
        )
    
    def delete_knowledge_base_item(self, kb_item_id: str, user_id: int) -> bool:
        """Delete a knowledge base item and its files."""
        return self.storage_service.delete_knowledge_base_item(kb_item_id, user_id)
    
    def unlink_knowledge_item_from_notebook(
        self, kb_item_id: str, notebook_id: int, user_id: int
    ) -> bool:
        """Remove a knowledge item link from a specific notebook."""
        return self.storage_service.unlink_knowledge_item_from_notebook(
            kb_item_id, notebook_id, user_id
        )
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about the current storage backend."""
        info = {
            'backend': 'minio',
            'service_class': self.storage_service.__class__.__name__,
            'is_minio': True,
        }
        
        # Add MinIO-specific information
        try:
            minio_config = getattr(settings, 'MINIO_SETTINGS', {})
            info['minio_endpoint'] = minio_config.get('ENDPOINT', 'not configured')
            info['minio_bucket'] = minio_config.get('BUCKET_NAME', 'not configured')
            info['minio_secure'] = minio_config.get('SECURE', False)
        except Exception as e:
            info['minio_error'] = str(e)
        
        return info
    
    def _generate_knowledge_base_paths(
        self, user_id: int, original_filename: str, kb_item_id: str
    ) -> Dict[str, str]:
        """
        Generate organized file paths for knowledge base storage.
        Delegates to the underlying storage service.
        """
        if hasattr(self.storage_service, '_generate_knowledge_base_paths'):
            return self.storage_service._generate_knowledge_base_paths(
                user_id, original_filename, kb_item_id
            )
        else:
            # Fallback implementation for MinIO storage
            from datetime import datetime
            current_date = datetime.now()
            year_month = current_date.strftime("%Y-%m")
            
            # Clean the filename
            cleaned_filename = original_filename.replace(" ", "_").replace("/", "_")
            
            base_dir = f"Users/u_{user_id}/knowledge_base_item/{year_month}/f_{kb_item_id}"
            content_dir = f"{base_dir}/content"
            images_dir = f"{base_dir}/images"
            
            return {
                'base_dir': base_dir,
                'original_file_path': f"{base_dir}/{cleaned_filename}",
                'content_dir': content_dir,
                'content_file_path': f"{content_dir}/extracted_content.md",
                'images_dir': images_dir,
            }


# Global singleton instance
_storage_adapter = None

def get_storage_adapter() -> StorageAdapter:
    """Get the global storage adapter instance."""
    global _storage_adapter
    if _storage_adapter is None:
        _storage_adapter = StorageAdapter()
    return _storage_adapter