"""
Django signals for cross-app communication and event handling.

Provides centralized event handling for:
- Model lifecycle events (create, update, delete)
- User authentication events
- File processing events
- Cache invalidation events
- Audit logging events
"""

import logging
from typing import Any, Dict, Type
from django.db.models.signals import post_save, post_delete, pre_save, pre_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.core.cache import cache
from django.dispatch import receiver, Signal
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models

logger = logging.getLogger(__name__)
User = get_user_model()

# Custom signals
notebook_created = Signal()
notebook_updated = Signal()
notebook_deleted = Signal()
file_uploaded = Signal()
file_processed = Signal()
file_processing_failed = Signal()
chat_message_sent = Signal()
batch_job_completed = Signal()


class SignalHandlers:
    """Centralized signal handlers for the application."""
    
    @staticmethod
    @receiver(post_save, sender=User)
    def handle_user_created(sender: Type[User], instance: User, created: bool, **kwargs):
        """Handle user creation events."""
        if created:
            logger.info(f"New user created: {instance.username} (ID: {instance.id})")
            
            # Initialize user-specific resources
            try:
                # Legacy Milvus initialization removed - now using RagFlow per-notebook datasets
                logger.info(f"User {instance.id} created - RagFlow datasets will be created per notebook")
                
            except Exception as e:
                logger.exception(f"Failed to initialize user resources for {instance.id}: {e}")
    
    @staticmethod
    @receiver(user_logged_in)
    def handle_user_login(sender: Type[User], request, user: User, **kwargs):
        """Handle successful user login."""
        client_ip = SignalHandlers._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
        logger.info(
            f"User logged in: {user.username} (ID: {user.id}) "
            f"from IP: {client_ip}, User-Agent: {user_agent}"
        )
        
        # Update last login tracking
        cache.set(f"last_login:{user.id}", timezone.now(), timeout=86400 * 30)  # 30 days
        
        # Clear any login failure counts
        cache.delete(f"login_failures:{client_ip}")
    
    @staticmethod
    @receiver(user_logged_out)
    def handle_user_logout(sender: Type[User], request, user: User, **kwargs):
        """Handle user logout."""
        if user:
            client_ip = SignalHandlers._get_client_ip(request)
            logger.info(f"User logged out: {user.username} (ID: {user.id}) from IP: {client_ip}")
    
    @staticmethod
    @receiver(user_login_failed)
    def handle_login_failed(sender: Type[User], credentials: Dict, request, **kwargs):
        """Handle failed login attempts."""
        client_ip = SignalHandlers._get_client_ip(request)
        username = credentials.get('username', 'unknown')
        
        logger.warning(f"Login failed for username: {username} from IP: {client_ip}")
        
        # Track login failures for rate limiting
        failure_key = f"login_failures:{client_ip}"
        current_failures = cache.get(failure_key, 0)
        cache.set(failure_key, current_failures + 1, timeout=3600)  # 1 hour
        
        # Log potential brute force attempts
        if current_failures >= 5:
            logger.critical(
                f"Potential brute force attack detected: {current_failures + 1} "
                f"failed attempts from IP: {client_ip}"
            )
    
    @staticmethod
    @receiver(notebook_created)
    def handle_notebook_created(sender, notebook, user, **kwargs):
        """Handle notebook creation events."""
        logger.info(f"Notebook created: {notebook.name} (ID: {notebook.id}) by user {user.id}")
        
        # Invalidate user's notebook list cache
        cache.delete(f"user_notebooks:{user.id}")
        
        # Initialize notebook-specific resources if needed
        try:
            # Any notebook initialization logic would go here
            pass
        except Exception as e:
            logger.exception(f"Failed to initialize notebook resources for {notebook.id}: {e}")
    
    @staticmethod
    @receiver(notebook_updated)
    def handle_notebook_updated(sender, notebook, user, updated_fields=None, **kwargs):
        """Handle notebook update events."""
        logger.info(
            f"Notebook updated: {notebook.name} (ID: {notebook.id}) "
            f"by user {user.id}, fields: {updated_fields}"
        )
        
        # Invalidate related caches
        cache.delete(f"user_notebooks:{user.id}")
        cache.delete(f"notebook_stats:{notebook.id}")
    
    @staticmethod
    @receiver(notebook_deleted)
    def handle_notebook_deleted(sender, notebook_id, user, **kwargs):
        """Handle notebook deletion events."""
        logger.info(f"Notebook deleted: ID {notebook_id} by user {user.id}")
        
        # Cleanup related caches
        cache.delete(f"user_notebooks:{user.id}")
        cache.delete(f"notebook_stats:{notebook_id}")
        
        # Cleanup related resources
        try:
            # Any cleanup logic would go here
            pass
        except Exception as e:
            logger.exception(f"Failed to cleanup resources for deleted notebook {notebook_id}: {e}")
    
    @staticmethod
    @receiver(file_uploaded)
    def handle_file_uploaded(sender, file_item, user, **kwargs):
        """Handle file upload events."""
        logger.info(
            f"File uploaded: {file_item.title} (ID: {file_item.id}) "
            f"to notebook {file_item.notebook.id} by user {user.id}"
        )
        
        # Invalidate notebook-related caches
        cache.delete(f"notebook_files:{file_item.notebook.id}")
        cache.delete(f"notebook_stats:{file_item.notebook.id}")
    
    @staticmethod
    @receiver(file_processed)
    def handle_file_processed(sender, file_item, processing_result=None, **kwargs):
        """Handle successful file processing events."""
        logger.info(
            f"File processed successfully: {file_item.title} (ID: {file_item.id})"
        )
        
        # Invalidate related caches
        cache.delete(f"notebook_files:{file_item.notebook.id}")
        cache.delete(f"notebook_stats:{file_item.notebook.id}")
        cache.delete(f"file_content:{file_item.id}")
        
        # Update processing statistics
        try:
            stats_key = f"processing_stats:user:{file_item.notebook.user.id}"
            current_stats = cache.get(stats_key, {'processed': 0, 'failed': 0})
            current_stats['processed'] += 1
            cache.set(stats_key, current_stats, timeout=86400 * 7)  # 7 days
        except Exception as e:
            logger.exception(f"Failed to update processing stats: {e}")
    
    @staticmethod
    @receiver(file_processing_failed)
    def handle_file_processing_failed(sender, file_item, error_message=None, **kwargs):
        """Handle failed file processing events."""
        logger.warning(
            f"File processing failed: {file_item.title} (ID: {file_item.id}), "
            f"error: {error_message}"
        )
        
        # Invalidate related caches
        cache.delete(f"notebook_files:{file_item.notebook.id}")
        cache.delete(f"notebook_stats:{file_item.notebook.id}")
        
        # Update processing statistics
        try:
            stats_key = f"processing_stats:user:{file_item.notebook.user.id}"
            current_stats = cache.get(stats_key, {'processed': 0, 'failed': 0})
            current_stats['failed'] += 1
            cache.set(stats_key, current_stats, timeout=86400 * 7)  # 7 days
        except Exception as e:
            logger.exception(f"Failed to update processing stats: {e}")
    
    @staticmethod
    @receiver(chat_message_sent)
    def handle_chat_message_sent(sender, message, notebook, user, **kwargs):
        """Handle chat message events."""
        logger.info(
            f"Chat message sent in notebook {notebook.id} by user {user.id}, "
            f"sender: {message.sender}, length: {len(message.message)}"
        )
        
        # Invalidate chat-related caches
        cache.delete(f"chat_history:{notebook.id}")
        cache.delete(f"notebook_stats:{notebook.id}")
        
        # Update chat activity metrics
        try:
            activity_key = f"chat_activity:user:{user.id}"
            current_count = cache.get(activity_key, 0)
            cache.set(activity_key, current_count + 1, timeout=86400)  # 24 hours
        except Exception as e:
            logger.exception(f"Failed to update chat activity metrics: {e}")
    
    @staticmethod
    @receiver(batch_job_completed)
    def handle_batch_job_completed(sender, batch_job, **kwargs):
        """Handle batch job completion events."""
        logger.info(
            f"Batch job completed: {batch_job.job_type} (ID: {batch_job.id}) "
            f"for notebook {batch_job.notebook.id}, status: {batch_job.status}"
        )
        
        # Invalidate related caches
        cache.delete(f"batch_jobs:{batch_job.notebook.id}")
        cache.delete(f"notebook_stats:{batch_job.notebook.id}")
        
        # Update batch processing metrics
        try:
            metrics_key = f"batch_metrics:user:{batch_job.notebook.user.id}"
            current_metrics = cache.get(metrics_key, {})
            
            if batch_job.job_type not in current_metrics:
                current_metrics[batch_job.job_type] = {'completed': 0, 'failed': 0}
            
            if batch_job.status == 'completed':
                current_metrics[batch_job.job_type]['completed'] += 1
            else:
                current_metrics[batch_job.job_type]['failed'] += 1
            
            cache.set(metrics_key, current_metrics, timeout=86400 * 7)  # 7 days
        except Exception as e:
            logger.exception(f"Failed to update batch processing metrics: {e}")
    
    @staticmethod
    def _get_client_ip(request) -> str:
        """Get the client's IP address from request."""
        if not request:
            return 'unknown'
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip


