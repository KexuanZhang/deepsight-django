"""
Knowledge Base Service - Handle knowledge base operations following Django patterns.
"""
import logging
from typing import Dict, List, Optional
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from rest_framework import status

from ..models import KnowledgeBaseItem, BatchJob
from ..utils.storage import get_storage_adapter
from core.services import NotebookBaseService

logger = logging.getLogger(__name__)


class KnowledgeBaseService(NotebookBaseService):
    """Handle knowledge base operations business logic following Django patterns."""
    
    def __init__(self):
        super().__init__()
        self.storage_adapter = get_storage_adapter()
    
    def perform_action(self, **kwargs):
        """
        Implementation of abstract method from BaseService.
        This service uses direct method calls rather than the template pattern.
        """
        pass
    
    def get_user_knowledge_base(self, user_id: int, notebook, content_type: str = None, limit: int = None, offset: int = None) -> Dict:
        """
        Get knowledge base items for this specific notebook.
        
        Args:
            user_id: User ID
            notebook: Notebook instance
            content_type: Optional content type filter
            limit: Optional limit for pagination
            offset: Optional offset for pagination
            
        Returns:
            Dict with knowledge base items and metadata
        """
        # Validate notebook access
        self.validate_notebook_access(notebook, notebook.user)
        try:
            # Since knowledge base items are now notebook-specific, just get items for this notebook
            queryset = KnowledgeBaseItem.objects.filter(notebook=notebook)
            
            # Apply content type filter if specified
            if content_type:
                queryset = queryset.filter(content_type=content_type)
                
            # Apply pagination
            if offset:
                queryset = queryset[offset:]
            if limit:
                queryset = queryset[:limit]
                
            # Convert to dictionary format for API compatibility
            knowledge_base = []
            for kb_item in queryset.order_by('-created_at'):
                item_data = {
                    "id": str(kb_item.id),
                    "title": kb_item.title,
                    "content_type": kb_item.content_type,
                    "processing_status": kb_item.processing_status,
                    "metadata": kb_item.metadata or {},
                    "file_metadata": kb_item.file_metadata or {},
                    "created_at": kb_item.created_at.isoformat(),
                    "updated_at": kb_item.updated_at.isoformat(),
                    "linked_to_notebook": True,  # All items are now linked to the notebook
                    "notes": kb_item.notes,
                    "tags": kb_item.tags,
                }
                knowledge_base.append(item_data)

            return {
                "success": True,
                "items": knowledge_base,
                "notebook_id": notebook.id,
                "pagination": {"limit": limit, "offset": offset},
            }

        except Exception as e:
            self.logger.exception(f"Failed to retrieve knowledge base for user {user_id}: {e}")
            return {
                "error": "Failed to retrieve knowledge base",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    @transaction.atomic
    def link_knowledge_item_to_notebook(self, kb_item_id: str, notebook, user_id: int, notes: str = "") -> Dict:
        """
        Link a knowledge base item to a notebook.
        
        Args:
            kb_item_id: Knowledge base item ID
            notebook: Notebook instance
            user_id: User ID
            notes: Optional notes
            
        Returns:
            Dict with operation result
        """
        # Validate notebook access
        self.validate_notebook_access(notebook, notebook.user)
        try:
            # Link the item using storage adapter
            success = self.storage_adapter.link_knowledge_item_to_notebook(
                kb_item_id=kb_item_id,
                notebook_id=notebook.id,
                user_id=user_id,
                notes=notes,
            )

            if success:
                return {
                    "success": True,
                    "linked": True
                }
            else:
                return {
                    "error": "Failed to link knowledge item",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
                }

        except Exception as e:
            self.logger.exception(f"Failed to link KB item {kb_item_id} to notebook {notebook.id}: {e}")
            return {
                "error": "Link operation failed",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    @transaction.atomic
    def delete_knowledge_base_item(self, kb_item_id, user_id):
        """Delete a knowledge base item entirely from user's knowledge base"""
        try:
            # Delete the knowledge base item entirely
            success = self.storage_adapter.delete_knowledge_base_item(
                kb_item_id, user_id
            )

            if success:
                return {
                    "success": True,
                    "status_code": status.HTTP_204_NO_CONTENT
                }
            else:
                return {
                    "error": "Knowledge base item not found or access denied",
                    "status_code": status.HTTP_404_NOT_FOUND,
                }

        except Exception as e:
            logger.exception(f"Failed to delete KB item {kb_item_id} for user {user_id}: {e}")
            return {
                "error": "Delete operation failed",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    def get_knowledge_base_images(self, file_id, notebook):
        """Get all images for a knowledge base item"""
        try:
            # Get the knowledge base item from the notebook
            kb_item = get_object_or_404(KnowledgeBaseItem, id=file_id, notebook=notebook)
            
            # Get all images for this knowledge base item
            from ..models import KnowledgeBaseImage
            images = KnowledgeBaseImage.objects.filter(
                knowledge_base_item=kb_item
            ).order_by('created_at')
            
            # Serialize image data
            image_data = []
            for image in images:
                image_url = image.get_image_url(expires=3600)  # 1 hour
                if image_url:
                    # Get the original filename from metadata for display
                    original_filename = "unknown"
                    if image.image_metadata and 'original_filename' in image.image_metadata:
                        original_filename = image.image_metadata['original_filename']
                    
                    image_data.append({
                        'id': str(image.id),
                        'figure_id': str(image.figure_id),
                        'name': str(image.figure_id),  # Use figure_id as name for API compatibility
                        'image_caption': image.image_caption,
                        'image_url': image_url,
                        'imageUrl': image_url,  # Also include imageUrl for frontend compatibility
                        'content_type': image.content_type,
                        'file_size': image.file_size,
                        'created_at': image.created_at.isoformat(),
                        'original_filename': original_filename,
                    })
            
            return {
                "success": True,
                'images': image_data,
                'count': len(image_data),
                'knowledge_base_item_id': file_id,
            }
            
        except Exception as e:
            logger.exception(f"Failed to retrieve images for KB item {file_id}: {e}")
            return {
                "error": "Failed to retrieve images",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    def get_batch_job_status(self, batch_job_id, notebook):
        """Get status of a batch job"""
        try:
            # Get the batch job
            batch_job = get_object_or_404(BatchJob, id=batch_job_id, notebook=notebook)

            # Get batch job items
            from ..models import BatchJobItem
            items = BatchJobItem.objects.filter(batch_job=batch_job).order_by('created_at')

            # Serialize data
            items_data = []
            for item in items:
                items_data.append({
                    'id': str(item.id),
                    'item_data': item.item_data,
                    'upload_id': item.upload_id,
                    'status': item.status,
                    'result_data': item.result_data,
                    'error_message': item.error_message,
                    'created_at': item.created_at.isoformat(),
                    'updated_at': item.updated_at.isoformat(),
                })

            return {
                "success": True,
                'batch_job': {
                    'id': str(batch_job.id),
                    'job_type': batch_job.job_type,
                    'status': batch_job.status,
                    'total_items': batch_job.total_items,
                    'completed_items': batch_job.completed_items,
                    'failed_items': batch_job.failed_items,
                    'created_at': batch_job.created_at.isoformat(),
                    'updated_at': batch_job.updated_at.isoformat(),
                },
                'items': items_data,
            }

        except Exception as e:
            logger.exception(f"Failed to get batch job {batch_job_id} status: {e}")
            return {
                "error": "Failed to get batch job status",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            } 