"""
Enhanced Django service base classes for notebooks app.

This module extends the core service classes with notebook-specific
functionality while maintaining Django best practices.
"""

import logging
from typing import Any, Dict, List, Optional, Type
from django.db import models, transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model

# Import from our core service base
from core.services import BaseService, ModelService, AsyncService
from core.exceptions import ProcessingError, ValidationError as CustomValidationError

User = get_user_model()


class NotebookBaseService(BaseService):
    """
    Base service for notebook-related operations.
    
    Provides common patterns for notebook-scoped operations with
    proper user permission checking and validation.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__module__)
    
    def get_user_notebook(self, notebook_id: str, user):
        """
        Get a notebook that belongs to the specified user.
        
        Args:
            notebook_id: ID of the notebook
            user: User who should own the notebook
            
        Returns:
            Notebook instance
            
        Raises:
            PermissionDenied: If notebook not found or doesn't belong to user
        """
        from ..models import Notebook
        
        try:
            return Notebook.objects.get(id=notebook_id, user=user)
        except Notebook.DoesNotExist:
            raise PermissionDenied("Notebook not found or access denied")
    
    def validate_notebook_access(self, notebook, user):
        """
        Validate that user has access to the notebook.
        
        Args:
            notebook: Notebook instance
            user: User to check access for
            
        Raises:
            PermissionDenied: If user doesn't have access
        """
        if notebook.user != user:
            raise PermissionDenied("Access denied to notebook")
    
    def log_notebook_operation(self, operation: str, notebook_id: str, 
                             user_id: int, **kwargs):
        """
        Log notebook-specific operations with consistent formatting.
        
        Args:
            operation: Description of the operation
            notebook_id: ID of the notebook involved
            user_id: ID of the user performing the operation
            **kwargs: Additional context for logging
        """
        self.log_operation(
            operation,
            notebook_id=notebook_id,
            user_id=user_id,
            **kwargs
        )


class KnowledgeBaseService(ModelService):
    """
    Service for knowledge base item operations.
    
    Handles CRUD operations for knowledge base items with proper
    notebook scoping and user permission checks.
    """
    
    def __init__(self):
        from ..models import KnowledgeBaseItem
        super().__init__(KnowledgeBaseItem)
    
    def get_items_for_notebook(self, notebook_id: str, user, 
                              filters: Dict = None):
        """
        Get knowledge base items for a specific notebook.
        
        Args:
            notebook_id: ID of the notebook
            user: User who owns the notebook
            filters: Optional additional filters
            
        Returns:
            QuerySet of knowledge base items
        """
        # Validate notebook access
        from ..models import Notebook
        notebook = Notebook.objects.get(id=notebook_id, user=user)
        
        # Get items with optional filters
        queryset = self.model_class.objects.for_notebook(notebook)
        
        if filters:
            if 'status' in filters:
                if filters['status'] == 'processed':
                    queryset = queryset.processed()
                elif filters['status'] == 'processing':
                    queryset = queryset.processing()
                elif filters['status'] == 'failed':
                    queryset = queryset.failed()
            
            if 'content_type' in filters:
                queryset = queryset.by_content_type(filters['content_type'])
            
            if 'has_content' in filters and filters['has_content']:
                queryset = queryset.with_content()
            
            if 'search' in filters:
                queryset = queryset.search_content(filters['search'])
        
        return queryset
    
    def create_knowledge_item(self, notebook_id: str, user, **item_data):
        """
        Create a new knowledge base item.
        
        Args:
            notebook_id: ID of the notebook
            user: User who owns the notebook
            **item_data: Data for the knowledge base item
            
        Returns:
            Created KnowledgeBaseItem instance
        """
        # Validate notebook access
        from ..models import Notebook
        notebook = Notebook.objects.get(id=notebook_id, user=user)
        
        # Add notebook to item data
        item_data['notebook'] = notebook
        
        # Create the item
        item = self.model_class(**item_data)
        item.full_clean()
        item.save()
        
        self.log_operation(
            "knowledge_item_created",
            item_id=str(item.id),
            notebook_id=notebook_id,
            user_id=user.id
        )
        
        return item
    
    def update_processing_status(self, item_id: str, user, 
                               status: str, error_message: str = None):
        """
        Update the processing status of a knowledge base item.
        
        Args:
            item_id: ID of the knowledge base item
            user: User who owns the item
            status: New processing status
            error_message: Error message if status is 'failed'
        """
        item = self.model_class.objects.select_related('notebook').get(
            id=item_id, notebook__user=user
        )
        
        item.processing_status = status
        if error_message and status == 'failed':
            if not item.metadata:
                item.metadata = {}
            item.metadata['error_message'] = error_message
        
        item.save(update_fields=['processing_status', 'metadata', 'updated_at'])
        
        self.log_operation(
            "processing_status_updated",
            item_id=item_id,
            status=status,
            user_id=user.id
        )


class BatchProcessingService(NotebookBaseService):
    """
    Service for handling batch processing operations.
    
    Manages batch jobs and their individual items with proper
    status tracking and error handling.
    """
    
    @transaction.atomic
    def create_batch_job(self, notebook_id: str, user, job_type: str, 
                        items_data: List[Dict]):
        """
        Create a new batch processing job.
        
        Args:
            notebook_id: ID of the notebook
            user: User who owns the notebook
            job_type: Type of batch job
            items_data: List of item data dictionaries
            
        Returns:
            Created BatchJob instance
        """
        from ..models import BatchJob, BatchJobItem
        
        # Validate notebook access
        notebook = self.get_user_notebook(notebook_id, user)
        
        # Create batch job
        batch_job = BatchJob.objects.create(
            notebook=notebook,
            job_type=job_type,
            total_items=len(items_data)
        )
        
        # Create individual job items
        job_items = []
        for item_data in items_data:
            job_item = BatchJobItem(
                batch_job=batch_job,
                item_data=item_data
            )
            job_items.append(job_item)
        
        BatchJobItem.objects.bulk_create(job_items)
        
        self.log_notebook_operation(
            "batch_job_created",
            notebook_id,
            user.id,
            job_type=job_type,
            total_items=len(items_data)
        )
        
        return batch_job
    
    def update_job_item_status(self, item_id: str, status: str, 
                              result_data: Dict = None, 
                              error_message: str = None):
        """
        Update the status of a batch job item.
        
        Args:
            item_id: ID of the batch job item
            status: New status
            result_data: Result data if completed
            error_message: Error message if failed
        """
        from ..models import BatchJobItem
        
        item = BatchJobItem.objects.select_related('batch_job').get(id=item_id)
        
        item.status = status
        if result_data:
            item.result_data = result_data
        if error_message:
            item.error_message = error_message
        
        item.save()
        
        self.log_operation(
            "batch_item_status_updated",
            item_id=item_id,
            batch_job_id=str(item.batch_job.id),
            status=status
        )


class ChatService(NotebookBaseService):
    """
    Service for notebook chat operations.
    
    Handles chat message creation, retrieval, and management
    with proper notebook scoping.
    """
    
    def add_message(self, notebook_id: str, user, sender: str, 
                   message: str, metadata: Dict = None):
        """
        Add a new chat message to a notebook.
        
        Args:
            notebook_id: ID of the notebook
            user: User who owns the notebook
            sender: Who sent the message ('user' or 'assistant')
            message: Message content
            metadata: Optional metadata for the message
            
        Returns:
            Created NotebookChatMessage instance
        """
        from ..models import NotebookChatMessage
        
        # Validate notebook access
        notebook = self.get_user_notebook(notebook_id, user)
        
        # Create chat message
        chat_message = NotebookChatMessage.objects.create(
            notebook=notebook,
            sender=sender,
            message=message,
            metadata=metadata or {}
        )
        
        self.log_notebook_operation(
            "chat_message_added",
            notebook_id,
            user.id,
            sender=sender,
            message_length=len(message)
        )
        
        return chat_message
    
    def get_chat_history(self, notebook_id: str, user, limit: int = 50):
        """
        Get chat history for a notebook.
        
        Args:
            notebook_id: ID of the notebook
            user: User who owns the notebook
            limit: Maximum number of messages to return
            
        Returns:
            QuerySet of chat messages
        """
        # Validate notebook access
        notebook = self.get_user_notebook(notebook_id, user)
        
        return notebook.chat_messages.all()[:limit]
    
    def clear_chat_history(self, notebook_id: str, user):
        """
        Clear all chat messages for a notebook.
        
        Args:
            notebook_id: ID of the notebook
            user: User who owns the notebook
            
        Returns:
            Number of messages deleted
        """
        # Validate notebook access
        notebook = self.get_user_notebook(notebook_id, user)
        
        count, _ = notebook.chat_messages.all().delete()
        
        self.log_notebook_operation(
            "chat_history_cleared",
            notebook_id,
            user.id,
            messages_deleted=count
        )
        
        return count