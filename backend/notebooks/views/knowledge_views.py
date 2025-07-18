"""
Knowledge Base Views - Handle knowledge base item operations only
"""
import logging
from uuid import uuid4

from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response

from ..models import KnowledgeItem, KnowledgeBaseItem, BatchJob
from ..utils.view_mixins import (
    StandardAPIView, NotebookPermissionMixin, PaginationMixin
)
from ..utils.storage import get_storage_adapter
from ..services import KnowledgeBaseService

logger = logging.getLogger(__name__)

# Initialize storage adapter
storage_adapter = get_storage_adapter()


class KnowledgeBaseView(StandardAPIView, NotebookPermissionMixin, PaginationMixin):
    """Manage user's knowledge base items."""

    parser_classes = [JSONParser, MultiPartParser]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.knowledge_service = KnowledgeBaseService()

    def get(self, request, notebook_id):
        """Get user's entire knowledge base with linkage status."""
        # Verify notebook ownership
        notebook = self.get_user_notebook(notebook_id, request.user)

        # Get query parameters
        content_type = request.GET.get("content_type")
        limit, offset = self.get_pagination_params(request)

        # Use service to get knowledge base
        result = self.knowledge_service.get_user_knowledge_base(
            user_id=request.user.pk,
            notebook=notebook,
            content_type=content_type,
            limit=limit,
            offset=offset,
        )

        if result.get('success'):
            return self.success_response(result)
        else:
            return self.error_response(
                result['error'],
                status_code=result['status_code'],
                details=result.get('details', {}),
            )

    def post(self, request, notebook_id):
        """Link a knowledge base item to this notebook."""
        # Verify notebook ownership
        notebook = self.get_user_notebook(notebook_id, request.user)

        # Validate request data
        kb_item_id = request.data.get("knowledge_base_item_id")
        notes = request.data.get("notes", "")

        if not kb_item_id:
            return self.error_response("knowledge_base_item_id is required")

        # Use service to link item
        result = self.knowledge_service.link_knowledge_item_to_notebook(
            kb_item_id=kb_item_id,
            notebook=notebook,
            user_id=request.user.pk,
            notes=notes,
        )

        if result.get('success'):
            return self.success_response(result)
        else:
            return self.error_response(
                result['error'],
                status_code=result['status_code'],
                details=result.get('details', {}),
            )

    def delete(self, request, notebook_id):
        """Delete a knowledge base item entirely from user's knowledge base."""
        # Verify notebook ownership (for permission check)
        self.get_user_notebook(notebook_id, request.user)

        # Validate request data
        kb_item_id = request.data.get("knowledge_base_item_id")
        if not kb_item_id:
            return self.error_response("knowledge_base_item_id is required")

        # Use service to delete item
        result = self.knowledge_service.delete_knowledge_base_item(
            kb_item_id, request.user.pk
        )

        if result.get('success'):
            return Response(status=result['status_code'])
        else:
            return self.error_response(
                result['error'],
                status_code=result['status_code'],
                details=result.get('details', {}),
            )


class KnowledgeBaseImagesView(StandardAPIView, NotebookPermissionMixin):
    """Manage knowledge base images - REST API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.knowledge_service = KnowledgeBaseService()

    def get(self, request, notebook_id, file_id):
        """Get all images for a knowledge base item."""
        # Verify access through notebook
        notebook = self.get_user_notebook(notebook_id, request.user)
        
        # Use service to get images
        result = self.knowledge_service.get_knowledge_base_images(file_id, request.user)
        
        if result.get('success'):
            return self.success_response(result)
        else:
            return self.error_response(
                result['error'],
                status_code=result['status_code'],
                details=result.get('details', {}),
            ) 