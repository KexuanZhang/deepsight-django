"""
Knowledge Base Views - Handle knowledge base item operations only
"""
import logging
from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.http import Http404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response

from ..models import KnowledgeItem, KnowledgeBaseItem, BatchJob
from ..utils.view_mixins import (
    StandardAPIView, NotebookPermissionMixin, PaginationMixin, FileAccessValidatorMixin
)
from ..utils.storage import get_storage_adapter
from ..services import KnowledgeBaseService

logger = logging.getLogger(__name__)

# Initialize storage adapter
storage_adapter = get_storage_adapter()


class KnowledgeBaseView(StandardAPIView, NotebookPermissionMixin, PaginationMixin):
    """Manage user's knowledge base items."""

    parser_classes = [JSONParser, MultiPartParser]

    def get(self, request, notebook_id):
        """Get user's entire knowledge base with linkage status."""
        try:
            # Verify notebook ownership
            notebook = self.get_user_notebook(notebook_id, request.user)

            # Get query parameters
            content_type = request.GET.get("content_type")
            limit, offset = self.get_pagination_params(request)

            # Get knowledge base items
            knowledge_base = storage_adapter.get_user_knowledge_base(
                user_id=request.user.pk,
                content_type=content_type,
                limit=limit,
                offset=offset,
            )

            # Check which items are already linked to this notebook
            linked_kb_item_ids = set(
                KnowledgeItem.objects.filter(notebook=notebook).values_list(
                    "knowledge_base_item_id", flat=True
                )
            )

            # Add linked status to each item
            for item in knowledge_base:
                item["linked_to_notebook"] = item["id"] in linked_kb_item_ids

            return self.success_response(
                {
                    "items": knowledge_base,
                    "notebook_id": notebook_id,
                    "pagination": {"limit": limit, "offset": offset},
                }
            )

        except Exception as e:
            return self.error_response(
                "Failed to retrieve knowledge base",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )

    def post(self, request, notebook_id):
        """Link a knowledge base item to this notebook."""
        try:
            # Verify notebook ownership
            notebook = self.get_user_notebook(notebook_id, request.user)

            # Validate request data
            kb_item_id = request.data.get("knowledge_base_item_id")
            notes = request.data.get("notes", "")

            if not kb_item_id:
                return self.error_response("knowledge_base_item_id is required")

            # Link the item
            success = storage_adapter.link_knowledge_item_to_notebook(
                kb_item_id=kb_item_id,
                notebook_id=notebook_id,
                user_id=request.user.pk,
                notes=notes,
            )

            if success:
                return self.success_response({"linked": True})
            else:
                return self.error_response("Failed to link knowledge item")

        except Exception as e:
            return self.error_response(
                "Link operation failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )

    def delete(self, request, notebook_id):
        """Delete a knowledge base item entirely from user's knowledge base."""
        try:
            # Verify notebook ownership (for permission check)
            self.get_user_notebook(notebook_id, request.user)

            # Validate request data
            kb_item_id = request.data.get("knowledge_base_item_id")
            if not kb_item_id:
                return self.error_response("knowledge_base_item_id is required")

            # Delete the knowledge base item entirely
            success = storage_adapter.delete_knowledge_base_item(
                kb_item_id, request.user.pk
            )

            if success:
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return self.error_response(
                    "Knowledge base item not found or access denied",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            return self.error_response(
                "Delete operation failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )


class KnowledgeBaseImagesView(StandardAPIView, NotebookPermissionMixin, FileAccessValidatorMixin):
    """REST API endpoint for querying KnowledgeBaseImage records."""

    @swagger_auto_schema(
        operation_description="Get images for a knowledge base item",
        responses={
            200: openapi.Response(
                description="List of images for the knowledge base item",
                examples={
                    "application/json": {
                        "images": [
                            {
                                "id": "uuid",
                                "image_caption": "Sample caption",
                                "image_url": "https://...",
                                "minio_object_key": "...",
                                "content_type": "image/jpeg",
                                "file_size": 12345,
                                "created_at": "2025-01-01T12:00:00Z"
                            }
                        ],
                        "count": 1
                    }
                }
            ),
            404: openapi.Response(description="Knowledge base item not found"),
        },
        manual_parameters=[
            openapi.Parameter(
                'notebook_id',
                openapi.IN_PATH,
                description="ID of the notebook",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'file_id',
                openapi.IN_PATH,
                description="ID of the knowledge base item",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ]
    )
    def get(self, request, notebook_id, file_id):
        """Get all images for a knowledge base item."""
        try:
            # Validate access
            notebook, kb_item, _ = self.validate_notebook_file_access(
                notebook_id, file_id, request.user
            )
            
            # Query images
            from ..models import KnowledgeBaseImage
            from ..serializers import KnowledgeBaseImageSerializer
            
            images = KnowledgeBaseImage.objects.filter(
                knowledge_base_item=kb_item
            ).order_by('created_at')
            
            # Serialize data
            serializer = KnowledgeBaseImageSerializer(images, many=True)
            
            return Response({
                "images": serializer.data,
                "count": len(serializer.data),
                "file_id": file_id,
                "notebook_id": notebook_id
            }, status=status.HTTP_200_OK)
            
        except PermissionDenied as e:
            return self.error_response(str(e), status_code=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return self.error_response(str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return self.error_response(
                "Failed to retrieve images",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)}
            ) 