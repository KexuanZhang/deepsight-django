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
        self.logger.info("Initialized enhanced storage adapter")
    
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


class EnhancedFileStorageService(FileStorageService):
    """
    Enhanced file storage service with additional methods needed by views.
    """
    
    def get_content_with_minio_urls(self, file_id: str, user_id: int = None, expires: int = 86400) -> Optional[str]:
        """
        Retrieve file content with all image links converted to direct MinIO pre-signed URLs.
        
        Args:
            file_id: Knowledge base item ID
            user_id: User ID for access control
            expires: URL expiration time in seconds (default: 24 hours)
            
        Returns:
            Content with MinIO URLs for images
        """
        try:
            # Import here to avoid circular imports
            from ..models import KnowledgeBaseItem, KnowledgeBaseImage
            
            # Query the database for the knowledge base item
            kb_query = KnowledgeBaseItem.objects.filter(id=file_id)
            if user_id:
                kb_query = kb_query.filter(user=user_id)

            kb_item = kb_query.first()
            if not kb_item:
                return None

            # Get base content - prioritize database field first
            content = None
            if kb_item.content:
                content = kb_item.content
            elif kb_item.file_object_key:
                try:
                    content_bytes = self.minio_backend.get_file(kb_item.file_object_key)
                    if content_bytes:
                        content = content_bytes.decode('utf-8')
                except Exception as e:
                    self.log_operation(
                        "get_content_minio_error",
                        f"kb_item_id={file_id}, object_key={kb_item.file_object_key}, error={str(e)}",
                        "error",
                    )
                    return None
            
            if not content:
                return None
            
            # Get all images for this knowledge base item
            images = KnowledgeBaseImage.objects.filter(knowledge_base_item=kb_item)
            
            # Create mapping of filenames to MinIO URLs
            image_url_mapping = {}
            for image in images:
                try:
                    presigned_url = self.minio_backend.get_presigned_url(image.minio_object_key, expires)
                    # Extract filename from object key or use figure_id as fallback
                    import os
                    filename = os.path.basename(image.minio_object_key) if image.minio_object_key else f"{image.figure_id}.jpg"
                    image_url_mapping[filename] = presigned_url
                except Exception as e:
                    self.log_operation(
                        "get_image_url_error",
                        f"Failed to generate URL for image {image.figure_id}: {e}",
                        "error"
                    )
            
            # Update content with MinIO URLs
            if image_url_mapping:
                content = self._update_image_links_to_minio_urls(content, image_url_mapping)
                self.log_operation(
                    "get_content_with_minio_urls_success",
                    f"Retrieved content with {len(image_url_mapping)} MinIO image URLs",
                )
            
            return content
            
        except Exception as e:
            self.log_operation(
                "get_content_with_minio_urls_error",
                f"file_id={file_id}, user_id={user_id}, error={str(e)}",
                "error",
            )
            return None

    def _update_image_links_to_minio_urls(self, content: str, image_url_mapping: dict) -> str:
        """
        Update all image links in content to use MinIO pre-signed URLs.
        
        Args:
            content: Original content with image references
            image_url_mapping: Dictionary mapping filenames to MinIO URLs
            
        Returns:
            Updated content with MinIO URLs
        """
        import re
        
        # Pattern to match markdown image syntax: ![alt](filename)
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        def replace_image_url(match):
            alt_text = match.group(1)
            original_filename = match.group(2)
            
            # Extract just the filename (remove path if present)
            import os
            filename = os.path.basename(original_filename)
            
            # Get MinIO URL for this filename
            minio_url = image_url_mapping.get(filename)
            if minio_url:
                return f'![{alt_text}]({minio_url})'
            else:
                # Keep original if no mapping found
                return match.group(0)
        
        # Replace all image URLs
        updated_content = re.sub(pattern, replace_image_url, content)
        
        return updated_content 