# Model-specific signal handlers using dynamic imports to avoid circular dependencies
@receiver(post_save)
def generic_model_post_save(sender, instance, created, **kwargs):
    """Generic post-save handler for cache invalidation."""
    model_name = sender._meta.label_lower
    
    # Invalidate model-specific caches
    if hasattr(instance, 'id'):
        cache.delete(f"{model_name}:{instance.id}")
    
    # Invalidate list caches
    cache.delete(f"{model_name}_list")
    
    # Handle specific models
    if model_name == 'notebooks.notebook':
        if created:
            notebook_created.send(sender=sender, notebook=instance, user=instance.user)
        else:
            notebook_updated.send(sender=sender, notebook=instance, user=instance.user)
    
    elif model_name == 'notebooks.knowledgebaseitem':
        if created:
            file_uploaded.send(sender=sender, file_item=instance, user=instance.notebook.user)
    
    elif model_name == 'notebooks.notebookchatmessage':
        if created:
            chat_message_sent.send(
                sender=sender, 
                message=instance, 
                notebook=instance.notebook,
                user=instance.notebook.user
            )


@receiver(post_delete)
def generic_model_post_delete(sender, instance, **kwargs):
    """Generic post-delete handler for cache invalidation."""
    model_name = sender._meta.label_lower
    
    # Invalidate model-specific caches
    if hasattr(instance, 'id'):
        cache.delete(f"{model_name}:{instance.id}")
    
    # Invalidate list caches
    cache.delete(f"{model_name}_list")
    
    # Handle specific models
    if model_name == 'notebooks.notebook':
        notebook_deleted.send(
            sender=sender, 
            notebook_id=str(instance.id), 
            user=instance.user
        )


