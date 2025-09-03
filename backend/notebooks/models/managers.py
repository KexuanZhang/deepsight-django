"""
Custom managers and querysets for notebooks models.

Following Django best practices for database query optimization
and common query patterns.
"""

import logging
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class NotebookQuerySet(models.QuerySet):
    """Custom queryset for notebook-related queries."""
    
    def for_user(self, user):
        """Filter notebooks for a specific user."""
        return self.filter(user=user)
    
    def with_stats(self):
        """Annotate notebooks with source and knowledge item counts."""
        return self.annotate(
            source_count=Count('sources', distinct=True),
            knowledge_item_count=Count('knowledge_base_items', distinct=True),
            chat_message_count=Count('chat_messages', distinct=True)
        )
    
    def with_recent_activity(self, days=30):
        """Filter notebooks with recent activity."""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return self.filter(
            Q(updated_at__gte=cutoff_date) |
            Q(knowledge_base_items__updated_at__gte=cutoff_date) |
            Q(chat_messages__timestamp__gte=cutoff_date)
        ).distinct()
    
    def active(self):
        """Filter notebooks that have content."""
        return self.filter(knowledge_base_items__isnull=False).distinct()


class NotebookManager(models.Manager):
    """Custom manager for Notebook model."""
    
    def get_queryset(self):
        return NotebookQuerySet(self.model, using=self._db)
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)
    
    def with_stats(self):
        return self.get_queryset().with_stats()
    
    def with_recent_activity(self, days=30):
        return self.get_queryset().with_recent_activity(days)
    
    def active(self):
        return self.get_queryset().active()


class KnowledgeBaseItemQuerySet(models.QuerySet):
    """Custom queryset for knowledge base item queries."""
    
    def for_notebook(self, notebook):
        """Filter items for a specific notebook."""
        return self.filter(notebook=notebook)
    
    def for_user(self, user):
        """Filter items for a specific user through notebook relationship."""
        return self.filter(notebook__user=user)
    
    def processed(self):
        """Filter only successfully processed items."""
        return self.filter(processing_status='done')
    
    def processing(self):
        """Filter items currently being processed."""
        return self.filter(processing_status__in=['processing', 'in_progress'])
    
    def failed(self):
        """Filter items that failed processing."""
        return self.filter(processing_status='failed')
    
    def with_content(self):
        """Filter items that have actual content."""
        return self.exclude(
            Q(content='') & Q(file_object_key__isnull=True)
        )
    
    def with_files(self):
        """Filter items that have file attachments."""
        return self.exclude(
            Q(file_object_key__isnull=True) & Q(original_file_object_key__isnull=True)
        )
    
    def by_content_type(self, content_type):
        """Filter by content type."""
        return self.filter(content_type=content_type)
    
    def search_content(self, query):
        """Simple text search in title and content."""
        return self.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query)
        )
    
    def recent(self, days=7):
        """Filter items created in the last N days."""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date)
    
    def with_images(self):
        """Filter items that have associated images."""
        return self.filter(images__isnull=False).distinct()


class KnowledgeBaseItemManager(models.Manager):
    """Enhanced manager for KnowledgeBaseItem model."""
    
    def get_queryset(self):
        return KnowledgeBaseItemQuerySet(self.model, using=self._db)
    
    def for_notebook(self, notebook):
        return self.get_queryset().for_notebook(notebook)
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)
    
    def processed(self):
        return self.get_queryset().processed()
    
    def processing(self):
        return self.get_queryset().processing()
    
    def failed(self):
        return self.get_queryset().failed()
    
    def with_content(self):
        return self.get_queryset().with_content()
    
    def with_files(self):
        return self.get_queryset().with_files()
    
    def by_content_type(self, content_type):
        return self.get_queryset().by_content_type(content_type)
    
    def search_content(self, query):
        return self.get_queryset().search_content(query)
    
    def recent(self, days=7):
        return self.get_queryset().recent(days)
    
    def with_images(self):
        return self.get_queryset().with_images()
    
    def bulk_update_status(self, item_ids, status):
        """Bulk update processing status for multiple items."""
        return self.filter(id__in=item_ids).update(
            processing_status=status,
            updated_at=timezone.now()
        )
    
    def get_content(self, item_id, user_id):
        """
        Get content for a knowledge base item with user verification.
        Maintained for backward compatibility.
        """
        try:
            from django.contrib.auth import get_user_model
            from ..utils.storage_adapter import get_storage_adapter
            
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            # Security: Find knowledge base item through user's notebooks
            item = self.select_related('notebook').get(
                id=item_id, 
                notebook__user=user
            )
            
            # Use storage adapter to get content
            storage_adapter = get_storage_adapter()
            content = storage_adapter.get_file_content(item_id, user_id=user_id)
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to get content for KB item {item_id}: {e}")
            return None


class BatchJobQuerySet(models.QuerySet):
    """Custom queryset for batch job queries."""
    
    def for_notebook(self, notebook):
        """Filter jobs for a specific notebook."""
        return self.filter(notebook=notebook)
    
    def for_user(self, user):
        """Filter jobs for a specific user through notebook relationship."""
        return self.filter(notebook__user=user)
    
    def by_status(self, status):
        """Filter jobs by status."""
        return self.filter(status=status)
    
    def by_type(self, job_type):
        """Filter jobs by type."""
        return self.filter(job_type=job_type)
    
    def active(self):
        """Filter active (pending or processing) jobs."""
        return self.filter(status__in=['pending', 'processing'])
    
    def completed(self):
        """Filter completed jobs."""
        return self.filter(status__in=['completed', 'partially_completed'])
    
    def failed(self):
        """Filter failed jobs."""
        return self.filter(status='failed')
    
    def recent(self, days=7):
        """Filter jobs created in the last N days."""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date)


class BatchJobManager(models.Manager):
    """Custom manager for BatchJob model."""
    
    def get_queryset(self):
        return BatchJobQuerySet(self.model, using=self._db)
    
    def for_notebook(self, notebook):
        return self.get_queryset().for_notebook(notebook)
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)
    
    def by_status(self, status):
        return self.get_queryset().by_status(status)
    
    def by_type(self, job_type):
        return self.get_queryset().by_type(job_type)
    
    def active(self):
        return self.get_queryset().active()
    
    def completed(self):
        return self.get_queryset().completed()
    
    def failed(self):
        return self.get_queryset().failed()
    
    def recent(self, days=7):
        return self.get_queryset().recent(days)