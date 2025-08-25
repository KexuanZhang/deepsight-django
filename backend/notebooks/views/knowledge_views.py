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

from ..models import KnowledgeBaseItem, BatchJob
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
        """Get notebook's knowledge base items directly."""
        try:
            # Verify notebook ownership
            notebook = self.get_user_notebook(notebook_id, request.user)

            # Get query parameters
            content_type = request.GET.get("content_type")
            limit, offset = self.get_pagination_params(request)

            # Get knowledge base items directly from notebook
            knowledge_base = storage_adapter.get_notebook_knowledge_items(
                notebook_id=notebook_id,
                content_type=content_type,
                limit=limit,
                offset=offset,
            )

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
        """Create a new knowledge base item directly in this notebook."""
        try:
            # Verify notebook ownership
            notebook = self.get_user_notebook(notebook_id, request.user)

            # This endpoint is now mainly used by file upload pipeline
            # Most creation will happen automatically during file processing
            return self.error_response(
                "Knowledge base items are created automatically during file processing",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return self.error_response(
                "Operation failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )

    def delete(self, request, notebook_id):
        """Delete a knowledge base item from this notebook."""
        try:
            # Verify notebook ownership
            notebook = self.get_user_notebook(notebook_id, request.user)

            # Validate request data
            kb_item_id = request.data.get("knowledge_base_item_id")
            if not kb_item_id:
                return self.error_response("knowledge_base_item_id is required")

            # Delete the knowledge base item from this notebook
            success = storage_adapter.delete_notebook_knowledge_item(
                notebook_id=notebook_id,
                kb_item_id=kb_item_id
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