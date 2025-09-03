"""
Enhanced Notebook Service following Django best practices.

Handles notebook business logic with proper validation, permissions,
and transaction management.
"""

import logging
from typing import Dict, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator

from core.services import ModelService, NotebookBaseService


class NotebookService(ModelService):
    """
    Service for notebook operations following Django patterns.
    
    Provides comprehensive notebook management with proper user
    permission checking, validation, and transaction management.
    """
    
    def __init__(self):
        from ..models import Notebook
        super().__init__(Notebook)
        self.logger = logging.getLogger(__name__)
    
    def perform_action(self, **kwargs):
        """
        Implementation of abstract method from BaseService.
        This service uses direct method calls rather than the template pattern.
        """
        # This method is required by BaseService but not used in this service
        # Individual methods handle their own transactions and validation
        pass
    
    def get_user_notebooks(self, user, with_stats: bool = False, 
                          filters: Dict = None, page: int = 1, 
                          page_size: int = 20):
        """
        Get notebooks for a user with optional filtering and pagination.
        
        Args:
            user: User to get notebooks for
            with_stats: Whether to include statistics (source/item counts)
            filters: Optional filters to apply
            page: Page number for pagination
            page_size: Number of items per page
            
        Returns:
            Dict with notebooks, pagination info, and metadata
        """
        # Start with user's notebooks
        queryset = self.model_class.objects.for_user(user)
        
        # Apply statistics if requested
        if with_stats:
            queryset = queryset.with_stats()
        
        # Apply filters
        if filters:
            if 'search' in filters and filters['search']:
                search_term = filters['search']
                queryset = queryset.filter(
                    models.Q(name__icontains=search_term) |
                    models.Q(description__icontains=search_term)
                )
            
            if 'has_content' in filters and filters['has_content']:
                queryset = queryset.active()
            
            if 'recent_activity' in filters:
                days = filters.get('recent_activity_days', 30)
                queryset = queryset.with_recent_activity(days)
        
        # Paginate results
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        self.log_operation(
            "notebooks_retrieved",
            user_id=user.id,
            total_count=paginator.count,
            page=page,
            filters=filters or {}
        )
        
        return {
            'notebooks': list(page_obj),
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            },
            'stats': {
                'total_notebooks': paginator.count,
                'active_notebooks': queryset.active().count() if not filters else None,
            }
        }
    
    @transaction.atomic
    def create_notebook(self, user, name: str, description: str = ""):
        """
        Create a new notebook with validation.
        
        Args:
            user: User who will own the notebook
            name: Name of the notebook
            description: Optional description
            
        Returns:
            Created Notebook instance
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate input
        if not name or not name.strip():
            raise ValidationError("Notebook name cannot be empty")
        
        # Check for duplicate names (case-insensitive)
        if self.model_class.objects.filter(
            user=user, 
            name__iexact=name.strip()
        ).exists():
            raise ValidationError("A notebook with this name already exists")
        
        # Create notebook
        notebook = self.model_class(
            user=user,
            name=name.strip(),
            description=description.strip() if description else ""
        )
        notebook.full_clean()
        notebook.save()
        
        # Create RagFlow dataset for the notebook
        try:
            from .ragflow_service import RagFlowService
            ragflow_service = RagFlowService()
            dataset_result = ragflow_service.create_dataset(notebook)
            
            if not dataset_result.get('success'):
                # If dataset creation fails, rollback notebook creation
                notebook.delete()
                error_msg = dataset_result.get('error', 'Failed to create RagFlow dataset')
                raise ValidationError(f"Failed to create notebook: {error_msg}")
            
            self.log_operation(
                "notebook_created_with_ragflow_dataset",
                notebook_id=str(notebook.id),
                user_id=user.id,
                name=notebook.name,
                ragflow_dataset_id=dataset_result.get('dataset_id'),
                ragflow_chat_id=dataset_result.get('chat_id')
            )
            
        except ValidationError:
            # Re-raise ValidationError to maintain the interface
            raise
        except Exception as e:
            # For any other error, rollback and raise ValidationError
            notebook.delete()
            self.logger.error(f"Failed to create RagFlow dataset for notebook {name}: {e}")
            raise ValidationError(f"Failed to create notebook: RagFlow service error")
        
        return notebook
    
    @transaction.atomic 
    def update_notebook(self, notebook_id: str, user, **updates):
        """
        Update a notebook with validation and permission checking.
        
        Args:
            notebook_id: ID of the notebook to update
            user: User who owns the notebook
            **updates: Fields to update
            
        Returns:
            Updated Notebook instance
            
        Raises:
            PermissionDenied: If user doesn't own the notebook
            ValidationError: If validation fails
        """
        # Get notebook with permission check
        notebook = self.get_object_for_user(notebook_id, user)
        
        # Apply updates
        updated_fields = []
        for field, value in updates.items():
            if hasattr(notebook, field) and field in ['name', 'description']:
                if field == 'name':
                    value = value.strip() if value else ""
                    if not value:
                        raise ValidationError("Notebook name cannot be empty")
                    
                    # Check for duplicate names (excluding current notebook)
                    if self.model_class.objects.filter(
                        user=user,
                        name__iexact=value
                    ).exclude(pk=notebook.pk).exists():
                        raise ValidationError("A notebook with this name already exists")
                
                elif field == 'description':
                    value = value.strip() if value else ""
                
                setattr(notebook, field, value)
                updated_fields.append(field)
        
        # Validate and save
        if updated_fields:
            notebook.full_clean()
            updated_fields.append('updated_at')
            notebook.save(update_fields=updated_fields)
            
            self.log_operation(
                "notebook_updated",
                notebook_id=notebook_id,
                user_id=user.id,
                updated_fields=updated_fields
            )
        
        return notebook
    
    @transaction.atomic
    def delete_notebook(self, notebook_id: str, user):
        """
        Delete a notebook with permission checking.
        
        Args:
            notebook_id: ID of the notebook to delete
            user: User who owns the notebook
            
        Returns:
            Dict with deletion statistics
            
        Raises:
            PermissionDenied: If user doesn't own the notebook
        """
        # Get notebook with permission check
        notebook = self.get_object_for_user(notebook_id, user)
        
        # Collect statistics before deletion
        stats = {
            'notebook_name': notebook.name,
            'knowledge_items_count': notebook.knowledge_base_items.count(),
            'chat_messages_count': notebook.chat_messages.count(),
            'batch_jobs_count': notebook.batch_jobs.count(),
        }
        
        # Delete RagFlow dataset if it exists
        ragflow_dataset_deleted = False
        ragflow_dataset_id = None
        if hasattr(notebook, 'ragflow_dataset'):
            try:
                from .ragflow_service import RagFlowService
                ragflow_service = RagFlowService()
                ragflow_dataset_id = notebook.ragflow_dataset.ragflow_dataset_id
                
                delete_result = ragflow_service.delete_dataset(notebook.ragflow_dataset)
                ragflow_dataset_deleted = delete_result.get('success', False)
                
                if not ragflow_dataset_deleted:
                    self.logger.warning(
                        f"Failed to delete RagFlow dataset {ragflow_dataset_id} "
                        f"for notebook {notebook_id}: {delete_result.get('error')}"
                    )
                else:
                    stats['ragflow_dataset_deleted'] = True
                    stats['ragflow_dataset_id'] = ragflow_dataset_id
                    
            except Exception as e:
                self.logger.error(
                    f"Error deleting RagFlow dataset for notebook {notebook_id}: {e}"
                )
                stats['ragflow_cleanup_error'] = str(e)
        
        # Delete notebook (cascade will handle related objects including RagFlowDataset)
        notebook.delete()
        
        self.log_operation(
            "notebook_deleted_with_ragflow_cleanup",
            notebook_id=notebook_id,
            user_id=user.id,
            ragflow_dataset_deleted=ragflow_dataset_deleted,
            ragflow_dataset_id=ragflow_dataset_id,
            **stats
        )
        
        return stats
    
    def get_notebook_stats(self, notebook_id: str, user):
        """
        Get comprehensive statistics for a notebook.
        
        Args:
            notebook_id: ID of the notebook
            user: User who owns the notebook
            
        Returns:
            Dict with notebook statistics
        """
        from django.db.models import Count, Q
        from django.utils import timezone
        from datetime import timedelta
        
        # Get notebook with permission check
        notebook = self.get_object_for_user(notebook_id, user)
        
        # Get processing status summary
        processing_status = notebook.get_processing_status_summary()
        
        # Get content type summary
        content_types = notebook.get_content_types_summary()
        
        # Get recent activity
        last_week = timezone.now() - timedelta(days=7)
        recent_items = notebook.knowledge_base_items.filter(
            created_at__gte=last_week
        ).count()
        recent_messages = notebook.chat_messages.filter(
            timestamp__gte=last_week
        ).count()
        
        stats = {
            'basic_info': {
                'name': notebook.name,
                'description': notebook.description,
                'created_at': notebook.created_at,
                'updated_at': notebook.updated_at,
            },
            'content_counts': {
                'knowledge_items': notebook.knowledge_base_items.count(),
                'chat_messages': notebook.chat_messages.count(),
                'batch_jobs': notebook.batch_jobs.count(),
                'images': notebook.knowledge_base_items.with_images().count(),
            },
            'processing_status': processing_status,
            'content_types': content_types,
            'recent_activity': {
                'items_last_week': recent_items,
                'messages_last_week': recent_messages,
            },
            'storage_info': {
                'has_processed_content': notebook.has_processed_content(),
                'items_with_files': notebook.knowledge_base_items.with_files().count(),
            }
        }
        
        self.log_operation(
            "notebook_stats_retrieved",
            notebook_id=notebook_id,
            user_id=user.id
        )
        
        return stats
    
    @transaction.atomic
    def duplicate_notebook(self, notebook_id: str, user, new_name: str):
        """
        Create a duplicate of an existing notebook.
        
        Args:
            notebook_id: ID of the notebook to duplicate
            user: User who owns the notebook
            new_name: Name for the new notebook
            
        Returns:
            New Notebook instance
        """
        # Get original notebook
        original = self.get_object_for_user(notebook_id, user)
        
        # Create duplicate notebook
        duplicate = self.create_notebook(
            user=user,
            name=new_name,
            description=f"Copy of {original.name}"
        )
        
        # Note: Knowledge items are not duplicated as they may reference
        # external storage. This would require a separate service method
        # to handle content duplication properly.
        
        self.log_operation(
            "notebook_duplicated",
            original_notebook_id=notebook_id,
            new_notebook_id=str(duplicate.id),
            user_id=user.id
        )
        
        return duplicate
    
    def cleanup_empty_notebooks(self, user, older_than_days: int = 30):
        """
        Clean up empty notebooks older than specified days.
        
        Args:
            user: User whose notebooks to clean up
            older_than_days: Delete notebooks older than this many days
            
        Returns:
            Number of notebooks deleted
        """
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=older_than_days)
        
        # Find empty notebooks older than cutoff
        empty_notebooks = self.model_class.objects.filter(
            user=user,
            created_at__lt=cutoff_date,
            knowledge_base_items__isnull=True
        ).distinct()
        
        count = empty_notebooks.count()
        if count > 0:
            notebook_names = list(empty_notebooks.values_list('name', flat=True))
            empty_notebooks.delete()
            
            self.log_operation(
                "empty_notebooks_cleaned",
                user_id=user.id,
                count=count,
                notebook_names=notebook_names
            )
        
        return count
    
    # RagFlow Integration Methods
    
    def get_notebook_dataset(self, notebook_id: str, user):
        """
        Get RagFlow dataset for a notebook.
        
        Args:
            notebook_id: ID of the notebook
            user: User who owns the notebook
            
        Returns:
            RagFlowDataset instance or None if not found
            
        Raises:
            PermissionDenied: If user doesn't own the notebook
        """
        notebook = self.get_object_for_user(notebook_id, user)
        return getattr(notebook, 'ragflow_dataset', None)
    
    def has_dataset(self, notebook_id: str, user) -> bool:
        """
        Check if notebook has an associated RagFlow dataset.
        
        Args:
            notebook_id: ID of the notebook
            user: User who owns the notebook
            
        Returns:
            True if dataset exists and is active
        """
        try:
            dataset = self.get_notebook_dataset(notebook_id, user)
            return dataset is not None and dataset.is_ready()
        except Exception:
            return False
    
    def get_dataset_status(self, notebook_id: str, user):
        """
        Get RagFlow dataset status for a notebook.
        
        Args:
            notebook_id: ID of the notebook
            user: User who owns the notebook
            
        Returns:
            Dict with dataset status information
        """
        try:
            dataset = self.get_notebook_dataset(notebook_id, user)
            if not dataset:
                return {
                    'has_dataset': False,
                    'status': 'not_created'
                }
            
            return {
                'has_dataset': True,
                'status': dataset.status,
                'dataset_id': dataset.ragflow_dataset_id,
                'dataset_name': dataset.dataset_name,
                'chat_id': dataset.ragflow_chat_id,
                'error_message': dataset.error_message if dataset.has_error() else None,
                'document_count': dataset.get_document_count(),
                'created_at': dataset.created_at,
                'updated_at': dataset.updated_at
            }
            
        except Exception as e:
            self.logger.exception(f"Failed to get dataset status for notebook {notebook_id}: {e}")
            return {
                'has_dataset': False,
                'status': 'error',
                'error': str(e)
            }