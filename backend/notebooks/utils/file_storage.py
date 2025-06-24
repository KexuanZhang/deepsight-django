"""
File storage service for managing processed files and knowledge base.
"""

import json
import shutil
import os
import hashlib
import re
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, UTC
from django.conf import settings
from django.core.files.base import ContentFile

try:
    from .config import config as config_settings, storage_config
except ImportError:
    config_settings = None
    storage_config = None

class FileStorageService:
    """Service for storing and managing processed files in user knowledge base."""
    
    def __init__(self):
        self.service_name = "file_storage"
        self.logger = logging.getLogger(f"{__name__}.file_storage")
        
        # Use the new DeepSight data storage path
        self.base_data_root = Path(settings.MEDIA_ROOT)
        
        # Create base directory structure if it doesn't exist
        self.base_data_root.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"File storage service initialized with base path: {self.base_data_root}")
    
    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log service operations with consistent formatting."""
        message = f"[{self.service_name}] {operation}"
        if details:
            message += f": {details}"
        
        getattr(self.logger, level)(message)
    
    def _clean_filename(self, filename: str, max_length: int = 100) -> str:
        """
        Clean filename according to FilenameCleanup rules for cross-platform compatibility.
        
        Rules:
        - ASCII letters (A–Z, a–z), digits (0–9), hyphens (-), underscores (_), single period (.)
        - No null character, directory separators, Windows-forbidden symbols, whitespace
        - No names starting/ending with hyphens, underscores, periods, or whitespace
        - Length constraints: filename ≤ 255 characters; we use max_length for practical limits
        """
        if not filename:
            return "unnamed_file"
        
        # Split filename and extension
        name_parts = filename.rsplit('.', 1)
        basename = name_parts[0] if name_parts else filename
        extension = name_parts[1] if len(name_parts) > 1 else ""
        
        # Clean basename: replace invalid characters with underscores
        # Keep only ASCII letters, digits, hyphens, underscores
        basename_cleaned = re.sub(r'[^A-Za-z0-9_-]', '_', basename)
        
        # Remove leading/trailing hyphens, underscores, periods
        basename_cleaned = re.sub(r'^[_.-]+|[_.-]+$', '', basename_cleaned)
        
        # Ensure it doesn't start or end with invalid characters
        if not basename_cleaned or not re.match(r'^[A-Za-z0-9]', basename_cleaned):
            basename_cleaned = 'file_' + basename_cleaned
        
        # Ensure it doesn't end with invalid characters
        if not re.match(r'.*[A-Za-z0-9]$', basename_cleaned):
            basename_cleaned = basename_cleaned + '_file'
        
        # Clean extension similarly
        if extension:
            extension_cleaned = re.sub(r'[^A-Za-z0-9_-]', '', extension)
            if not extension_cleaned:
                extension_cleaned = 'bin'  # fallback for binary files
        else:
            extension_cleaned = ""
        
        # Check against Windows reserved names
        windows_reserved = {
            'CON', 'PRN', 'AUX', 'NUL', 
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        if basename_cleaned.upper() in windows_reserved:
            basename_cleaned = f"file_{basename_cleaned}"
        
        # Construct final filename
        if extension_cleaned:
            final_filename = f"{basename_cleaned}.{extension_cleaned}"
        else:
            final_filename = basename_cleaned
        
        # Enforce length constraint
        if len(final_filename) > max_length:
            # Truncate basename while preserving extension
            available_length = max_length - len(f".{extension_cleaned}") if extension_cleaned else max_length
            basename_truncated = basename_cleaned[:max(1, available_length)]
            final_filename = f"{basename_truncated}.{extension_cleaned}" if extension_cleaned else basename_truncated
        
        # Final validation with regex (simplified version of the full regex)
        if not re.match(r'^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9_-]+)?$', final_filename):
            # Fallback to a safe name
            timestamp = int(datetime.now().timestamp())
            final_filename = f"file_{timestamp}.{extension_cleaned}" if extension_cleaned else f"file_{timestamp}"
        
        return final_filename
    
    def _generate_knowledge_base_paths(self, user_id: int, original_filename: str, kb_item_id: str) -> Dict[str, str]:
        """
        Generate organized file paths for knowledge base storage.
        New structure: Users/u_user_id/knowledge_base_item/yyyy-mm/f_file_id/title.pdf
        Content: Users/u_user_id/knowledge_base_item/yyyy-mm/f_file_id/content/extracted_content.md
        
        Returns:
            {
                'base_dir': 'Users/u_user_X/knowledge_base_item/2025-06/f_file_id/',
                'original_file_path': 'Users/u_user_X/knowledge_base_item/2025-06/f_file_id/title.pdf',
                'content_dir': 'Users/u_user_X/knowledge_base_item/2025-06/f_file_id/content/',
                'content_file_path': 'Users/u_user_X/knowledge_base_item/2025-06/f_file_id/content/extracted_content.md'
            }
        """
        # Clean the filename
        cleaned_filename = self._clean_filename(original_filename)
        
        # Get current year-month for organization
        current_date = datetime.now()
        year_month = current_date.strftime('%Y-%m')
        
        # Build paths according to new structure with prefixed IDs
        base_dir = f"Users/u_{user_id}/knowledge_base_item/{year_month}/f_{kb_item_id}"
        content_dir = f"{base_dir}/content"
        
        return {
            'base_dir': base_dir,
            'original_file_path': f"{base_dir}/{cleaned_filename}",
            'content_dir': content_dir,
            'content_file_path': f"{content_dir}/extracted_content.md",
            'cleaned_filename': cleaned_filename,
            'year_month': year_month
        }
    
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
        source_id: Optional[int] = None,
        original_file_path: Optional[str] = None
    ) -> str:
        """Store processed file content in user's knowledge base with organized structure."""
        try:
            # Import here to avoid circular imports
            from ..models import KnowledgeBaseItem, KnowledgeItem, Notebook, Source
            
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
                return str(existing_item.id)
            
            # Create new knowledge base item (without files initially)
            title = self._generate_title_from_metadata(metadata)
            content_type = self._determine_content_type(metadata)
            
            # Create the knowledge base item
            kb_item = KnowledgeBaseItem.objects.create(
                user_id=user_id,
                title=title,
                content_type=content_type,
                content="",  # We'll store in organized file structure
                metadata=metadata,
                source_hash=content_hash,
                tags=self._extract_tags_from_metadata(metadata)
            )
            
            # Generate organized file paths
            original_filename = metadata.get('original_filename', metadata.get('filename', 'unknown_file'))
            paths = self._generate_knowledge_base_paths(user_id, original_filename, str(kb_item.id))
            
            # Ensure user directories exist
            if storage_config:
                storage_config.ensure_user_directories(user_id)
            
            # Create specific directories for this file
            base_dir = self.base_data_root / paths['base_dir']
            content_dir = self.base_data_root / paths['content_dir']
            
            base_dir.mkdir(parents=True, exist_ok=True)
            content_dir.mkdir(parents=True, exist_ok=True)
            
            # Store original file with cleaned name if provided
            if original_file_path and os.path.exists(original_file_path):
                self._save_organized_original_file(kb_item, original_file_path, paths)
            
            # Store extracted content in organized structure
            self._save_organized_content_file(kb_item, content, paths)
            
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
                notes=f"Processed from {original_filename}"
            )
            
            self.log_operation("store_knowledge_item", f"kb_item_id={kb_item.id}, user_id={user_id}, organized_structure=True")
            return str(kb_item.id)
            
        except Exception as e:
            self.log_operation("store_file_error", str(e), "error")
            raise
    
    def _save_organized_original_file(self, kb_item: 'KnowledgeBaseItem', original_file_path: str, paths: Dict[str, str]):
        """Save the original binary file in organized structure."""
        try:
            # Read the original file and save it with cleaned filename
            with open(original_file_path, 'rb') as f:
                content_file = ContentFile(f.read())
                kb_item.original_file.save(paths['original_file_path'], content_file, save=True)
            
            self.log_operation("save_organized_original_file", f"Saved original file: {paths['original_file_path']}")
            
        except Exception as e:
            self.log_operation("save_organized_original_file_error", f"kb_item_id={kb_item.id}, error={str(e)}", "error")
    
    def _save_organized_content_file(self, kb_item: 'KnowledgeBaseItem', content: str, paths: Dict[str, str]):
        """Save the extracted content in organized structure."""
        try:
            # Save content in the content subdirectory
            content_file = ContentFile(content.encode('utf-8'))
            kb_item.file.save(paths['content_file_path'], content_file, save=True)
            
            self.log_operation("save_organized_content_file", f"Saved content file: {paths['content_file_path']}")
            
        except Exception as e:
            self.log_operation("save_organized_content_file_error", f"kb_item_id={kb_item.id}, error={str(e)}", "error")
    
    def _delete_organized_structure(self, kb_item: 'KnowledgeBaseItem', user_id: int):
        """Delete the entire organized directory structure for a knowledge base item."""
        try:
            # Try to determine the organized directory from the file paths
            if kb_item.original_file or kb_item.file:
                # Get the directory path from either original_file or file
                file_path = None
                if kb_item.original_file:
                    file_path = kb_item.original_file.name
                elif kb_item.file:
                    file_path = kb_item.file.name
                
                if file_path:
                    # Extract the base directory (should be like Users/u_user_id/knowledge_base_item/yyyy-mm/f_file_id/)
                    path_parts = Path(file_path).parts
                    
                    # Look for pattern: Users/u_user_id/knowledge_base_item/yyyy-mm/f_file_id/
                    if (len(path_parts) >= 5 and 
                        path_parts[0] == 'Users' and 
                        path_parts[2] == 'knowledge_base_item' and 
                        f"u_{user_id}" in path_parts[1]):
                        
                        base_dir = self.base_data_root / path_parts[0] / path_parts[1] / path_parts[2] / path_parts[3] / path_parts[4]
                        
                        if base_dir.exists() and base_dir.is_dir():
                            # Safety check: ensure it's the right user and contains our kb_item_id
                            if f"u_{user_id}" in str(base_dir) and f"f_{kb_item.id}" in str(base_dir):
                                shutil.rmtree(base_dir)
                                self.log_operation("delete_organized_structure", f"Deleted directory: {base_dir}")
                            else:
                                self.log_operation("delete_organized_structure_skip", f"Safety check failed for: {base_dir}")
            
        except Exception as e:
            self.log_operation("delete_organized_structure_error", f"kb_item_id={kb_item.id}, error={str(e)}", "error")
    

    
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
            from ..models import KnowledgeBaseItem
            
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
            from ..models import KnowledgeBaseItem
            
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
                    'has_original_file': bool(item.original_file),
                    'metadata': item.metadata or {}
                })
            
            return result
        except Exception as e:
            self.log_operation("get_knowledge_base_error", f"user_id={user_id}, error={str(e)}", "error")
            return []
    
    def link_knowledge_item_to_notebook(self, kb_item_id: str, notebook_id: int, user_id: int, notes: str = "") -> bool:
        """Link an existing knowledge base item to a notebook."""
        try:
            from ..models import KnowledgeBaseItem, KnowledgeItem, Notebook
            
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
        """Delete a knowledge base item and its organized directory structure."""
        try:
            from ..models import KnowledgeBaseItem
            
            kb_item = KnowledgeBaseItem.objects.filter(id=kb_item_id, user_id=user_id).first()
            if not kb_item:
                return False
            
            # Delete the entire organized directory structure
            # This will remove both the original file and content files
            self._delete_organized_structure(kb_item, user_id)
            
            # Delete the knowledge base item (this will cascade delete notebook links)
            kb_item.delete()
            
            self.log_operation("delete_knowledge_item", f"kb_item_id={kb_item_id}, user_id={user_id}, organized_structure_deleted=True")
            return True
            
        except Exception as e:
            self.log_operation("delete_knowledge_item_error", f"kb_item_id={kb_item_id}, user_id={user_id}, error={str(e)}", "error")
            return False
    
    def unlink_knowledge_item_from_notebook(self, kb_item_id: str, notebook_id: int, user_id: int) -> bool:
        """Remove a knowledge item link from a specific notebook without deleting the knowledge base item."""
        try:
            from ..models import KnowledgeItem, Notebook
            
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




# Global singleton instance to prevent repeated initialization
file_storage_service = FileStorageService() 