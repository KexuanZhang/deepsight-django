"""
Common view mixins and utilities for notebooks app.
"""

import logging
from typing import Dict, Any, Optional
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions, authentication

from ..models import Notebook, KnowledgeBaseItem, KnowledgeItem

logger = logging.getLogger(__name__)


class NotebookPermissionMixin:
    """Mixin to handle notebook ownership verification."""
    
    def get_user_notebook(self, notebook_id: int, user):
        """Get notebook owned by user or raise 404."""
        return get_object_or_404(Notebook, id=notebook_id, user=user)
    
    def verify_notebook_access(self, notebook_id: int, user) -> bool:
        """Verify user has access to notebook."""
        return Notebook.objects.filter(id=notebook_id, user=user).exists()


class KnowledgeBasePermissionMixin:
    """Mixin to handle knowledge base item ownership verification."""
    
    def get_user_kb_item(self, kb_item_id: str, user):
        """Get knowledge base item owned by user or raise 404."""
        return get_object_or_404(KnowledgeBaseItem, id=kb_item_id, user=user)
    
    def verify_kb_item_access(self, kb_item_id: str, user) -> bool:
        """Verify user has access to knowledge base item."""
        return KnowledgeBaseItem.objects.filter(id=kb_item_id, user=user).exists()


class StandardAPIView(APIView):
    """Base API view with common settings and error handling."""
    
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]
    
    def handle_exception(self, exc):
        """Enhanced exception handling with logging."""
        logger.error(f"API Exception in {self.__class__.__name__}: {str(exc)}", 
                    exc_info=True)
        return super().handle_exception(exc)
    
    def success_response(self, data: Any = None, status_code: int = status.HTTP_200_OK) -> Response:
        """Standardized success response."""
        return Response({"success": True, "data": data}, status=status_code)
    
    def error_response(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, 
                      details: Optional[Dict] = None) -> Response:
        """Standardized error response."""
        response_data = {"success": False, "error": message}
        if details:
            response_data["details"] = details
        return Response(response_data, status=status_code)


class FileMetadataExtractorMixin:
    """Mixin for extracting file metadata from knowledge base items."""
    
    def extract_original_filename(self, metadata: Dict, fallback_title: str) -> str:
        """Extract original filename from metadata, with fallback to title."""
        if not metadata:
            return fallback_title
        
        original_filename = (metadata.get('original_filename') or 
                           metadata.get('filename') or 
                           fallback_title)
        
        if original_filename and '.' not in original_filename:
            extension = metadata.get('file_extension', '')
            if extension and not extension.startswith('.'):
                extension = '.' + extension
            if extension:
                original_filename = original_filename + extension
        
        return original_filename
    
    def extract_file_extension(self, metadata: Dict) -> str:
        """Extract file extension from metadata."""
        if not metadata:
            return ""
        
        extension = metadata.get('file_extension', '')
        if not extension and 'original_filename' in metadata and '.' in metadata['original_filename']:
            extension = '.' + metadata['original_filename'].split('.')[-1]
        elif not extension and 'filename' in metadata and '.' in metadata['filename']:
            extension = '.' + metadata['filename'].split('.')[-1]
        
        return extension
    
    def extract_file_size(self, metadata: Dict) -> Optional[int]:
        """Extract file size from metadata."""
        if not metadata:
            return None
        
        return (metadata.get('file_size') or 
                metadata.get('content_length') or 
                None)


class FileAccessValidatorMixin:
    """Mixin for validating file access permissions."""
    
    def validate_notebook_file_access(self, notebook_id: int, file_id: str, user) -> tuple:
        """
        Validate user has access to file through notebook.
        Returns (notebook, kb_item, knowledge_item) or raises appropriate error.
        """
        notebook = get_object_or_404(Notebook, id=notebook_id, user=user)
        kb_item = get_object_or_404(KnowledgeBaseItem, id=file_id, user=user)
        
        knowledge_item = KnowledgeItem.objects.filter(
            notebook=notebook,
            knowledge_base_item=kb_item
        ).first()
        
        if not knowledge_item:
            logger.warning(f"User {user.id} attempted unauthorized access: "
                         f"notebook={notebook_id}, file={file_id}")
            raise Http404("File not linked to this notebook")
        
        return notebook, kb_item, knowledge_item


class PaginationMixin:
    """Mixin for handling pagination parameters."""
    
    def get_pagination_params(self, request) -> tuple:
        """Extract pagination parameters from request."""
        try:
            limit = int(request.GET.get('limit', 50))
            offset = int(request.GET.get('offset', 0))
            
            # Apply reasonable bounds
            limit = min(max(1, limit), 100)  # Between 1 and 100
            offset = max(0, offset)  # Non-negative
            
            return limit, offset
        except (ValueError, TypeError):
            return 50, 0  # Default values


class FileListResponseMixin(FileMetadataExtractorMixin):
    """Mixin for generating standardized file list responses."""
    
    def build_file_response_data(self, ki: KnowledgeItem) -> Dict[str, Any]:
        """Build standardized file response data from KnowledgeItem."""
        kb_item = ki.knowledge_base_item
        source = ki.source
        
        file_data = {
            "file_id": str(kb_item.id),
            "knowledge_item_id": ki.id,
            "title": kb_item.title,
            "content_type": kb_item.content_type,
            "tags": kb_item.tags,
            "created_at": kb_item.created_at.isoformat(),
            "updated_at": kb_item.updated_at.isoformat(),
            "added_to_notebook_at": ki.added_at.isoformat(),
            "notes": ki.notes,
            "metadata": kb_item.metadata or {},
            "has_file": bool(kb_item.file),
            "has_content": bool(kb_item.content),
            "has_original_file": bool(kb_item.original_file),
            "parsing_status": "completed",
            
            # Extract metadata
            "original_filename": self.extract_original_filename(
                kb_item.metadata, kb_item.title
            ),
            "file_extension": self.extract_file_extension(kb_item.metadata),
            "file_size": self.extract_file_size(kb_item.metadata),
            "uploaded_at": kb_item.created_at.isoformat(),
        }
        
        # Add source information if available
        if source:
            file_data.update({
                "source_id": source.id,
                "source_type": source.source_type,
                "source_title": source.title,
                "source_status": source.processing_status,
            })
            
            # Add source-specific metadata
            if source.source_type == "url" and hasattr(source, 'url_result'):
                url_result = source.url_result
                file_data.update({
                    "source_url": source.title,
                    "content_length": len(url_result.content_md) if url_result.content_md else 0,
                    "processing_method": "web_scraping",
                    "extraction_type": "url_extractor",
                })
                
                if url_result.downloaded_file:
                    file_data["downloaded_file_path"] = url_result.downloaded_file.name
                    file_data["downloaded_file_url"] = url_result.downloaded_file.url
            
            elif source.source_type == "text":
                file_data.update({
                    "original_filename": f"{source.title}.txt",
                    "file_extension": ".txt",
                })
        
        # Add knowledge base file URLs
        if kb_item.file:
            file_data.update({
                "knowledge_file_path": kb_item.file.name,
                "knowledge_file_url": kb_item.file.url,
            })
        
        if kb_item.original_file:
            file_data.update({
                "original_file_path": kb_item.original_file.name,
                "original_file_url": kb_item.original_file.url,
            })
        
        return file_data