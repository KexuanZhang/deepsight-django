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

from ..models import Notebook, KnowledgeBaseItem

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

    def get_notebook_kb_item(self, kb_item_id: str, notebook):
        """Get knowledge base item from specific notebook or raise 404."""
        return get_object_or_404(KnowledgeBaseItem, id=kb_item_id, notebook=notebook)

    def verify_kb_item_access(self, kb_item_id: str, notebook) -> bool:
        """Verify knowledge base item exists in the specified notebook."""
        return KnowledgeBaseItem.objects.filter(id=kb_item_id, notebook=notebook).exists()

    # Legacy method for backward compatibility
    def get_user_kb_item(self, kb_item_id: str, user):
        """Legacy method - knowledge base items are now notebook-specific."""
        # This method is deprecated since knowledge base items are now notebook-specific
        # Kept for backward compatibility but will require notebook context
        raise NotImplementedError("Use get_notebook_kb_item with notebook parameter instead")


class StandardAPIView(APIView):
    """Base API view with common settings and error handling."""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def handle_exception(self, exc):
        """Enhanced exception handling with logging."""
        logger.error(
            f"API Exception in {self.__class__.__name__}: {str(exc)}", exc_info=True
        )
        return super().handle_exception(exc)

    def success_response(
        self, data: Any = None, status_code: int = status.HTTP_200_OK
    ) -> Response:
        """Standardized success response."""
        return Response({"success": True, "data": data}, status=status_code)

    def error_response(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict] = None,
    ) -> Response:
        """Standardized error response."""
        response_data = {"success": False, "error": message}
        if details:
            response_data["details"] = details
        return Response(response_data, status=status_code)


class FileAccessValidatorMixin:
    """Mixin for validating file access permissions."""

    def validate_notebook_file_access(
        self, notebook_id: int, file_id: str, user
    ) -> tuple:
        """
        Validate user has access to file through notebook.
        Returns (notebook, kb_item) or raises appropriate error.
        """
        notebook = get_object_or_404(Notebook, id=notebook_id, user=user)
        kb_item = get_object_or_404(KnowledgeBaseItem, id=file_id, notebook=notebook)

        return notebook, kb_item


class PaginationMixin:
    """Mixin for handling pagination parameters."""

    def get_pagination_params(self, request) -> tuple:
        """Extract pagination parameters from request."""
        try:
            limit = int(request.GET.get("limit", 50))
            offset = int(request.GET.get("offset", 0))

            # Apply reasonable bounds
            limit = min(max(1, limit), 100)  # Between 1 and 100
            offset = max(0, offset)  # Non-negative

            return limit, offset
        except (ValueError, TypeError):
            return 50, 0  # Default values


class FileMetadataExtractorMixin:
    """Mixin for extracting metadata from file objects."""

    def extract_original_filename(self, metadata: Dict, fallback_title: str) -> str:
        """Extract original filename from metadata."""
        if metadata:
            # Try different metadata keys
            for key in ["original_filename", "filename", "name"]:
                if key in metadata and metadata[key]:
                    return metadata[key]
        return fallback_title

    def extract_file_extension(self, metadata: Dict) -> Optional[str]:
        """Extract file extension from metadata."""
        if metadata and "file_extension" in metadata:
            return metadata["file_extension"]
        return None

    def extract_file_size(self, metadata: Dict) -> Optional[int]:
        """Extract file size from metadata."""
        if metadata and "file_size" in metadata:
            try:
                return int(metadata["file_size"])
            except (ValueError, TypeError):
                pass
        return None


class FileListResponseMixin(FileMetadataExtractorMixin):
    """Mixin for generating standardized file list responses."""

    def build_file_response_data(self, kb_item: KnowledgeBaseItem) -> Dict[str, Any]:
        """Build standardized file response data from KnowledgeBaseItem."""

        # Determine parsing status based on processing_status and content availability
        parsing_status = "completed"  # Default for completed items
        if hasattr(kb_item, 'processing_status'):
            if kb_item.processing_status == "in_progress":
                parsing_status = "in_progress"  # Keep original status name
            elif kb_item.processing_status == "error":
                parsing_status = "error"
            elif kb_item.processing_status == "pending":
                parsing_status = "pending"
            elif kb_item.processing_status == "done":
                parsing_status = "completed"  # Map "done" to "completed" for frontend

        # Combine metadata and file_metadata for frontend compatibility
        combined_metadata = {**(kb_item.metadata or {})}
        if kb_item.file_metadata:
            combined_metadata['file_metadata'] = kb_item.file_metadata
            
        file_data = {
            "file_id": str(kb_item.id),
            "title": kb_item.title,
            "content_type": kb_item.content_type,
            "tags": kb_item.tags,
            "created_at": kb_item.created_at.isoformat(),
            "updated_at": kb_item.updated_at.isoformat(),
            "notes": kb_item.notes,
            "metadata": combined_metadata,
            "has_file": bool(kb_item.file_object_key),
            "has_content": bool(kb_item.content),
            "has_original_file": bool(kb_item.original_file_object_key),
            "parsing_status": parsing_status,
            "processing_status": getattr(kb_item, 'processing_status', 'done'),
            # Extract metadata from knowledge base item
            "original_filename": self.extract_original_filename(
                kb_item.metadata, kb_item.title
            ),
            "file_extension": self.extract_file_extension(kb_item.metadata),
            "file_size": self.extract_file_size(kb_item.metadata),
            "uploaded_at": kb_item.created_at.isoformat(),
        }

        return file_data