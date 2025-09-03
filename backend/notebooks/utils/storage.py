"""
Storage operations for the notebooks module.
Consolidated MinIO-based storage functionality.
"""

import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

from .helpers import calculate_content_hash, calculate_source_hash

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    Minio = None
    S3Error = Exception
    MINIO_AVAILABLE = False


class MinIOBackend:
    """MinIO backend for file storage operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.minio_backend")
        
        if not MINIO_AVAILABLE:
            raise ImportError("MinIO is not available. Install with: pip install minio")
        
        # Initialize MinIO client
        self.client = self._initialize_client()
        self.bucket_name = getattr(settings, 'MINIO_BUCKET_NAME', 'deepsight-users')
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
        
        self.logger.info(f"MinIO backend initialized with bucket: {self.bucket_name}")
    
    def _initialize_client(self) -> Minio:
        """Initialize MinIO client with settings."""
        endpoint = getattr(settings, 'MINIO_ENDPOINT', 'localhost:9000')
        access_key = getattr(settings, 'MINIO_ACCESS_KEY', 'minioadmin')
        secret_key = getattr(settings, 'MINIO_SECRET_KEY', 'minioadmin')
        secure = getattr(settings, 'MINIO_USE_SSL', False)
        
        return Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                self.logger.info(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            self.logger.error(f"Error ensuring bucket exists: {e}")
            raise
    
    def store_file(self, object_key: str, file_content: bytes, content_type: str = None) -> bool:
        """Store file content in MinIO."""
        try:
            import io
            
            extra_args = {}
            if content_type:
                extra_args['content_type'] = content_type
            
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=io.BytesIO(file_content),
                length=len(file_content),
                **extra_args
            )
            
            self.logger.debug(f"Stored file: {object_key}")
            return True
            
        except S3Error as e:
            self.logger.error(f"Error storing file {object_key}: {e}")
            return False
    
    def get_file(self, object_key: str) -> Optional[bytes]:
        """Retrieve file content from MinIO."""
        try:
            response = self.client.get_object(self.bucket_name, object_key)
            return response.read()
        except S3Error as e:
            self.logger.error(f"Error retrieving file {object_key}: {e}")
            return None
    
    def delete_file(self, object_key: str) -> bool:
        """Delete a single file from MinIO."""
        try:
            self.client.remove_object(self.bucket_name, object_key)
            self.logger.debug(f"Deleted file: {object_key}")
            return True
        except S3Error as e:
            self.logger.error(f"Error deleting file {object_key}: {e}")
            return False
    
    def delete_folder(self, folder_prefix: str) -> bool:
        """
        Delete all files in a folder (prefix) from MinIO.
        
        Args:
            folder_prefix: Folder prefix to delete (e.g., "user_123/kb/uuid-folder/")
            
        Returns:
            True if deletion was successful (or folder was empty)
        """
        try:
            # List all objects with the given prefix
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=folder_prefix,
                recursive=True
            )
            
            # Collect object names to delete
            object_names = [obj.object_name for obj in objects]
            
            if not object_names:
                self.logger.info(f"No objects found to delete with prefix: {folder_prefix}")
                return True
            
            # Delete objects in batches (MinIO supports batch deletion)
            from minio.deleteobjects import DeleteObject
            delete_objects = [DeleteObject(name) for name in object_names]
            
            # Perform batch deletion
            delete_result = self.client.remove_objects(self.bucket_name, delete_objects)
            
            # Check for any errors in deletion
            deleted_count = 0
            errors = []
            for delete_error in delete_result:
                if hasattr(delete_error, 'error_message'):
                    errors.append(f"{delete_error.object_name}: {delete_error.error_message}")
                else:
                    deleted_count += 1
            
            if errors:
                self.logger.error(f"Errors deleting objects from folder {folder_prefix}: {errors}")
                return False
            else:
                self.logger.info(f"Successfully deleted {deleted_count} objects from folder: {folder_prefix}")
                return True
            
        except S3Error as e:
            self.logger.error(f"Failed to delete folder {folder_prefix}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error deleting folder {folder_prefix}: {e}")
            return False
    
    def get_presigned_url(self, object_key: str, expires: int = 3600, response_headers: Dict[str, str] = None) -> Optional[str]:
        """Get pre-signed URL for file access."""
        try:
            kwargs = {
                'bucket_name': self.bucket_name,
                'object_name': object_key,
                'expires': timedelta(seconds=expires)
            }
            
            if response_headers:
                kwargs['response_headers'] = response_headers
                
            url = self.client.presigned_get_object(**kwargs)
            return url
        except S3Error as e:
            self.logger.error(f"Error generating presigned URL for {object_key}: {e}")
            return None
    
    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """
        Copy a file from one MinIO location to another within the same bucket.
        
        Args:
            source_key: Source object key in MinIO
            dest_key: Destination object key in MinIO
            
        Returns:
            True if copy was successful, False otherwise
        """
        try:
            from minio.commonconfig import CopySource
            
            # Create copy source configuration
            copy_source = CopySource(
                bucket_name=self.bucket_name,
                object_name=source_key
            )
            
            # Perform the copy operation
            self.client.copy_object(
                bucket_name=self.bucket_name,
                object_name=dest_key,
                source=copy_source
            )
            
            self.logger.debug(f"Successfully copied file from {source_key} to {dest_key}")
            return True
            
        except S3Error as e:
            self.logger.error(f"Error copying file from {source_key} to {dest_key}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error copying file from {source_key} to {dest_key}: {e}")
            return False

    def list_objects(self, prefix: str = "") -> List[str]:
        """List objects in bucket with optional prefix."""
        try:
            objects = self.client.list_objects(self.bucket_name, prefix=prefix)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            self.logger.error(f"Error listing objects with prefix {prefix}: {e}")
            return []
    
    def save_file_with_auto_key(
        self, 
        content: bytes, 
        filename: str, 
        prefix: str, 
        content_type: str = None,
        metadata: Dict[str, str] = None,
        user_id: str = None,
        file_id: str = None,
        subfolder: str = None,
        subfolder_uuid: str = None
    ) -> str:
        """
        Save file to MinIO with auto-generated object key.
        
        Args:
            content: File content as bytes
            filename: Original filename
            prefix: Storage prefix (kb, reports, podcasts, etc.)
            content_type: MIME content type
            metadata: Additional metadata
            user_id: User ID for folder organization
            file_id: File ID for kb files organization (optional)
            subfolder: Subfolder name for kb files (optional)
            subfolder_uuid: UUID for subfolder organization (optional)
            
        Returns:
            Generated object key
        """
        try:
            import hashlib
            from datetime import datetime, timezone
            from io import BytesIO
            import uuid
            
            # Calculate content hash for deduplication
            content_hash = hashlib.sha256(content).hexdigest()
            
            # Generate object key
            object_key = self._generate_object_key(prefix, filename, content_hash, user_id, file_id, subfolder, subfolder_uuid)
            
            # Prepare metadata
            object_metadata = {
                'original_filename': filename,
                'content_hash': content_hash,
                'upload_timestamp': datetime.now(timezone.utc).isoformat(),
            }
            if metadata:
                object_metadata.update(metadata)
            
            # Sanitize metadata to ensure ASCII compatibility
            object_metadata = self._sanitize_metadata(object_metadata)
            
            # Determine content type
            if not content_type:
                import mimetypes
                content_type, _ = mimetypes.guess_type(filename)
                content_type = content_type or 'application/octet-stream'
            
            # Upload to MinIO
            content_stream = BytesIO(content)
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=content_stream,
                length=len(content),
                content_type=content_type,
                metadata=object_metadata
            )
            
            self.logger.info(f"Saved file to MinIO: {object_key} ({len(content)} bytes)")
            return object_key
            
        except S3Error as e:
            self.logger.error(f"Failed to save file to MinIO: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error saving file to MinIO: {e}")
            raise
    
    def _generate_object_key(self, prefix: str, filename: str, content_hash: str = None, user_id: str = None, file_id: str = None, subfolder: str = None, subfolder_uuid: str = None) -> str:
        """
        Generate MinIO object key using the pattern: {user_id}/{prefix}/{file_id}/{subfolder}/{uuid}/{filename}
        For kb files: {user_id}/kb/{file_id}/{filename} or {user_id}/kb/{file_id}/images/{uuid}/{filename}
        For other files: {user_id}/{prefix}/{timestamp}_{content_hash}_{uuid}{extension}
        """
        import hashlib
        from datetime import datetime, timezone
        import uuid
        
        # For kb files with file_id, use structured folder approach
        if prefix == "kb" and file_id:
            if subfolder:
                if subfolder_uuid:
                    object_key = f"{user_id}/kb/{file_id}/{subfolder}/{subfolder_uuid}/{filename}"
                else:
                    object_key = f"{user_id}/kb/{file_id}/{subfolder}/{filename}"
            else:
                object_key = f"{user_id}/kb/{file_id}/{filename}"
            self.logger.debug(f"Generated structured object key: {object_key}")
            return object_key
        
        # For other files or legacy kb files, use timestamp-based approach
        # Extract extension
        if '.' in filename:
            _, extension = filename.rsplit('.', 1)
            extension = f".{extension}"
        else:
            extension = ""
        
        # Generate timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        # Generate short UUID
        short_uuid = str(uuid.uuid4()).replace('-', '')[:8]
        
        # Use provided content hash or generate a random one
        if content_hash:
            hash_part = content_hash[:16]
        else:
            hash_part = hashlib.sha256(f"{timestamp}_{short_uuid}".encode()).hexdigest()[:16]
        
        # Generate object key with user_id prefix if provided
        if user_id:
            object_key = f"{user_id}/{prefix}/{timestamp}_{hash_part}_{short_uuid}{extension}"
        else:
            object_key = f"{prefix}/{timestamp}_{hash_part}_{short_uuid}{extension}"
        
        self.logger.debug(f"Generated object key: {object_key}")
        return object_key
    
    def _sanitize_metadata(self, metadata: Dict[str, str]) -> Dict[str, str]:
        """Sanitize metadata to ensure ASCII compatibility."""
        sanitized = {}
        for key, value in metadata.items():
            # Convert to string and encode/decode to ensure ASCII
            try:
                sanitized_value = str(value).encode('ascii', errors='ignore').decode('ascii')
                sanitized[key] = sanitized_value
            except Exception:
                # Skip problematic metadata
                continue
        return sanitized


class FileStorageService:
    """Unified file storage service using MinIO backend."""
    
    def __init__(self):
        self.service_name = "file_storage"
        self.logger = logging.getLogger(f"{__name__}.file_storage")
        
        # Initialize MinIO backend lazily
        self._minio_backend = None
    
    @property
    def minio_backend(self):
        """Lazy initialization of MinIO backend."""
        if self._minio_backend is None:
            self._minio_backend = MinIOBackend()
        return self._minio_backend
    
    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log service operations with consistent formatting."""
        message = f"[{self.service_name}] {operation}"
        if details:
            message += f": {details}"
        getattr(self.logger, level)(message)
    
    def store_processed_file(
        self,
        content: str,
        metadata: Dict[str, Any],
        processing_result: Dict[str, Any],
        user_id: int,
        notebook_id: int,
        source_id: Optional[int] = None,
        original_file_path: Optional[str] = None,
        source_identifier: Optional[str] = None,
        kb_item_id: Optional[str] = None,
    ) -> str:
        """Store processed file content in user's knowledge base."""
        try:
            # Import here to avoid circular imports
            from ..models import KnowledgeBaseItem, Notebook
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            user = User.objects.get(id=user_id)
            # Verify notebook ownership for security
            notebook = Notebook.objects.get(id=notebook_id, user=user)
            
            # Calculate source hash (primary) - use source_identifier if provided
            if source_identifier:
                source_hash = calculate_source_hash(source_identifier, user_id)
            else:
                # Fallback to content hash if no source identifier provided
                source_hash = calculate_content_hash(content)
            
            # Check if we're updating an existing pre-created KnowledgeBaseItem
            if kb_item_id:
                try:
                    # Security: Verify the knowledge base item belongs to the verified notebook
                    knowledge_item = KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
                    
                    # Update the existing record with processed data
                    knowledge_item.content = content
                    knowledge_item.source_hash = source_hash
                    knowledge_item.metadata = {
                        'file_extension': metadata.get('file_extension', ''),
                        'file_size': metadata.get('file_size', len(content.encode('utf-8'))),
                        'content_type': metadata.get('content_type', ''),
                        'processing_status': 'completed',
                        'original_filename': metadata.get('original_filename', 'Untitled'),
                        'source_hash_used': source_hash,  # Track source hash used for deduplication
                        **metadata  # Include all other metadata
                    }
                    knowledge_item.file_metadata = {
                        'file_size': metadata.get('file_size', len(content.encode('utf-8'))),
                        'content_type': metadata.get('content_type', ''),
                        'processing_result': processing_result
                    }
                    # Don't change processing_status here - let the task handle it
                    knowledge_item.save()
                    
                    self.log_operation("kb_item_updated", f"Updated existing KB item: {knowledge_item.id}")
                    
                    # Generate object keys for MinIO storage using kb pattern with actual item ID
                    base_key = f"{user_id}/kb/{knowledge_item.id}"
                    
                    # Store main content only if not skipped (for marker processing that provides better content)
                    content_key = None
                    if not processing_result.get('skip_content_file', False):
                        content_filename = processing_result.get('content_filename', 'extracted_content.md')
                        content_key = f"{base_key}/{content_filename}"
                        
                        content_bytes = content.encode('utf-8')
                        if not self.minio_backend.store_file(content_key, content_bytes, 'text/markdown'):
                            raise Exception("Failed to store content file for existing KB item")
                    
                    # Store original file if provided
                    original_file_key = None
                    if original_file_path and os.path.exists(original_file_path):
                        with open(original_file_path, 'rb') as f:
                            original_content = f.read()
                        
                        original_filename = metadata.get('original_filename', os.path.basename(original_file_path))
                        original_file_key = f"{base_key}/{original_filename}"
                        
                        if not self.minio_backend.store_file(original_file_key, original_content, metadata.get('content_type')):
                            self.log_operation("original_file_storage_failed", f"Failed to store original file for existing KB item: {original_filename}", "warning")
                        else:
                            self.log_operation("original_file_stored", f"Successfully stored original file for existing KB item: {original_filename}")
                    
                    # Update database record with the object keys
                    knowledge_item.file_object_key = content_key
                    knowledge_item.original_file_object_key = original_file_key
                    knowledge_item.save()
                    
                    # Return early since we've processed the existing item
                    return str(knowledge_item.id)
                    
                except KnowledgeBaseItem.DoesNotExist:
                    self.log_operation("kb_item_not_found", f"KB item {kb_item_id} not found, creating new one", "warning")
                    knowledge_item = None
            else:
                knowledge_item = None
            
            # If no existing item to update, check for duplicates and create new one
            if not knowledge_item:
                # Check for existing source first (primary check)
                existing_item = KnowledgeBaseItem.objects.filter(
                    user=user, source_hash=source_hash
                ).first()
                
                if existing_item:
                    self.log_operation("duplicate_source", f"Source already exists: {existing_item.id}")
                    return str(existing_item.id)
                
                # Secondary check: content-based deduplication for different filenames with same content
                if source_identifier:  # Only do secondary check if we used source hash as primary
                    content_hash = calculate_content_hash(content)
                    existing_content = KnowledgeBaseItem.objects.filter(
                        user=user,
                        source_hash=content_hash  # Check if content hash exists in any source_hash
                    ).first()
                    
                    if existing_content:
                        self.log_operation("duplicate_content", f"Content already exists with different source: {existing_content.id}")
                        return str(existing_content.id)
                
                # Create database record first to get the ID
                knowledge_item = KnowledgeBaseItem.objects.create(
                    notebook=notebook,
                    title=metadata.get('original_filename', 'Untitled'),
                    content_type=metadata.get('source_type', 'document'),  # Map source_type to content_type
                    content=content,  # Store the actual content in the database
                    source_hash=source_hash,
                    tags=[],  # Explicitly set empty list
                    metadata={
                        'file_extension': metadata.get('file_extension', ''),
                        'file_size': metadata.get('file_size', len(content.encode('utf-8'))),
                        'content_type': metadata.get('content_type', ''),
                        'processing_status': 'completed',
                        'original_filename': metadata.get('original_filename', 'Untitled'),
                        'source_hash_used': source_hash,  # Track source hash used for deduplication
                        **metadata  # Include all other metadata
                    },
                    file_metadata={
                        'file_size': metadata.get('file_size', len(content.encode('utf-8'))),
                        'content_type': metadata.get('content_type', ''),
                        'processing_result': processing_result
                    }
                )
            
            # Generate object keys for MinIO storage using kb pattern with actual item ID
            base_key = f"{user_id}/kb/{knowledge_item.id}"
            
            # Store main content only if not skipped (for marker processing that provides better content)
            content_key = None
            if not processing_result.get('skip_content_file', False):
                content_filename = processing_result.get('content_filename', 'extracted_content.md')
                content_key = f"{base_key}/{content_filename}"
                
                content_bytes = content.encode('utf-8')
                if not self.minio_backend.store_file(content_key, content_bytes, 'text/markdown'):
                    # If storage fails, clean up the database record
                    knowledge_item.delete()
                    raise Exception("Failed to store content file")
            
            # Store original file if provided
            original_file_key = None
            if original_file_path and os.path.exists(original_file_path):
                with open(original_file_path, 'rb') as f:
                    original_content = f.read()
                
                original_filename = metadata.get('original_filename', os.path.basename(original_file_path))
                original_file_key = f"{base_key}/{original_filename}"
                
                if not self.minio_backend.store_file(original_file_key, original_content, metadata.get('content_type')):
                    self.log_operation("original_file_storage_failed", f"Failed to store original file: {original_filename}", "warning")
            
            # Update database record with the object keys
            knowledge_item.file_object_key = content_key
            knowledge_item.original_file_object_key = original_file_key
            knowledge_item.save()
            
            # Knowledge base item is already directly linked to notebook via foreign key
            # No additional linking needed as the item was created with notebook=notebook
            
            self.log_operation("file_stored", f"Stored file with ID: {knowledge_item.id}")
            return str(knowledge_item.id)
            
        except Exception as e:
            self.log_operation("store_error", f"Failed to store file: {e}", "error")
            raise
    
    def get_file_content(self, file_id: str, user_id: int) -> Optional[str]:
        """Retrieve file content by ID."""
        try:
            from ..models import KnowledgeBaseItem, Notebook
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            # Security: Find knowledge base item through user's notebooks
            user_notebooks = Notebook.objects.filter(user=user)
            knowledge_item = KnowledgeBaseItem.objects.get(id=file_id, notebook__in=user_notebooks)
            
            # First, try to get content from the database field
            if knowledge_item.content:
                return knowledge_item.content
            
            # Fallback to MinIO if no content in database
            if knowledge_item.file_object_key:
                content_bytes = self.minio_backend.get_file(knowledge_item.file_object_key)
                if content_bytes:
                    return content_bytes.decode('utf-8')
            
            return None
            
        except Exception as e:
            self.log_operation("get_content_error", f"Failed to get content for {file_id}: {e}", "error")
            return None
    
    def get_file_url(self, file_id: str, user_id: int, file_type: str = 'content') -> Optional[str]:
        """Get pre-signed URL for file access."""
        try:
            from ..models import KnowledgeBaseItem, Notebook
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            # Security: Find knowledge base item through user's notebooks
            user_notebooks = Notebook.objects.filter(user=user)
            knowledge_item = KnowledgeBaseItem.objects.get(id=file_id, notebook__in=user_notebooks)
            
            object_key = None
            if file_type == 'content':
                object_key = knowledge_item.file_object_key
            elif file_type == 'original':
                object_key = knowledge_item.original_file_object_key
            
            if not object_key:
                return None
            
            return self.minio_backend.get_presigned_url(object_key)
            
        except Exception as e:
            self.log_operation("get_url_error", f"Failed to get URL for {file_id}: {e}", "error")
            return None
    
    
    def get_user_knowledge_base(self, user_id: int, content_type: str = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all knowledge base items for a user."""
        try:
            from ..models import KnowledgeBaseItem
            from django.contrib.auth import get_user_model
            
            from ..models import Notebook
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            # Build query - show all items from user's notebooks regardless of processing status
            user_notebooks = Notebook.objects.filter(user=user)
            queryset = KnowledgeBaseItem.objects.filter(notebook__in=user_notebooks)
            
            if content_type:
                queryset = queryset.filter(content_type=content_type)
            
            # Apply pagination
            queryset = queryset.order_by('-created_at')[offset:offset + limit]
            
            # Convert to list of dictionaries
            items = []
            for item in queryset:
                items.append({
                    'id': str(item.id),
                    'title': item.title,
                    'content_type': item.content_type,
                    'source_hash': item.source_hash,
                    'processing_status': item.processing_status,  # Add processing status
                    'metadata': item.metadata or {},
                    'file_metadata': item.file_metadata or {},
                    'created_at': item.created_at.isoformat(),
                    'updated_at': item.updated_at.isoformat(),
                })
            
            self.log_operation("get_user_kb", f"Retrieved {len(items)} items for user {user_id}")
            return items
            
        except Exception as e:
            self.log_operation("get_user_kb_error", f"Failed to get knowledge base for user {user_id}: {e}", "error")
            return []
    
    def link_knowledge_item_to_notebook(self, kb_item_id: str, notebook_id: int, user_id: int, notes: str = "") -> bool:
        """Legacy method - Knowledge items are now notebook-specific by default."""
        # This method is no longer needed since KnowledgeBaseItems are created directly in notebooks
        # Kept for backward compatibility but returns True since items are already linked
        self.log_operation("legacy_link_called", f"Legacy link method called for KB item {kb_item_id} - items are now notebook-specific")
        return True
    
    def delete_knowledge_base_item(self, kb_item_id: str, user_id: int) -> bool:
        """Delete a notebook-specific knowledge base item and its MinIO files."""
        try:
            from ..models import KnowledgeBaseItem
            
            # Get the knowledge base item (no longer filtered by user since it's notebook-specific)
            kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id)
            
            # Delete files from MinIO
            if kb_item.file_object_key:
                self.minio_backend.delete_file(kb_item.file_object_key)
            if kb_item.original_file_object_key:
                self.minio_backend.delete_file(kb_item.original_file_object_key)
            
            # Delete the KB item directly
            kb_item.delete()
            
            self.log_operation("kb_item_deleted", f"Deleted KB item {kb_item_id}")
            
            return True
            
        except Exception as e:
            self.log_operation("delete_kb_error", f"Failed to delete KB item {kb_item_id}: {e}", "error")
            return False
    
    def unlink_knowledge_item_from_notebook(self, kb_item_id: str, notebook_id: int, user_id: int) -> bool:
        """Legacy method - Knowledge items are now notebook-specific and cannot be unlinked."""
        # Since knowledge items are now directly bound to notebooks, unlinking means deleting
        # This method is kept for backward compatibility but redirects to delete_notebook_knowledge_item
        self.log_operation("legacy_unlink_called", f"Legacy unlink method called for KB item {kb_item_id} - redirecting to delete")
        return self.delete_notebook_knowledge_item(notebook_id, kb_item_id)

    def get_notebook_knowledge_items(self, notebook_id: str, content_type: str = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all knowledge base items for a specific notebook."""
        try:
            from ..models import KnowledgeBaseItem, Notebook
            
            # Get the notebook (this will validate it exists)
            notebook = Notebook.objects.get(id=notebook_id)
            
            # Build query - show all items regardless of processing status
            queryset = KnowledgeBaseItem.objects.filter(notebook=notebook)
            
            if content_type:
                queryset = queryset.filter(content_type=content_type)
            
            # Apply pagination
            queryset = queryset.order_by('-created_at')[offset:offset + limit]
            
            # Convert to list of dictionaries
            items = []
            for item in queryset:
                items.append({
                    'id': str(item.id),
                    'title': item.title,
                    'content_type': item.content_type,
                    'source_hash': item.source_hash,
                    'processing_status': item.processing_status,
                    'metadata': item.metadata or {},
                    'file_metadata': item.file_metadata or {},
                    'notes': item.notes,
                    'created_at': item.created_at.isoformat(),
                    'updated_at': item.updated_at.isoformat(),
                })
            
            self.log_operation("get_notebook_kb", f"Retrieved {len(items)} items for notebook {notebook_id}")
            return items
            
        except Exception as e:
            self.log_operation("get_notebook_kb_error", f"Failed to get knowledge base for notebook {notebook_id}: {e}", "error")
            return []

    def get_file_by_upload_id(self, upload_file_id: str, user_pk: int = None) -> Optional[Dict[str, Any]]:
        """
        Legacy method - not implemented in current MinIO storage system.
        The upload system now uses direct KnowledgeBaseItem creation.
        """
        self.log_operation("legacy_get_file_by_upload_id", f"Legacy method called for upload_id {upload_file_id}")
        return None

    def delete_notebook_knowledge_item(self, notebook_id: str, kb_item_id: str) -> bool:
        """Delete a knowledge base item from a specific notebook."""
        try:
            from ..models import KnowledgeBaseItem, Notebook
            
            # Get the notebook (validates ownership through notebook access)
            notebook = Notebook.objects.get(id=notebook_id)
            
            # Get and delete the knowledge base item
            kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
            
            # Clean up any associated files from MinIO
            if kb_item.file_object_key:
                try:
                    self.minio_backend.delete_file(kb_item.file_object_key)
                except Exception as e:
                    self.log_operation("minio_delete_error", f"Failed to delete processed file {kb_item.file_object_key}: {e}", "error")
            
            if kb_item.original_file_object_key:
                try:
                    self.minio_backend.delete_file(kb_item.original_file_object_key)
                except Exception as e:
                    self.log_operation("minio_delete_error", f"Failed to delete original file {kb_item.original_file_object_key}: {e}", "error")
            
            # Delete the database record
            kb_item.delete()
            
            self.log_operation("kb_item_deleted", f"Deleted KB item {kb_item_id} from notebook {notebook_id}")
            return True
            
        except Exception as e:
            self.log_operation("delete_kb_item_error", f"Failed to delete KB item {kb_item_id} from notebook {notebook_id}: {e}", "error")
            return False


class StorageAdapter:
    """Adapter that provides unified storage operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.storage_adapter")
        self.storage_service = FileStorageService()
        self.logger.info("Storage adapter initialized")
    
    @property
    def file_storage(self):
        """Compatibility property for legacy code."""
        return self.storage_service
    
    def is_minio_backend(self) -> bool:
        """Check if currently using MinIO backend."""
        return True  # Always MinIO now
    
    def store_processed_file(self, *args, **kwargs):
        """Store processed file using the unified service."""
        return self.storage_service.store_processed_file(*args, **kwargs)
    
    def get_file_content(self, *args, **kwargs):
        """Get file content using the unified service."""
        return self.storage_service.get_file_content(*args, **kwargs)
    
    def get_file_url(self, *args, **kwargs):
        """Get file URL using the unified service."""
        return self.storage_service.get_file_url(*args, **kwargs)
    
    
    def get_user_knowledge_base(self, *args, **kwargs):
        """Get user knowledge base using the unified service."""
        return self.storage_service.get_user_knowledge_base(*args, **kwargs)
    
    def link_knowledge_item_to_notebook(self, *args, **kwargs):
        """Link knowledge item to notebook using the unified service."""
        return self.storage_service.link_knowledge_item_to_notebook(*args, **kwargs)
    
    def delete_knowledge_base_item(self, *args, **kwargs):
        """Delete knowledge base item using the unified service."""
        return self.storage_service.delete_knowledge_base_item(*args, **kwargs)
    
    def unlink_knowledge_item_from_notebook(self, *args, **kwargs):
        """Unlink knowledge item from notebook using the unified service."""
        return self.storage_service.unlink_knowledge_item_from_notebook(*args, **kwargs)


# Factory function for getting storage adapter
def get_storage_adapter() -> StorageAdapter:
    """Get storage adapter instance."""
    return StorageAdapter()


# Factory function for getting MinIO backend
def get_minio_backend() -> MinIOBackend:
    """Get MinIO backend instance."""
    return MinIOBackend() 