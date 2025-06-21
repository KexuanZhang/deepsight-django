"""
File storage service for managing processed files and knowledge base.
"""

import json
import shutil
import os
import hashlib
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, UTC
from django.conf import settings
from django.core.files.base import ContentFile

from .base_service import BaseService
from ..core.config import settings as config_settings

class FileStorageService(BaseService):
    """Service for storing and managing processed files in user knowledge base."""
    
    def __init__(self):
        super().__init__("file_storage")
        
        # Use Django's MEDIA_ROOT for file storage
        media_root = Path(settings.MEDIA_ROOT)
        
        # Create storage directories that match Django models
        self.source_uploads_dir = media_root / "source_uploads"
        self.knowledge_base_dir = media_root / "knowledge_base"
        
        self.source_uploads_dir.mkdir(exist_ok=True)
        self.knowledge_base_dir.mkdir(exist_ok=True)
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content for deduplication."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def store_processed_file(
        self, 
        content: str, 
        metadata: Dict[str, Any], 
        processing_result: Dict[str, Any],
        user_id: int,
        notebook_id: int,
        source_id: Optional[int] = None
    ) -> str:
        """Store processed file content in user's knowledge base."""
        try:
            # Import here to avoid circular imports
            from ...models import KnowledgeBaseItem, KnowledgeItem, Notebook, Source
            
            # Calculate content hash for deduplication
            content_hash = self._calculate_content_hash(content)
            
            # Check if this content already exists in user's knowledge base
            existing_item = KnowledgeBaseItem.objects.filter(
                user_id=user_id,
                source_hash=content_hash
            ).first()
            
            if existing_item:
                self.log_operation("duplicate_content", f"Content already exists: {existing_item.id}")
                # Link existing knowledge base item to current notebook
                notebook = Notebook.objects.get(id=notebook_id, user_id=user_id)
                
                # Get the source if provided
                source = None
                if source_id:
                    source = Source.objects.filter(id=source_id, notebook=notebook).first()
                
                knowledge_item, created = KnowledgeItem.objects.get_or_create(
                    notebook=notebook,
                    knowledge_base_item=existing_item,
                    defaults={
                        'source': source,
                        'notes': f"Imported from {metadata.get('filename', 'unknown source')}"
                    }
                )
                return existing_item.id
            
            # Create new knowledge base item
            title = self._generate_title_from_metadata(metadata)
            content_type = self._determine_content_type(metadata)
            
            # Create the knowledge base item
            kb_item = KnowledgeBaseItem.objects.create(
                user_id=user_id,
                title=title,
                content_type=content_type,
                content=content,  # Store content inline for now
                metadata=metadata,
                source_hash=content_hash,
                tags=self._extract_tags_from_metadata(metadata)
            )
            
            # Optionally save as file if content is large
            if len(content) > 10000:  # 10KB threshold
                self._save_content_as_file(kb_item, content)
            
            # Link to current notebook
            notebook = Notebook.objects.get(id=notebook_id, user_id=user_id)
            
            # Get the source if provided
            source = None
            if source_id:
                source = Source.objects.filter(id=source_id, notebook=notebook).first()
            
            KnowledgeItem.objects.create(
                notebook=notebook,
                knowledge_base_item=kb_item,
                source=source,
                notes=f"Processed from {metadata.get('filename', 'source')}"
            )
            
            self.log_operation("store_knowledge_item", f"kb_item_id={kb_item.id}, user_id={user_id}, notebook_id={notebook_id}, source_id={source_id}")
            return str(kb_item.id)
            
        except Exception as e:
            self.log_operation("store_file_error", str(e), "error")
            raise
    
    def _save_content_as_file(self, kb_item: 'KnowledgeBaseItem', content: str):
        """Save large content as a file in the knowledge base."""
        filename = f"{kb_item.id}.md"
        content_file = ContentFile(content.encode('utf-8'))
        kb_item.file.save(filename, content_file, save=True)
        # Clear inline content since we now have a file
        kb_item.content = ""
        kb_item.save(update_fields=['content'])
    
    def _generate_title_from_metadata(self, metadata: Dict[str, Any]) -> str:
        """Generate a meaningful title from metadata."""
        if 'original_filename' in metadata:
            return os.path.splitext(metadata['original_filename'])[0]
        elif 'source_url' in metadata:
            from urllib.parse import urlparse
            parsed = urlparse(metadata['source_url'])
            return parsed.hostname or 'Web Content'
        else:
            return f"Content {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"
    
    def _determine_content_type(self, metadata: Dict[str, Any]) -> str:
        """Determine content type from metadata."""
        if 'source_url' in metadata:
            return 'webpage'
        elif 'file_extension' in metadata:
            ext = metadata['file_extension'].lower()
            if ext in ['.pdf', '.doc', '.docx', '.txt']:
                return 'document'
            elif ext in ['.mp3', '.mp4', '.wav', '.avi']:
                return 'media'
        return 'text'
    
    def _extract_tags_from_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """Extract relevant tags from metadata."""
        tags = []
        if 'file_extension' in metadata:
            tags.append(metadata['file_extension'].replace('.', ''))
        if 'content_type' in metadata:
            tags.append(metadata['content_type'].split('/')[0])
        return tags
    
    def get_file_content(self, file_id: str, user_id: int = None) -> Optional[str]:
        """Retrieve file content by knowledge base item ID."""
        try:
            # Import here to avoid circular imports
            from ...models import KnowledgeBaseItem
            
            # Query the database for the knowledge base item
            kb_query = KnowledgeBaseItem.objects.filter(id=file_id)
            if user_id:
                kb_query = kb_query.filter(user_id=user_id)
            
            kb_item = kb_query.first()
            if not kb_item:
                return None
            
            # Return inline content if available
            if kb_item.content:
                return kb_item.content
            
            # Otherwise read from file
            if kb_item.file:
                try:
                    # Use Django's file field to read content
                    with kb_item.file.open('r') as f:
                        return f.read()
                except (FileNotFoundError, OSError) as e:
                    self.log_operation("get_content_file_error", f"kb_item_id={file_id}, error={str(e)}", "error")
                    return None
            
            return None
        except Exception as e:
            self.log_operation("get_content_error", f"file_id={file_id}, user_id={user_id}, error={str(e)}", "error")
            return None
    
    def get_user_knowledge_base(self, user_id: int, content_type: str = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all knowledge base items for a user."""
        try:
            from ...models import KnowledgeBaseItem
            
            query = KnowledgeBaseItem.objects.filter(user_id=user_id)
            if content_type:
                query = query.filter(content_type=content_type)
            
            items = query.order_by('-created_at')[offset:offset + limit]
            
            result = []
            for item in items:
                result.append({
                    'id': str(item.id),
                    'title': item.title,
                    'content_type': item.content_type,
                    'tags': item.tags,
                    'created_at': item.created_at.isoformat(),
                    'updated_at': item.updated_at.isoformat(),
                    'has_file': bool(item.file),
                    'has_content': bool(item.content),
                    'metadata': item.metadata or {}
                })
            
            return result
        except Exception as e:
            self.log_operation("get_knowledge_base_error", f"user_id={user_id}, error={str(e)}", "error")
            return []
    
    def link_knowledge_item_to_notebook(self, kb_item_id: str, notebook_id: int, user_id: int, notes: str = "") -> bool:
        """Link an existing knowledge base item to a notebook."""
        try:
            from ...models import KnowledgeBaseItem, KnowledgeItem, Notebook
            
            # Verify ownership
            kb_item = KnowledgeBaseItem.objects.filter(id=kb_item_id, user_id=user_id).first()
            if not kb_item:
                return False
            
            notebook = Notebook.objects.filter(id=notebook_id, user_id=user_id).first()
            if not notebook:
                return False
            
            # Create or get the link
            knowledge_item, created = KnowledgeItem.objects.get_or_create(
                notebook=notebook,
                knowledge_base_item=kb_item,
                defaults={'notes': notes}
            )
            
            self.log_operation("link_knowledge_item", f"kb_item_id={kb_item_id}, notebook_id={notebook_id}, created={created}")
            return True
            
        except Exception as e:
            self.log_operation("link_knowledge_item_error", f"kb_item_id={kb_item_id}, notebook_id={notebook_id}, error={str(e)}", "error")
            return False
    
    def delete_knowledge_base_item(self, kb_item_id: str, user_id: int) -> bool:
        """Delete a knowledge base item and all its notebook links and related source files."""
        try:
            from ...models import KnowledgeBaseItem, KnowledgeItem, Source
            
            kb_item = KnowledgeBaseItem.objects.filter(id=kb_item_id, user_id=user_id).first()
            if not kb_item:
                return False
            
            # Find all knowledge items that link to this knowledge base item
            knowledge_items = KnowledgeItem.objects.filter(knowledge_base_item=kb_item)
            
            # Collect all related source files to delete
            source_files_to_delete = []
            
            for ki in knowledge_items:
                self.log_operation("delete_source_check", f"Checking KnowledgeItem {ki.id}, has_source: {bool(ki.source)}")
                if ki.source:
                    source = ki.source
                    self.log_operation("delete_source_check", f"Source {source.id} type: {source.source_type}")
                    
                    # Delete uploaded files (original files uploaded by user)
                    if hasattr(source, 'upload') and source.upload:
                        upload = source.upload
                        if upload.file:
                            source_files_to_delete.append(('uploaded_file', upload.file))
                            self.log_operation("delete_source_file", f"Queued uploaded file: {upload.file.name}")
                    
                    # Delete pasted text files
                    if hasattr(source, 'pasted_text_file') and source.pasted_text_file:
                        text_file = source.pasted_text_file
                        if text_file.file:
                            source_files_to_delete.append(('pasted_text_file', text_file.file))
                            self.log_operation("delete_source_file", f"Queued pasted text file: {text_file.file.name}")
                    
                    # Delete URL processing result files
                    if hasattr(source, 'url_result') and source.url_result:
                        url_result = source.url_result
                        if url_result.downloaded_file:
                            source_files_to_delete.append(('url_result_file', url_result.downloaded_file))
                            self.log_operation("delete_source_file", f"Queued URL result file: {url_result.downloaded_file.name}")
                else:
                    self.log_operation("delete_source_check", f"KnowledgeItem {ki.id} has no source - cannot delete original files")
            
            # Delete the knowledge base item's processed content file
            if kb_item.file:
                source_files_to_delete.append(('knowledge_base_file', kb_item.file))
                self.log_operation("delete_source_file", f"Queued knowledge base file: {kb_item.file.name}")
            
            # Now delete all collected files
            for file_type, file_field in source_files_to_delete:
                try:
                    file_field.delete(save=False)
                    self.log_operation("delete_source_file", f"Deleted {file_type}: {file_field.name}")
                except (FileNotFoundError, OSError) as e:
                    # File already gone, that's fine - log but continue
                    self.log_operation("delete_source_file", f"File already deleted {file_type}: {getattr(file_field, 'name', 'unknown')} - {str(e)}", "warning")
                except Exception as e:
                    # Log other errors but continue
                    self.log_operation("delete_source_file", f"Error deleting {file_type}: {getattr(file_field, 'name', 'unknown')} - {str(e)}", "error")
            
            # Delete the knowledge base item (this will cascade delete notebook links and sources)
            kb_item.delete()
            
            self.log_operation("delete_knowledge_item", f"kb_item_id={kb_item_id}, user_id={user_id}, deleted_files_count={len(source_files_to_delete)}")
            return True
            
        except Exception as e:
            self.log_operation("delete_knowledge_item_error", f"kb_item_id={kb_item_id}, user_id={user_id}, error={str(e)}", "error")
            return False
    
    def unlink_knowledge_item_from_notebook(self, kb_item_id: str, notebook_id: int, user_id: int) -> bool:
        """Remove a knowledge item link from a specific notebook without deleting the knowledge base item."""
        try:
            from ...models import KnowledgeItem, Notebook
            
            self.log_operation("unlink_knowledge_item", f"Starting unlink: kb_item_id={kb_item_id}, notebook_id={notebook_id}, user_id={user_id}")
            
            # Verify ownership
            notebook = Notebook.objects.filter(id=notebook_id, user_id=user_id).first()
            if not notebook:
                self.log_operation("unlink_knowledge_item_error", f"Notebook not found: notebook_id={notebook_id}, user_id={user_id}", "error")
                return False
            
            # Try to convert kb_item_id to int if it's a valid number
            try:
                kb_item_id_int = int(kb_item_id)
                self.log_operation("unlink_knowledge_item", f"Converted kb_item_id to int: {kb_item_id_int}")
            except (ValueError, TypeError):
                self.log_operation("unlink_knowledge_item_error", f"Invalid kb_item_id format: {kb_item_id} (expected integer)", "error")
                return False
            
            # Delete the link using the integer ID
            deleted_count, _ = KnowledgeItem.objects.filter(
                notebook=notebook,
                knowledge_base_item_id=kb_item_id_int
            ).delete()
            
            self.log_operation("unlink_knowledge_item", f"kb_item_id={kb_item_id}, notebook_id={notebook_id}, deleted={deleted_count > 0}, deleted_count={deleted_count}")
            return deleted_count > 0
            
        except Exception as e:
            self.log_operation("unlink_knowledge_item_error", f"kb_item_id={kb_item_id}, notebook_id={notebook_id}, error={str(e)}", "error")
            return False

    # Legacy methods for backward compatibility
    def get_file_by_upload_id(self, upload_file_id: str, user_id: int = None) -> Optional[Dict[str, Any]]:
        """Legacy method for upload file ID lookup."""
        # This could be used for migration or backward compatibility
        return None
    
    def delete_file_by_upload_id(self, upload_file_id: str, user_id: int) -> bool:
        """Legacy method for upload file deletion."""
        return False
    
    def delete_file(self, file_id: str, user_id: int) -> bool:
        """Legacy method - redirects to delete_knowledge_base_item."""
        return self.delete_knowledge_base_item(file_id, user_id)


# Global singleton instance to prevent repeated initialization
file_storage_service = FileStorageService() 