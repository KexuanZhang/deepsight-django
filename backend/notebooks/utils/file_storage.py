"""
MinIO-based file storage service for managing processed files and knowledge base.
Unified implementation that replaces both local filesystem and MinIO storage services.
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

from .minio_backend import get_minio_backend
from .image_processing import clean_title


class FileStorageService:
    """MinIO-based service for storing and managing processed files in user knowledge base."""

    def __init__(self):
        self.service_name = "file_storage"
        self.logger = logging.getLogger(f"{__name__}.file_storage")
        
        # Initialize MinIO backend lazily
        self._minio_backend = None
        
        self.logger.info("MinIO-based file storage service initialized")
    
    @property
    def minio_backend(self):
        """Lazy initialization of MinIO backend."""
        if self._minio_backend is None:
            self._minio_backend = get_minio_backend()
        return self._minio_backend

    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log service operations with consistent formatting."""
        message = f"[{self.service_name}] {operation}"
        if details:
            message += f": {details}"

        getattr(self.logger, level)(message)


    def _calculate_content_hash(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """
        Calculate SHA-256 hash of content for deduplication.
        
        For files with minimal or empty content (like marker-processed PDFs),
        include file metadata to prevent false duplicates.
        """
        # If content is empty, include metadata to create a unique hash
        if not content.strip():
            if metadata:
                # Create a more unique identifier using file metadata
                hash_input = f"{content}|{metadata.get('original_filename', '')}|{metadata.get('file_size', 0)}|{metadata.get('upload_timestamp', '')}"
                return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
        
        # For substantial content, use content-based hashing as before
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

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
        """Store processed file content in user's knowledge base using MinIO storage."""
        try:
            # Import here to avoid circular imports
            from ..models import KnowledgeBaseItem, KnowledgeItem, Notebook, Source
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            
            # Get the user instance
            user = User.objects.get(id=user_id)

            # Calculate content hash for deduplication
            content_hash = self._calculate_content_hash(content, metadata)

            # Check if this content already exists in user's knowledge base
            existing_item = KnowledgeBaseItem.objects.filter(
                user=user, source_hash=content_hash
            ).first()

            if existing_item:
                self.log_operation(
                    "duplicate_content", f"Content already exists: {existing_item.id}"
                )
                # Link existing knowledge base item to current notebook
                notebook = Notebook.objects.get(id=notebook_id, user=user)

                # Get the source if provided
                source = None
                if source_id:
                    source = Source.objects.filter(
                        id=source_id, notebook=notebook
                    ).first()

                knowledge_item, created = KnowledgeItem.objects.get_or_create(
                    notebook=notebook,
                    knowledge_base_item=existing_item,
                    defaults={
                        "source": source,
                        "notes": f"Imported from {metadata.get('filename', 'unknown source')}",
                    },
                )
                return str(existing_item.id)

            # Create new knowledge base item
            title = self._generate_title_from_metadata(metadata)
            content_type = self._determine_content_type(metadata)

            # Create the knowledge base item with MinIO fields
            kb_item = KnowledgeBaseItem.objects.create(
                user=user,
                title=title,
                content_type=content_type,
                content=content,  # Store content in database for searchability
                metadata=metadata,
                source_hash=content_hash,
                tags=self._extract_tags_from_metadata(metadata),
            )

            # Store files in MinIO
            original_filename = metadata.get('original_filename', metadata.get('filename', 'unknown_file'))
            
            # Store original file in MinIO if provided
            if original_file_path and self._file_exists(original_file_path):
                original_object_key = self._store_original_file_minio(kb_item, original_file_path, original_filename)
                # Update the knowledge base item with MinIO object key
                kb_item.original_file_object_key = original_object_key
            
            # Store processed content in MinIO
            # Special handling for markdown files that should use original file as content
            if processing_result.get('use_original_file', False) and original_file_path and self._file_exists(original_file_path):
                # Use the original file as the content file (for .md files)
                kb_item.file_object_key = kb_item.original_file_object_key
            elif not processing_result.get('skip_content_file', False):
                # Normal processing: create separate content file
                content_filename = processing_result.get('content_filename', 'extracted_content.md')
                content_object_key = self._store_content_file_minio(kb_item, content, content_filename)
                # Update the knowledge base item with MinIO object key
                kb_item.file_object_key = content_object_key
            
            # Store extracted images in MinIO if they exist
            if 'images' in processing_result and processing_result['images']:
                image_mapping = self._store_images_minio(kb_item, processing_result['images'])
                
                # Update image links in content if images were saved
                if image_mapping and content:
                    content = self._update_image_links_in_content(content, image_mapping)
                    # Re-store the updated content
                    if kb_item.file_object_key:
                        content_filename = processing_result.get('content_filename', 'extracted_content.md')
                        content_object_key = self._store_content_file_minio(kb_item, content, content_filename)
                        kb_item.file_object_key = content_object_key

            # Store comprehensive file metadata in the database
            # For markdown files using original file, content filename should be the original filename
            content_filename = original_filename if processing_result.get('use_original_file', False) else processing_result.get('content_filename', 'extracted_content.md')
            
            file_metadata = {
                'original_filename': original_filename,
                'content_filename': content_filename,
                'file_size': metadata.get('file_size', 0),
                'content_type': metadata.get('content_type', ''),
                'upload_timestamp': metadata.get('upload_timestamp', datetime.now(timezone.utc).isoformat()),
                'processing_metadata': processing_result,
                'minio_metadata': {
                    'has_original_file': bool(kb_item.original_file_object_key),
                    'has_content_file': bool(kb_item.file_object_key),
                    'has_images': bool('images' in processing_result and processing_result['images']),
                    'uses_original_as_content': processing_result.get('use_original_file', False),
                }
            }
            kb_item.file_metadata = file_metadata
            kb_item.save()
            
            # Link to current notebook
            notebook = Notebook.objects.get(id=notebook_id, user=user)

            # Get the source if provided
            source = None
            if source_id:
                source = Source.objects.filter(id=source_id, notebook=notebook).first()

            KnowledgeItem.objects.create(
                notebook=notebook,
                knowledge_base_item=kb_item,
                source=source,
                notes=f"Processed from {original_filename}",
            )

            self.log_operation(
                "store_knowledge_item",
                f"kb_item_id={kb_item.id}, user_id={user.id}, minio_storage=True",
            )
            return str(kb_item.id)

        except Exception as e:
            self.log_operation("store_file_error", str(e), "error")
            raise

    def _store_original_file_minio(self, kb_item, original_file_path: str, original_filename: str) -> str:
        """Store the original binary file in MinIO."""
        try:
            # Read the original file
            with open(original_file_path, "rb") as f:
                file_content = f.read()

            # Clean the original filename using clean_title function
            file_path = Path(original_filename)
            base_name = file_path.stem
            extension = file_path.suffix
            clean_base_name = clean_title(base_name)
            clean_filename = f"{clean_base_name}{extension}"

            # Store in MinIO with 'kb' prefix using file ID structure
            object_key = self.minio_backend.save_file_with_auto_key(
                content=file_content,
                filename=clean_filename,
                prefix="kb",
                metadata={
                    'kb_item_id': str(kb_item.id),
                    'user_id': str(kb_item.user.id),
                    'file_type': 'original',
                },
                user_id=str(kb_item.user.id),
                file_id=str(kb_item.id)
            )

            self.log_operation(
                "store_original_file_minio",
                f"Stored original file in MinIO: {object_key}",
            )
            return object_key

        except Exception as e:
            self.log_operation(
                "store_original_file_minio_error",
                f"kb_item_id={kb_item.id}, error={str(e)}",
                "error",
            )
            raise

    def _store_content_file_minio(self, kb_item, content: str, content_filename: str) -> str:
        """Store the extracted content in MinIO."""
        try:
            # Convert content to bytes
            content_bytes = content.encode('utf-8')

            # Store in MinIO with 'kb' prefix using file ID structure
            object_key = self.minio_backend.save_file_with_auto_key(
                content=content_bytes,
                filename=content_filename,
                prefix="kb",
                content_type="text/markdown",
                metadata={
                    'kb_item_id': str(kb_item.id),
                    'user_id': str(kb_item.user.id),
                    'file_type': 'content',
                },
                user_id=str(kb_item.user.id),
                file_id=str(kb_item.id)
            )

            self.log_operation(
                "store_content_file_minio",
                f"Stored content file in MinIO: {object_key}",
            )
            return object_key

        except Exception as e:
            self.log_operation(
                "store_content_file_minio_error",
                f"kb_item_id={kb_item.id}, error={str(e)}",
                "error",
            )
            raise

    def _store_images_minio(self, kb_item, images: Dict[str, bytes]) -> Dict[str, str]:
        """
        Store extracted images in MinIO and create KnowledgeBaseImage records.
        
        Args:
            kb_item: Knowledge base item instance
            images: Dictionary of {image_name: image_bytes}
            
        Returns:
            Dictionary mapping original image names to MinIO object keys
        """
        image_mapping = {}
        
        if not images:
            return image_mapping
            
        try:
            # Import here to avoid circular imports
            from ..models import KnowledgeBaseImage
            
            image_id = 1  # Start sequential numbering
            
            for image_file, image_data in images.items():
                try:
                    # Determine content type
                    import mimetypes
                    content_type, _ = mimetypes.guess_type(image_file)
                    content_type = content_type or 'application/octet-stream'
                    
                    # Store in MinIO with 'kb' prefix using file ID structure with images subfolder
                    object_key = self.minio_backend.save_file_with_auto_key(
                        content=image_data,
                        filename=image_file,
                        prefix="kb",
                        content_type=content_type,
                        metadata={
                            'kb_item_id': str(kb_item.id),
                            'user_id': str(kb_item.user.id),
                            'file_type': 'image',
                        },
                        user_id=str(kb_item.user.id),
                        file_id=str(kb_item.id),
                        subfolder="images"
                    )
                    
                    # Create KnowledgeBaseImage record
                    kb_image = KnowledgeBaseImage.objects.create(
                        knowledge_base_item=kb_item,
                        image_caption="",  # Will be filled later if caption data is available
                        minio_object_key=object_key,
                        content_type=content_type,
                        file_size=len(image_data),
                        image_metadata={
                            'original_filename': image_file,
                            'file_size': len(image_data),
                            'content_type': content_type,
                            'kb_item_id': str(kb_item.id),
                        }
                    )
                    
                    image_mapping[image_file] = object_key
                    
                    self.log_operation(
                        "store_image_minio", 
                        f"Stored image in MinIO and DB: {object_key}, kb_image_id={kb_image.id}"
                    )
                    
                    image_id += 1  # Increment for next image
                    
                except Exception as e:
                    self.log_operation("store_image_minio_error", f"Failed to store image {image_file}: {str(e)}", "error")
                    continue
            
            if image_mapping:
                self.log_operation("store_images_minio", f"Stored {len(image_mapping)} images in MinIO and database")
                
        except Exception as e:
            self.log_operation("store_images_minio_error", f"kb_item_id={kb_item.id}, error={str(e)}", "error")
            
        return image_mapping

    def _update_image_links_in_content(self, content: str, image_mapping: Dict[str, str]) -> str:
        """
        Update image links in markdown content to point to MinIO pre-signed URLs.
        
        Args:
            content: Original markdown content
            image_mapping: Dictionary mapping original image names to MinIO object keys
            
        Returns:
            Updated content with MinIO-based image links
        """
        if not image_mapping:
            return content
        
        updated_content = content
        
        # Pattern to match markdown image syntax: ![alt text](image_path)
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        def replace_image_link(match):
            alt_text = match.group(1)
            original_path = match.group(2)
            
            # Extract filename from the original path
            original_filename = os.path.basename(original_path)
            
            # Check if we have a saved version of this image
            if original_filename in image_mapping:
                # Generate pre-signed URL for the image (valid for 24 hours)
                try:
                    object_key = image_mapping[original_filename]
                    presigned_url = self.minio_backend.get_file_url(object_key, expires=86400)  # 24 hours
                    return f"![{alt_text}]({presigned_url})"
                except Exception as e:
                    self.log_operation("update_image_link_error", f"Failed to generate presigned URL for {object_key}: {e}", "error")
                    # Fall back to original link
                    return match.group(0)
            
            # If no mapping found, return original
            return match.group(0)
        
        updated_content = re.sub(image_pattern, replace_image_link, updated_content)
        
        if image_mapping:
            self.log_operation("update_image_links", f"Updated {len(image_mapping)} image links to MinIO URLs")
        
        return updated_content

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

            # Get base content
            content = None
            if kb_item.content:
                content = kb_item.content
            elif kb_item.file_object_key:
                try:
                    content_bytes = self.minio_backend.get_file_content(kb_item.file_object_key)
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
                    presigned_url = self.minio_backend.get_file_url(image.minio_object_key, expires)
                    # Extract filename from object key
                    import os
                    filename = os.path.basename(image.minio_object_key) if image.minio_object_key else "image.jpg"
                    image_url_mapping[filename] = presigned_url
                except Exception as e:
                    self.log_operation(
                        "get_image_url_error",
                        f"Failed to generate URL for image {image.id}: {e}",
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

    def _update_image_links_to_minio_urls(self, content: str, image_url_mapping: Dict[str, str]) -> str:
        """
        Update image links in markdown content to direct MinIO pre-signed URLs.
        
        Args:
            content: Original markdown content
            image_url_mapping: Dictionary mapping image filenames to MinIO pre-signed URLs
            
        Returns:
            Updated content with direct MinIO URLs
        """
        if not image_url_mapping:
            return content
        
        updated_content = content
        
        # Pattern to match markdown image syntax: ![alt text](image_path)
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        def replace_image_link(match):
            alt_text = match.group(1)
            original_path = match.group(2)
            
            # Extract filename from the original path
            original_filename = os.path.basename(original_path)
            
            # Check if we have a MinIO URL for this image
            if original_filename in image_url_mapping:
                minio_url = image_url_mapping[original_filename]
                return f"![{alt_text}]({minio_url})"
            
            # If no mapping found, return original
            return match.group(0)
        
        updated_content = re.sub(image_pattern, replace_image_link, updated_content)
        
        return updated_content

    def get_file_content(self, file_id: str, user_id: int = None) -> Optional[str]:
        """Retrieve file content by knowledge base item ID from MinIO."""
        try:
            # Import here to avoid circular imports
            from ..models import KnowledgeBaseItem

            # Query the database for the knowledge base item
            kb_query = KnowledgeBaseItem.objects.filter(id=file_id)
            if user_id:
                kb_query = kb_query.filter(user=user_id)

            kb_item = kb_query.first()
            if not kb_item:
                return None

            # Return inline content if available
            if kb_item.content:
                return kb_item.content

            # Try to read from MinIO using the processed content object key
            if kb_item.file_object_key:
                try:
                    content_bytes = self.minio_backend.get_file_content(kb_item.file_object_key)
                    content = content_bytes.decode('utf-8')
                    
                    self.log_operation(
                        "get_content_minio_success",
                        f"Retrieved content from MinIO: {kb_item.file_object_key}",
                    )
                    return content
                    
                except Exception as e:
                    self.log_operation(
                        "get_content_minio_error",
                        f"kb_item_id={file_id}, object_key={kb_item.file_object_key}, error={str(e)}",
                        "error",
                    )

            # If no processed content, try the original file (useful for .md files)
            if kb_item.original_file_object_key:
                try:
                    content_bytes = self.minio_backend.get_file_content(kb_item.original_file_object_key)
                    content = content_bytes.decode('utf-8')
                    
                    self.log_operation(
                        "get_original_content_minio_success",
                        f"Retrieved original content from MinIO: {kb_item.original_file_object_key}",
                    )
                    return content
                    
                except Exception as e:
                    self.log_operation(
                        "get_original_content_minio_error",
                        f"kb_item_id={file_id}, object_key={kb_item.original_file_object_key}, error={str(e)}",
                        "error",
                    )

            # Note: Legacy Django FileField support has been removed after MinIO migration
            # All files should now be stored in MinIO with object keys

            return None
            
        except Exception as e:
            self.log_operation(
                "get_content_error",
                f"file_id={file_id}, user_id={user_id}, error={str(e)}",
                "error",
            )
            return None

    def get_file_url(self, file_id: str, user_id: int = None, expires: int = 86400) -> Optional[str]:
        """Get pre-signed URL for file access."""
        try:
            from ..models import KnowledgeBaseItem

            kb_query = KnowledgeBaseItem.objects.filter(id=file_id)
            if user_id:
                kb_query = kb_query.filter(user=user_id)

            kb_item = kb_query.first()
            if not kb_item or not kb_item.file_object_key:
                return None

            url = self.minio_backend.get_file_url(kb_item.file_object_key, expires)
            
            self.log_operation(
                "get_file_url_success",
                f"Generated presigned URL for: {kb_item.file_object_key}",
            )
            return url
            
        except Exception as e:
            self.log_operation(
                "get_file_url_error",
                f"file_id={file_id}, user_id={user_id}, error={str(e)}",
                "error",
            )
            return None

    def get_original_file_url(self, file_id: str, user_id: int = None, expires: int = 86400) -> Optional[str]:
        """Get pre-signed URL for original file access."""
        try:
            from ..models import KnowledgeBaseItem

            kb_query = KnowledgeBaseItem.objects.filter(id=file_id)
            if user_id:
                kb_query = kb_query.filter(user=user_id)

            kb_item = kb_query.first()
            if not kb_item or not kb_item.original_file_object_key:
                return None

            url = self.minio_backend.get_file_url(kb_item.original_file_object_key, expires)
            
            self.log_operation(
                "get_original_file_url_success",
                f"Generated presigned URL for original file: {kb_item.original_file_object_key}",
            )
            return url
            
        except Exception as e:
            self.log_operation(
                "get_original_file_url_error",
                f"file_id={file_id}, user_id={user_id}, error={str(e)}",
                "error",
            )
            return None

    def get_original_file_path(self, file_id: str, user_id: int = None) -> Optional[str]:
        """
        Get the original file URL (MinIO pre-signed URL) instead of local path.
        This method is kept for backward compatibility but now returns MinIO URLs.
        """
        self.log_operation(
            "get_original_file_path_deprecated", 
            f"get_original_file_path is deprecated, use get_original_file_url instead for file_id={file_id}",
            "warning"
        )
        return self.get_original_file_url(file_id, user_id, expires=3600)

    def delete_knowledge_base_item(self, kb_item_id: str, user_id: int) -> bool:
        """Delete a knowledge base item and its entire UUID folder from MinIO."""
        try:
            from ..models import KnowledgeBaseItem

            kb_item = KnowledgeBaseItem.objects.filter(
                id=kb_item_id, user=user_id
            ).first()
            if not kb_item:
                return False

            # Get the source name for vector deletion
            source_name = kb_item.title
            if kb_item.file_metadata and 'original_filename' in kb_item.file_metadata:
                source_name = kb_item.file_metadata['original_filename']
            elif kb_item.metadata and 'original_filename' in kb_item.metadata:
                source_name = kb_item.metadata['original_filename']
            elif kb_item.metadata and 'filename' in kb_item.metadata:
                source_name = kb_item.metadata['filename']

            # Delete vectors from Milvus first
            try:
                from rag.rag import delete_user_file
                delete_user_file(user_id, source_name)
                self.log_operation(
                    "delete_vectors_success",
                    f"kb_item_id={kb_item_id}, user_id={user_id}, source={source_name}",
                )
            except Exception as e:
                self.log_operation(
                    "delete_vectors_error",
                    f"kb_item_id={kb_item_id}, user_id={user_id}, source={source_name}, error={str(e)}",
                    "warning",
                )

            # Delete the entire UUID folder from MinIO instead of individual files
            # The folder structure is: {user_id}/kb/{file_id}/
            folder_prefix = f"{user_id}/kb/{kb_item.id}/"
            deleted_folder = self.minio_backend.delete_folder(folder_prefix)

            # For backward compatibility, also try to delete individual files if folder deletion fails
            if not deleted_folder:
                deleted_files = []
                
                if kb_item.file_object_key:
                    if self.minio_backend.delete_file(kb_item.file_object_key):
                        deleted_files.append(kb_item.file_object_key)
                
                if kb_item.original_file_object_key:
                    if self.minio_backend.delete_file(kb_item.original_file_object_key):
                        deleted_files.append(kb_item.original_file_object_key)

                # Delete associated images if they exist in metadata
                if kb_item.file_metadata and 'processing_metadata' in kb_item.file_metadata:
                    processing_result = kb_item.file_metadata['processing_metadata']
                    if 'images' in processing_result:
                        # Find and delete image objects
                        # Note: This would require tracking image object keys in metadata
                        pass

                self.log_operation(
                    "delete_knowledge_item_fallback",
                    f"kb_item_id={kb_item_id}, user_id={user_id}, deleted_individual_files={len(deleted_files)}",
                )
            else:
                self.log_operation(
                    "delete_knowledge_item_folder",
                    f"kb_item_id={kb_item_id}, user_id={user_id}, deleted_folder={folder_prefix}",
                )

            # Delete the knowledge base item (this will cascade delete notebook links)
            kb_item.delete()

            self.log_operation(
                "delete_knowledge_item",
                f"kb_item_id={kb_item_id}, user_id={user_id}, folder_deletion_success={deleted_folder}",
            )
            return True

        except Exception as e:
            self.log_operation(
                "delete_knowledge_item_error",
                f"kb_item_id={kb_item_id}, user_id={user_id}, error={str(e)}",
                "error",
            )
            return False

    # Utility methods from original implementation
    def _generate_title_from_metadata(self, metadata: Dict[str, Any]) -> str:
        """Generate a meaningful title from metadata."""
        if "original_filename" in metadata:
            return os.path.splitext(metadata["original_filename"])[0]
        elif "source_url" in metadata:
            from urllib.parse import urlparse
            parsed = urlparse(metadata["source_url"])
            return parsed.hostname or "Web Content"
        else:
            return f"Content {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"

    def _determine_content_type(self, metadata: Dict[str, Any]) -> str:
        """Determine content type from metadata."""
        if "source_url" in metadata:
            return "webpage"
        elif "file_extension" in metadata:
            ext = metadata["file_extension"].lower()
            if ext in [".pdf", ".doc", ".docx", ".txt"]:
                return "document"
            elif ext in [".mp3", ".mp4", ".wav", ".avi"]:
                return "media"
        return "text"

    def _extract_tags_from_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """Extract relevant tags from metadata."""
        tags = []
        if "file_extension" in metadata:
            tags.append(metadata["file_extension"].replace(".", ""))
        if "content_type" in metadata:
            tags.append(metadata["content_type"].split("/")[0])
        return tags

    def _file_exists(self, file_path: str) -> bool:
        """Check if local file exists."""
        return os.path.exists(file_path)

    # Methods for backward compatibility and additional functionality
    def get_user_knowledge_base(
        self, user_id: int, content_type: str = None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all knowledge base items for a user with MinIO metadata."""
        try:
            from ..models import KnowledgeBaseItem

            query = KnowledgeBaseItem.objects.filter(user=user_id)
            if content_type:
                query = query.filter(content_type=content_type)

            items = query.order_by("-created_at")[offset : offset + limit]

            result = []
            for item in items:
                result.append(
                    {
                        "id": str(item.id),
                        "title": item.title,
                        "content_type": item.content_type,
                        "tags": item.tags,
                        "created_at": item.created_at.isoformat(),
                        "updated_at": item.updated_at.isoformat(),
                        "has_file": bool(item.file_object_key),
                        "has_content": bool(item.content),
                        "has_original_file": bool(item.original_file_object_key),
                        "metadata": item.metadata or {},
                        "file_metadata": item.file_metadata or {},
                        "minio_storage": bool(item.file_object_key or item.original_file_object_key),
                    }
                )

            return result
        except Exception as e:
            self.log_operation(
                "get_knowledge_base_error",
                f"user_id={user_id}, error={str(e)}",
                "error",
            )
            return []

    def link_knowledge_item_to_notebook(
        self, kb_item_id: str, notebook_id: int, user_id: int, notes: str = ""
    ) -> bool:
        """Link an existing knowledge base item to a notebook."""
        try:
            from ..models import KnowledgeBaseItem, KnowledgeItem, Notebook

            # Verify ownership
            kb_item = KnowledgeBaseItem.objects.filter(
                id=kb_item_id, user=user_id
            ).first()
            if not kb_item:
                return False

            notebook = Notebook.objects.filter(id=notebook_id, user=user_id).first()
            if not notebook:
                return False

            # Create or get the link
            knowledge_item, created = KnowledgeItem.objects.get_or_create(
                notebook=notebook,
                knowledge_base_item=kb_item,
                defaults={"notes": notes},
            )

            self.log_operation(
                "link_knowledge_item",
                f"kb_item_id={kb_item_id}, notebook_id={notebook_id}, created={created}",
            )
            return True

        except Exception as e:
            self.log_operation(
                "link_knowledge_item_error",
                f"kb_item_id={kb_item_id}, notebook_id={notebook_id}, error={str(e)}",
                "error",
            )
            return False

    def unlink_knowledge_item_from_notebook(
        self, kb_item_id: str, notebook_id: int, user_id: int
    ) -> bool:
        """Remove a knowledge item link from a specific notebook."""
        try:
            from ..models import KnowledgeItem, Notebook

            # Verify ownership
            notebook = Notebook.objects.filter(id=notebook_id, user=user_id).first()
            if not notebook:
                return False

            # Find and delete the link
            deleted_count, _ = KnowledgeItem.objects.filter(
                notebook=notebook,
                knowledge_base_item_id=kb_item_id
            ).delete()

            self.log_operation(
                "unlink_knowledge_item",
                f"kb_item_id={kb_item_id}, notebook_id={notebook_id}, deleted_count={deleted_count}"
            )
            return deleted_count > 0

        except Exception as e:
            self.log_operation(
                "unlink_knowledge_item_error",
                f"kb_item_id={kb_item_id}, notebook_id={notebook_id}, error={str(e)}",
                "error"
            )
            return False


# Global singleton instance to prevent repeated initialization
file_storage_service = FileStorageService() 