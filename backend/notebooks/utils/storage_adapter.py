"""
Storage adapter module that provides unified access to storage services.
"""

import logging
from typing import Optional

from .storage import StorageAdapter as BaseStorageAdapter, FileStorageService


logger = logging.getLogger(__name__)


def get_storage_adapter():
    """Get the configured storage adapter instance."""
    return StorageAdapter()


class StorageAdapter:
    """
    Enhanced storage adapter that provides all methods expected by views.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.storage_adapter")
        self.storage_service = EnhancedFileStorageService()
    
    @property
    def file_storage(self):
        """Compatibility property for legacy code."""
        return self.storage_service
    
    def is_minio_backend(self) -> bool:
        """Check if currently using MinIO backend."""
        return True  # Always MinIO now
    
    def store_processed_file(self, *args, **kwargs):
        """Store processed file using the service."""
        return self.storage_service.store_processed_file(*args, **kwargs)
    
    def get_file_content(self, *args, **kwargs):
        """Get file content using the service."""
        return self.storage_service.get_file_content(*args, **kwargs)
    
    def get_file_url(self, *args, **kwargs):
        """Get file URL using the service."""
        return self.storage_service.get_file_url(*args, **kwargs)
    
    def get_original_file_url(self, file_id: str, user_id: int) -> Optional[str]:
        """Get original file URL."""
        return self.storage_service.get_file_url(file_id, user_id, file_type='original')
    
    def delete_file(self, *args, **kwargs):
        """Delete file using the service."""
        return self.storage_service.delete_file(*args, **kwargs)
    
    def get_user_knowledge_base(self, *args, **kwargs):
        """Get user knowledge base using the service."""
        return self.storage_service.get_user_knowledge_base(*args, **kwargs)
    
    def link_knowledge_item_to_notebook(self, *args, **kwargs):
        """Link knowledge item to notebook using the service."""
        return self.storage_service.link_knowledge_item_to_notebook(*args, **kwargs)
    
    def delete_knowledge_base_item(self, *args, **kwargs):
        """Delete knowledge base item using the service."""
        return self.storage_service.delete_knowledge_base_item(*args, **kwargs)
    
    def unlink_knowledge_item_from_notebook(self, *args, **kwargs):
        """Unlink knowledge item from notebook using the service."""
        return self.storage_service.unlink_knowledge_item_from_notebook(*args, **kwargs)
    
    def get_notebook_knowledge_items(self, *args, **kwargs):
        """Get knowledge items for a specific notebook."""
        return self.storage_service.get_notebook_knowledge_items(*args, **kwargs)
    
    def delete_notebook_knowledge_item(self, *args, **kwargs):
        """Delete a knowledge item from a specific notebook."""
        return self.storage_service.delete_notebook_knowledge_item(*args, **kwargs)


class EnhancedFileStorageService(FileStorageService):
    """
    Enhanced file storage service with additional methods needed by views.
    """
    
    # Content retrieval methods moved to KnowledgeBaseItemManager.
    # Use KnowledgeBaseItem.objects.get_content() and .get_content_with_minio_urls() instead. 