class AuditLogHandler:
    """Handler for audit logging of important model changes."""
    
    @staticmethod
    @receiver(pre_save)
    def log_model_changes(sender, instance, **kwargs):
        """Log important model changes for auditing."""
        # Only audit specific models
        audit_models = [
            'notebooks.notebook',
            'notebooks.knowledgebaseitem', 
            'users.user'
        ]
        
        model_name = sender._meta.label_lower
        if model_name not in audit_models:
            return
        
        # Get old instance for comparison
        if hasattr(instance, 'id') and instance.id:
            try:
                old_instance = sender.objects.get(id=instance.id)
                changes = AuditLogHandler._detect_changes(old_instance, instance)
                
                if changes:
                    logger.info(
                        f"Model audit: {model_name} (ID: {instance.id}) changed: {changes}"
                    )
            except sender.DoesNotExist:
                # This is a new instance
                logger.info(f"Model audit: New {model_name} being created")
    
    @staticmethod
    def _detect_changes(old_instance, new_instance) -> Dict[str, Any]:
        """Detect changes between old and new instance."""
        changes = {}
        
        # Get model fields
        fields = [f.name for f in new_instance._meta.fields]
        
        for field in fields:
            # Skip certain fields
            if field in ['updated_at', 'last_login']:
                continue
            
            old_value = getattr(old_instance, field, None)
            new_value = getattr(new_instance, field, None)
            
            if old_value != new_value:
                # Don't log sensitive data
                if 'password' in field.lower() or 'token' in field.lower():
                    changes[field] = '[REDACTED]'
                else:
                    changes[field] = {'from': old_value, 'to': new_value}
        
        return changes


# Initialize signal handlers
def init_signals():
    """Initialize all signal handlers."""
    logger.info("Initializing Django signals...")
    
    # Signal handlers are automatically connected via decorators
    # This function can be used for any additional initialization
    
    logger.info("Django signals initialized successfully")