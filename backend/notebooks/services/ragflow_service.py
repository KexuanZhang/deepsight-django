"""
RagFlow Service - Handle RagFlow operations following Django patterns.
"""

import logging
from typing import Dict, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import status

from ..models import Notebook, RagFlowDataset, KnowledgeBaseItem
from infrastructure.ragflow.client import get_ragflow_client, RagFlowClientError
from core.services import NotebookBaseService

logger = logging.getLogger(__name__)


class RagFlowService(NotebookBaseService):
    """Handle RagFlow operations business logic following Django patterns."""
    
    def __init__(self):
        super().__init__()
        self.ragflow_client = get_ragflow_client()
    
    def perform_action(self, **kwargs):
        """
        Implementation of abstract method from BaseService.
        This service uses direct method calls rather than the template pattern.
        """
        # This method is required by BaseService but not used in this service
        # Individual methods handle their own transactions and validation
        pass
    
    @transaction.atomic
    def create_dataset(self, notebook: Notebook, name: str = None) -> Dict:
        """
        Create RagFlow dataset for notebook.
        
        Args:
            notebook: Notebook instance
            name: Optional custom dataset name (defaults to generated name)
            
        Returns:
            Dict with dataset creation result
        """
        try:
            # Validate notebook
            self.validate_notebook_access(notebook, notebook.user)
            
            # Check if dataset already exists
            if hasattr(notebook, 'ragflow_dataset'):
                return {
                    "error": "Dataset already exists for this notebook",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "dataset_id": notebook.ragflow_dataset.ragflow_dataset_id
                }
            
            # Generate dataset name if not provided
            if not name:
                name = RagFlowDataset.generate_dataset_name(notebook)
            
            # Create RagFlow dataset via client
            ragflow_dataset_info = self.ragflow_client.create_dataset(
                name=name,
                description=f"Dataset for notebook: {notebook.name}"
            )
            
            # Create local RagFlowDataset record
            ragflow_dataset = RagFlowDataset.objects.create(
                notebook=notebook,
                ragflow_dataset_id=ragflow_dataset_info['id'],
                dataset_name=name,
                status='creating'
            )
            
            # Create chat assistant for the dataset
            try:
                chat_info = self.ragflow_client.create_chat_assistant(
                    dataset_ids=[ragflow_dataset_info['id']],
                    name=f"Assistant for {notebook.name}"
                )
                ragflow_dataset.ragflow_chat_id = chat_info['id']
                ragflow_dataset.mark_active()
                
                self.log_notebook_operation(
                    "ragflow_dataset_created",
                    str(notebook.id),
                    notebook.user.id,
                    ragflow_dataset_id=ragflow_dataset_info['id'],
                    chat_id=chat_info['id']
                )
                
            except Exception as chat_error:
                logger.warning(f"Failed to create chat assistant for dataset {ragflow_dataset_info['id']}: {chat_error}")
                ragflow_dataset.mark_active()  # Still mark as active, chat can be created later
            
            return {
                "success": True,
                "dataset_id": ragflow_dataset_info['id'],
                "local_dataset_id": ragflow_dataset.id,
                "chat_id": ragflow_dataset.ragflow_chat_id,
                "name": name
            }
            
        except RagFlowClientError as e:
            logger.exception(f"RagFlow client error creating dataset for notebook {notebook.id}: {e}")
            return {
                "error": f"Failed to create RagFlow dataset: {e}",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"ragflow_error": str(e)}
            }
        except Exception as e:
            logger.exception(f"Failed to create dataset for notebook {notebook.id}: {e}")
            return {
                "error": "Failed to create dataset",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    @transaction.atomic
    def delete_dataset(self, ragflow_dataset: RagFlowDataset) -> Dict:
        """
        Delete RagFlow dataset.
        
        Args:
            ragflow_dataset: RagFlowDataset instance to delete
            
        Returns:
            Dict with deletion result
        """
        try:
            ragflow_dataset.mark_deleting()
            
            # Delete chat assistant if exists
            if ragflow_dataset.ragflow_chat_id:
                try:
                    self.ragflow_client.delete_chat_assistant(ragflow_dataset.ragflow_chat_id)
                except Exception as e:
                    logger.warning(f"Failed to delete chat assistant {ragflow_dataset.ragflow_chat_id}: {e}")
            
            # Delete RagFlow dataset
            self.ragflow_client.delete_dataset(ragflow_dataset.ragflow_dataset_id)
            
            # Delete local record
            notebook_id = ragflow_dataset.notebook.id
            user_id = ragflow_dataset.notebook.user.id
            ragflow_dataset.delete()
            
            self.log_notebook_operation(
                "ragflow_dataset_deleted",
                str(notebook_id),
                user_id,
                ragflow_dataset_id=ragflow_dataset.ragflow_dataset_id
            )
            
            return {
                "success": True,
                "status_code": status.HTTP_204_NO_CONTENT
            }
            
        except RagFlowClientError as e:
            logger.exception(f"RagFlow client error deleting dataset {ragflow_dataset.ragflow_dataset_id}: {e}")
            ragflow_dataset.mark_error(f"Failed to delete: {e}")
            return {
                "error": f"Failed to delete RagFlow dataset: {e}",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"ragflow_error": str(e)}
            }
        except Exception as e:
            logger.exception(f"Failed to delete dataset {ragflow_dataset.ragflow_dataset_id}: {e}")
            ragflow_dataset.mark_error(f"Failed to delete: {e}")
            return {
                "error": "Failed to delete dataset",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def upload_knowledge_item_content(self, knowledge_item: KnowledgeBaseItem) -> Dict:
        """
        Upload KnowledgeBaseItem content to RagFlow dataset.
        
        Args:
            knowledge_item: KnowledgeBaseItem instance to upload
            
        Returns:
            Dict with upload result
        """
        try:
            # Validate knowledge item has content
            if not knowledge_item.has_content():
                return {
                    "error": "Knowledge item has no content to upload",
                    "status_code": status.HTTP_400_BAD_REQUEST
                }
            
            # Get notebook's RagFlow dataset
            if not hasattr(knowledge_item.notebook, 'ragflow_dataset'):
                return {
                    "error": "Notebook has no RagFlow dataset",
                    "status_code": status.HTTP_400_BAD_REQUEST
                }
            
            ragflow_dataset = knowledge_item.notebook.ragflow_dataset
            if not ragflow_dataset.is_ready():
                return {
                    "error": "RagFlow dataset is not ready",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "dataset_status": ragflow_dataset.status
                }
            
            # Mark as uploading
            knowledge_item.mark_ragflow_uploading()
            
            # Get content to upload
            content = knowledge_item.content
            if not content and knowledge_item.file_object_key:
                # Try to get content from storage
                try:
                    from infrastructure.storage.adapters import get_storage_adapter
                    storage = get_storage_adapter()
                    content = storage.get_file_content(knowledge_item.file_object_key)
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                except Exception as e:
                    logger.warning(f"Failed to get content from storage for {knowledge_item.id}: {e}")
            
            if not content:
                knowledge_item.mark_ragflow_failed("No content available for upload")
                return {
                    "error": "No content available for upload",
                    "status_code": status.HTTP_400_BAD_REQUEST
                }
            
            # Upload to RagFlow
            upload_result = self.ragflow_client.upload_document(
                dataset_id=ragflow_dataset.ragflow_dataset_id,
                content=content,
                display_name=f"{knowledge_item.title}_{knowledge_item.id}",
                content_type="text/markdown"
            )
            
            # Mark as parsing (RagFlow will handle the parsing)
            knowledge_item.mark_ragflow_parsing()
            
            # Trigger parsing
            self.ragflow_client.parse_documents(
                dataset_id=ragflow_dataset.ragflow_dataset_id,
                document_ids=[upload_result['id']]
            )
            
            # Mark as completed with document ID
            knowledge_item.mark_ragflow_completed(upload_result['id'])
            
            self.log_notebook_operation(
                "knowledge_item_uploaded_to_ragflow",
                str(knowledge_item.notebook.id),
                knowledge_item.notebook.user.id,
                knowledge_item_id=str(knowledge_item.id),
                ragflow_document_id=upload_result['id']
            )
            
            return {
                "success": True,
                "ragflow_document_id": upload_result['id'],
                "status": "uploaded"
            }
            
        except RagFlowClientError as e:
            logger.exception(f"RagFlow client error uploading knowledge item {knowledge_item.id}: {e}")
            knowledge_item.mark_ragflow_failed(str(e))
            return {
                "error": f"Failed to upload to RagFlow: {e}",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"ragflow_error": str(e)}
            }
        except Exception as e:
            logger.exception(f"Failed to upload knowledge item {knowledge_item.id}: {e}")
            knowledge_item.mark_ragflow_failed(str(e))
            return {
                "error": "Failed to upload content",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def delete_document(self, knowledge_item: KnowledgeBaseItem) -> Dict:
        """
        Delete document from RagFlow dataset.
        
        Args:
            knowledge_item: KnowledgeBaseItem instance with RagFlow document
            
        Returns:
            Dict with deletion result
        """
        try:
            if not knowledge_item.is_uploaded_to_ragflow():
                return {
                    "error": "Knowledge item is not uploaded to RagFlow",
                    "status_code": status.HTTP_400_BAD_REQUEST
                }
            
            # Get notebook's RagFlow dataset
            ragflow_dataset = knowledge_item.notebook.ragflow_dataset
            
            # Delete from RagFlow
            self.ragflow_client.delete_document(
                dataset_id=ragflow_dataset.ragflow_dataset_id,
                document_id=knowledge_item.ragflow_document_id
            )
            
            # Clear RagFlow fields
            knowledge_item.ragflow_document_id = ""
            knowledge_item.ragflow_processing_status = "pending"
            knowledge_item.save(update_fields=['ragflow_document_id', 'ragflow_processing_status', 'updated_at'])
            
            self.log_notebook_operation(
                "knowledge_item_deleted_from_ragflow",
                str(knowledge_item.notebook.id),
                knowledge_item.notebook.user.id,
                knowledge_item_id=str(knowledge_item.id)
            )
            
            return {
                "success": True,
                "status_code": status.HTTP_204_NO_CONTENT
            }
            
        except RagFlowClientError as e:
            logger.exception(f"RagFlow client error deleting document for knowledge item {knowledge_item.id}: {e}")
            return {
                "error": f"Failed to delete from RagFlow: {e}",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"ragflow_error": str(e)}
            }
        except Exception as e:
            logger.exception(f"Failed to delete document for knowledge item {knowledge_item.id}: {e}")
            return {
                "error": "Failed to delete document",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def get_document_status(self, knowledge_item: KnowledgeBaseItem) -> Dict:
        """
        Get RagFlow document processing status.
        
        Args:
            knowledge_item: KnowledgeBaseItem instance
            
        Returns:
            Dict with status information
        """
        try:
            if not knowledge_item.is_uploaded_to_ragflow():
                return {
                    "success": True,
                    "status": "not_uploaded",
                    "local_status": knowledge_item.ragflow_processing_status
                }
            
            # Get notebook's RagFlow dataset
            ragflow_dataset = knowledge_item.notebook.ragflow_dataset
            
            # Get status from RagFlow
            status_info = self.ragflow_client.get_document_status(
                dataset_id=ragflow_dataset.ragflow_dataset_id,
                document_id=knowledge_item.ragflow_document_id
            )
            
            if status_info:
                return {
                    "success": True,
                    "status": status_info.get('status', 'unknown'),
                    "local_status": knowledge_item.ragflow_processing_status,
                    "ragflow_info": status_info
                }
            else:
                return {
                    "success": True,
                    "status": "not_found",
                    "local_status": knowledge_item.ragflow_processing_status
                }
            
        except Exception as e:
            logger.exception(f"Failed to get document status for knowledge item {knowledge_item.id}: {e}")
            return {
                "error": "Failed to get document status",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def query_dataset(self, notebook: Notebook, query: str, limit: int = 10) -> Dict:
        """
        Query RagFlow dataset for relevant content.
        
        Args:
            notebook: Notebook instance
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Dict with query results
        """
        try:
            # Get notebook's RagFlow dataset
            if not hasattr(notebook, 'ragflow_dataset'):
                return {
                    "error": "Notebook has no RagFlow dataset",
                    "status_code": status.HTTP_400_BAD_REQUEST
                }
            
            ragflow_dataset = notebook.ragflow_dataset
            if not ragflow_dataset.is_ready():
                return {
                    "error": "RagFlow dataset is not ready",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "dataset_status": ragflow_dataset.status
                }
            
            # Query via RagFlow client
            # Note: This would use RagFlow's retrieval API when available
            # For now, we return a placeholder structure
            
            return {
                "success": True,
                "query": query,
                "results": [],  # Would contain actual search results
                "dataset_id": ragflow_dataset.ragflow_dataset_id
            }
            
        except Exception as e:
            logger.exception(f"Failed to query dataset for notebook {notebook.id}: {e}")
            return {
                "error": "Failed to query dataset",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def health_check(self) -> Dict:
        """
        Check RagFlow service health.
        
        Returns:
            Dict with health status
        """
        try:
            is_healthy = self.ragflow_client.health_check()
            return {
                "healthy": is_healthy,
                "service": "ragflow"
            }
        except Exception as e:
            logger.exception(f"RagFlow health check failed: {e}")
            return {
                "healthy": False,
                "service": "ragflow",
                "error": str(e)
            }