"""
Knowledge Base Service - Handle knowledge base operations business logic
"""
import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status

from ..models import KnowledgeItem, KnowledgeBaseItem, BatchJob
from ..utils.storage import get_storage_adapter

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """Handle knowledge base operations business logic"""
    
    def __init__(self):
        self.storage_adapter = get_storage_adapter()
    
    def get_user_knowledge_base(self, user_id, notebook, content_type=None, limit=None, offset=None):
        """Get user's entire knowledge base with linkage status"""
        try:
            # Get knowledge base items
            knowledge_base = self.storage_adapter.get_user_knowledge_base(
                user_id=user_id,
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

            return {
                "success": True,
                "items": knowledge_base,
                "notebook_id": notebook.id,
                "pagination": {"limit": limit, "offset": offset},
            }

        except Exception as e:
            logger.exception(f"Failed to retrieve knowledge base for user {user_id}: {e}")
            return {
                "error": "Failed to retrieve knowledge base",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    @transaction.atomic
    def link_knowledge_item_to_notebook(self, kb_item_id, notebook, user_id, notes=""):
        """Link a knowledge base item to a notebook"""
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
            logger.exception(f"Failed to link KB item {kb_item_id} to notebook {notebook.id}: {e}")
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

    def get_knowledge_base_images(self, file_id, user):
        """Get all images for a knowledge base item"""
        try:
            # Get the knowledge base item
            kb_item = get_object_or_404(KnowledgeBaseItem, id=file_id, user=user)
            
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
                    image_data.append({
                        'id': str(image.id),
                        'figure_id': str(image.figure_id),
                        'image_caption': image.image_caption,
                        'image_url': image_url,
                        'content_type': image.content_type,
                        'file_size': image.file_size,
                        'created_at': image.created_at.isoformat(),
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