"""
Base service classes for the DeepSight application.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from django.core.exceptions import ValidationError
from django.db import transaction


class BaseService(ABC):
    """
    Django-compatible base service following Single Responsibility Principle.
    
    This class establishes patterns for:
    - Logging
    - Transaction management
    - Input validation
    - Error handling
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__module__)
    
    @transaction.atomic
    def execute(self, **kwargs) -> Any:
        """
        Template method pattern with Django transaction management.
        
        This method ensures all service operations are executed within
        a database transaction and includes proper validation.
        """
        self.validate_input(**kwargs)
        return self.perform_action(**kwargs)
    
    def validate_input(self, **kwargs) -> None:
        """
        Override in subclasses for input validation.
        
        Should raise ValidationError for invalid inputs.
        """
        pass
    
    @abstractmethod
    def perform_action(self, **kwargs) -> Any:
        """
        Override in subclasses for main business logic.
        
        This method should contain the core business logic
        for the service operation.
        """
        pass
    
    def log_operation(self, operation: str, **kwargs) -> None:
        """
        Consistent logging across all services.
        
        Args:
            operation: Description of the operation
            **kwargs: Additional context for logging
        """
        # Filter out reserved LogRecord fields to avoid conflicts
        reserved_fields = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
            'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
            'thread', 'threadName', 'processName', 'process', 'getMessage', 'exc_info',
            'exc_text', 'stack_info', 'message'
        }
        
        # Create safe extra dict by prefixing custom fields
        safe_extra = {}
        for key, value in kwargs.items():
            if key in reserved_fields:
                # Prefix reserved field names to avoid conflicts
                safe_extra[f'ctx_{key}'] = value
            else:
                safe_extra[key] = value
        
        self.logger.info(f"[{self.__class__.__name__}] {operation}", extra=safe_extra)
    
    def log_error(self, error: str, exception: Exception = None, **kwargs) -> None:
        """
        Log errors with consistent formatting.
        
        Args:
            error: Error description
            exception: The exception that occurred
            **kwargs: Additional context for logging
        """
        # Same reserved fields filtering as log_operation
        reserved_fields = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
            'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
            'thread', 'threadName', 'processName', 'process', 'getMessage', 'exc_info',
            'exc_text', 'stack_info', 'message'
        }
        
        # Create safe extra dict
        safe_extra = {}
        for key, value in kwargs.items():
            if key in reserved_fields:
                safe_extra[f'ctx_{key}'] = value
            else:
                safe_extra[key] = value
        
        if exception:
            safe_extra['exception_type'] = type(exception).__name__
            safe_extra['exception_message'] = str(exception)
        
        self.logger.error(f"[{self.__class__.__name__}] {error}", extra=safe_extra)


class ModelService(BaseService):
    """
    Base service for operations on Django models.
    
    Provides common patterns for CRUD operations with proper
    permission checking and validation.
    """
    
    def __init__(self, model_class):
        super().__init__()
        self.model_class = model_class
    
    def get_object_for_user(self, object_id: str, user, **filters):
        """
        Get an object that belongs to the specified user.
        
        Args:
            object_id: ID of the object
            user: User who should own the object
            **filters: Additional filters to apply
            
        Returns:
            Model instance
            
        Raises:
            Model.DoesNotExist: If object not found or doesn't belong to user
        """
        filters.update({'id': object_id, 'user': user})
        return self.model_class.objects.get(**filters)
    
    def create_for_user(self, user, **data):
        """
        Create a new object for the specified user.
        
        Args:
            user: User who will own the object
            **data: Data for creating the object
            
        Returns:
            Created model instance
        """
        data['user'] = user
        instance = self.model_class(**data)
        instance.full_clean()  # Django model validation
        instance.save()
        
        self.log_operation(
            "object_created",
            model=self.model_class.__name__,
            object_id=str(instance.id),
            user_id=user.id
        )
        
        return instance
    
    def update_for_user(self, object_id: str, user, **updates):
        """
        Update an object that belongs to the specified user.
        
        Args:
            object_id: ID of the object to update
            user: User who owns the object
            **updates: Fields to update
            
        Returns:
            Updated model instance
            
        Raises:
            Model.DoesNotExist: If object not found or doesn't belong to user
        """
        instance = self.get_object_for_user(object_id, user)
        
        for field, value in updates.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        
        instance.full_clean()  # Django model validation
        instance.save()
        
        self.log_operation(
            "object_updated",
            model=self.model_class.__name__,
            object_id=str(instance.id),
            user_id=user.id,
            fields=list(updates.keys())
        )
        
        return instance


class AsyncService(BaseService):
    """
    Base service for asynchronous operations using Celery.
    
    Provides patterns for managing background tasks and
    tracking their progress.
    """
    
    def __init__(self):
        super().__init__()
        self.task_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
    
    def start_async_task(self, task_function, *args, **kwargs):
        """
        Start an asynchronous task using Celery.
        
        Args:
            task_function: Celery task function to execute
            *args: Arguments for the task
            **kwargs: Keyword arguments for the task
            
        Returns:
            Task ID for tracking
        """
        from celery import current_app
        
        task = task_function.delay(*args, **kwargs)
        
        self.log_operation(
            "async_task_started",
            task_id=task.id,
            task_name=self.task_name
        )
        
        return task.id
    
    def get_task_status(self, task_id: str):
        """
        Get the status of an async task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dict with task status information
        """
        from celery import current_app
        
        result = current_app.AsyncResult(task_id)
        
        return {
            'task_id': task_id,
            'status': result.status,
            'result': result.result if result.ready() else None,
            'info': result.info
        }


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
        from django.core.exceptions import PermissionDenied
        
        # Import here to avoid circular imports
        from notebooks.models import Notebook
        
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
        from django.core.exceptions import PermissionDenied
        
        if notebook.user != user:
            raise PermissionDenied("Access denied to this notebook")
    
    def log_notebook_operation(self, operation: str, notebook_id: str, user_id: int, **kwargs):
        """
        Log notebook-specific operations.
        
        Args:
            operation: Operation description
            notebook_id: Notebook ID
            user_id: User ID
            **kwargs: Additional context
        """
        self.log_operation(
            operation,
            notebook_id=notebook_id,
            user_id=user_id,
            **kwargs
        )
    
    def perform_action(self, **kwargs):
        """
        Default implementation - services can override if needed.
        """
        pass