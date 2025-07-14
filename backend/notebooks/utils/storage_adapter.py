"""
Storage adapter that provides backward compatibility between local file storage and MinIO.
Automatically routes operations to the appropriate storage backend based on configuration.
"""

import logging
from typing import Dict, Any, Optional, List

from django.conf import settings

# Import both storage services
try:
    from .file_storage import FileStorageService
except ImportError:
    FileStorageService = None

try:
    from .minio_file_storage import MinIOFileStorageService
except ImportError:
    MinIOFileStorageService = None


class StorageAdapter:
    """
    Adapter that routes storage operations to the appropriate backend.
    Provides seamless transition from local file storage to MinIO.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.storage_adapter")
        
        # Determine storage backend from settings
        self.storage_backend = getattr(settings, 'STORAGE_BACKEND', 'local')
        
        # Initialize the appropriate storage service
        if self.storage_backend == 'minio':
            if MinIOFileStorageService is None:
                self.logger.error("MinIO storage backend requested but MinIOFileStorageService not available")
                raise ImportError("MinIO storage backend not available")
            self.storage_service = MinIOFileStorageService()
            self.logger.info("Initialized MinIO storage backend")
        else:
            if FileStorageService is None:
                self.logger.error("Local storage backend requested but FileStorageService not available")
                raise ImportError("Local storage backend not available")
            # Use the singleton instance from file_storage.py
            from .file_storage import file_storage_service
            self.storage_service = file_storage_service
            self.logger.info("Initialized local file storage backend")
    
    def is_minio_backend(self) -> bool:
        """Check if currently using MinIO backend."""
        return self.storage_backend == 'minio'
    
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
        if self.is_minio_backend():
            return self.storage_service.get_file_url(file_id, user_id, expires)
        else:
            # For local storage, we don't have URL generation
            return None
    
    def get_original_file_url(self, file_id: str, user_id: int = None, expires: int = 3600) -> Optional[str]:
        """Get URL for original file access."""
        if self.is_minio_backend():
            return self.storage_service.get_original_file_url(file_id, user_id, expires)
        else:
            # For local storage, try to get the path
            if hasattr(self.storage_service, 'get_original_file_path'):
                return self.storage_service.get_original_file_path(file_id, user_id)
            return None
    
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
            'backend': self.storage_backend,
            'service_class': self.storage_service.__class__.__name__,
            'is_minio': self.is_minio_backend(),
        }
        
        # Add backend-specific information
        if self.is_minio_backend():
            try:
                minio_config = getattr(settings, 'MINIO_SETTINGS', {})
                info['minio_endpoint'] = minio_config.get('ENDPOINT', 'not configured')
                info['minio_bucket'] = minio_config.get('BUCKET_NAME', 'not configured')
                info['minio_secure'] = minio_config.get('SECURE', False)
            except Exception as e:
                info['minio_error'] = str(e)
        else:
            try:
                info['local_media_root'] = str(getattr(settings, 'MEDIA_ROOT', 'not configured'))
            except Exception as e:
                info['local_error'] = str(e)
        
        return info
    
    def migrate_to_minio(self, user_id: int = None, dry_run: bool = True) -> Dict[str, Any]:
        """
        Migrate existing local files to MinIO storage.
        
        Args:
            user_id: Specific user to migrate (None for all users)
            dry_run: If True, only analyze what would be migrated
            
        Returns:
            Migration report
        """
        if self.is_minio_backend():
            return {"error": "Already using MinIO backend"}
        
        if not MinIOFileStorageService:
            return {"error": "MinIO storage service not available"}
        
        # Import here to avoid circular imports
        from ..models import KnowledgeBaseItem
        
        # Query knowledge base items
        query = KnowledgeBaseItem.objects.all()
        if user_id:
            query = query.filter(user_id=user_id)
        
        items = query.filter(
            models.Q(file__isnull=False) | models.Q(original_file__isnull=False)
        )
        
        migration_report = {
            'dry_run': dry_run,
            'total_items': items.count(),
            'migrated_items': 0,
            'failed_items': 0,
            'errors': [],
            'storage_backend': self.storage_backend,
        }
        
        if dry_run:
            migration_report['would_migrate'] = []
            for item in items:
                item_info = {
                    'id': item.id,
                    'title': item.title,
                    'user_id': item.user_id,
                    'has_file': bool(item.file),
                    'has_original_file': bool(item.original_file),
                    'created_at': item.created_at.isoformat(),
                }
                migration_report['would_migrate'].append(item_info)
        else:
            # Actual migration would be implemented here
            migration_report['error'] = 'Actual migration not implemented in this version'
        
        return migration_report


# Global singleton instance
_storage_adapter = None

def get_storage_adapter() -> StorageAdapter:
    """Get the global storage adapter instance."""
    global _storage_adapter
    if _storage_adapter is None:
        _storage_adapter = StorageAdapter()
    return _storage_adapter