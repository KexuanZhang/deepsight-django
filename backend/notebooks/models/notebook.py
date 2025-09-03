"""
Notebook model for organizing user content and knowledge items.
"""

from django.db import models
from django.core.exceptions import ValidationError
from core.mixins import BaseModel, UserOwnedMixin
from .managers import NotebookManager


class Notebook(BaseModel, UserOwnedMixin):
    """
    User-created notebook for organizing sources and knowledge items.
    
    Each notebook belongs to a user and contains multiple knowledge base items
    that are processed from various sources (files, URLs, text).
    """
    
    name = models.CharField(
        max_length=255,
        help_text="Name of the notebook"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the notebook's purpose"
    )
    
    # Custom manager
    objects = NotebookManager()
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notebook"
        verbose_name_plural = "Notebooks"
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "name"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_notebook_name_per_user'
            )
        ]
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Django model validation."""
        if not self.name or not self.name.strip():
            raise ValidationError("Notebook name cannot be empty")
        
        # Normalize the name
        self.name = self.name.strip()
        
        # Check for duplicate names for the same user (case-insensitive)
        if self.user_id:
            existing = Notebook.objects.filter(
                user=self.user,
                name__iexact=self.name
            ).exclude(pk=self.pk)
            
            if existing.exists():
                raise ValidationError("A notebook with this name already exists")
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def source_count(self):
        """Get the count of sources in this notebook."""
        if hasattr(self, '_source_count'):
            return self._source_count
        return getattr(self, 'sources', []).count() if hasattr(self, 'sources') else 0
    
    @property 
    def knowledge_item_count(self):
        """Get the count of knowledge base items in this notebook."""
        if hasattr(self, '_knowledge_item_count'):
            return self._knowledge_item_count
        return self.knowledge_base_items.count()
    
    @property
    def chat_message_count(self):
        """Get the count of chat messages in this notebook."""
        if hasattr(self, '_chat_message_count'):
            return self._chat_message_count
        return self.chat_messages.count()
    
    def get_processing_status_summary(self):
        """Get summary of processing status for all knowledge items."""
        from django.db.models import Count
        
        status_counts = self.knowledge_base_items.values('processing_status').annotate(
            count=Count('id')
        ).order_by('processing_status')
        
        return {item['processing_status']: item['count'] for item in status_counts}
    
    def has_processed_content(self):
        """Check if notebook has any successfully processed content."""
        return self.knowledge_base_items.processed().exists()
    
    def get_content_types_summary(self):
        """Get summary of content types in this notebook."""
        from django.db.models import Count
        
        type_counts = self.knowledge_base_items.values('content_type').annotate(
            count=Count('id')
        ).order_by('content_type')
        
        return {item['content_type']: item['count'] for item in type_counts}
    
    def cleanup_failed_items(self):
        """Remove knowledge base items that failed processing."""
        failed_items = self.knowledge_base_items.failed()
        count = failed_items.count()
        failed_items.delete()
        return count