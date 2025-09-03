"""
Django model and view mixins for common functionality.
"""

import uuid
from django.db import models
from django.utils import timezone


class TimestampMixin(models.Model):
    """Mixin to add created_at and updated_at timestamps to models."""
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class UUIDMixin(models.Model):
    """Mixin to add UUID primary key to models."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True


class UserOwnedMixin(models.Model):
    """Mixin for models that belong to a user."""
    
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set'
    )
    
    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """Mixin to add soft delete functionality."""
    
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        """Mark the object as deleted without actually deleting it."""
        self.deleted_at = timezone.now()
        self.save()
    
    def restore(self):
        """Restore a soft deleted object."""
        self.deleted_at = None
        self.save()
    
    @property
    def is_deleted(self):
        """Check if the object is soft deleted."""
        return self.deleted_at is not None


class BaseModel(UUIDMixin, TimestampMixin):
    """Base model with UUID primary key and timestamps."""
    
    class Meta:
        abstract = True