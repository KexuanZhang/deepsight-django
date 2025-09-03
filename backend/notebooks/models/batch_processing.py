"""
Batch processing models for handling multiple file/URL operations.
"""

from django.db import models
from django.core.exceptions import ValidationError
from core.mixins import BaseModel
from .managers import BatchJobManager


class BatchJob(BaseModel):
    """
    Tracks batch processing operations for multiple URLs/files.
    Each batch job can contain multiple individual items to process.
    """
    
    BATCH_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partially_completed', 'Partially Completed'),
    ]
    
    JOB_TYPE_CHOICES = [
        ('url_parse', 'URL Parse'),
        ('url_parse_media', 'URL Parse with Media'),
        ('file_upload', 'File Upload'),
    ]
    
    notebook = models.ForeignKey(
        'notebooks.Notebook',
        on_delete=models.CASCADE,
        related_name='batch_jobs',
        help_text="Notebook this batch job belongs to"
    )
    job_type = models.CharField(
        max_length=20, 
        choices=JOB_TYPE_CHOICES,
        help_text="Type of batch operation"
    )
    status = models.CharField(
        max_length=20, 
        choices=BATCH_STATUS_CHOICES, 
        default='pending',
        help_text="Current status of the batch job"
    )
    total_items = models.PositiveIntegerField(
        default=0,
        help_text="Total number of items to process"
    )
    completed_items = models.PositiveIntegerField(
        default=0,
        help_text="Number of successfully completed items"
    )
    failed_items = models.PositiveIntegerField(
        default=0,
        help_text="Number of failed items"
    )
    
    # Custom manager
    objects = BatchJobManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Batch Job"
        verbose_name_plural = "Batch Jobs"
        indexes = [
            models.Index(fields=["notebook", "-created_at"]),
            models.Index(fields=["notebook", "status"]),
            models.Index(fields=["notebook", "job_type"]),
            models.Index(fields=["status", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(total_items__gte=0),
                name='batch_job_total_items_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(completed_items__gte=0),
                name='batch_job_completed_items_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(failed_items__gte=0),
                name='batch_job_failed_items_non_negative'
            ),
        ]

    def __str__(self):
        return f"BatchJob {self.id} ({self.job_type}) - {self.status}"
    
    def clean(self):
        """Django model validation."""
        # Validate counters
        if self.completed_items + self.failed_items > self.total_items:
            raise ValidationError(
                "Completed items + failed items cannot exceed total items"
            )
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation and update status."""
        # Auto-update status based on item counts
        if self.total_items > 0:
            processed_items = self.completed_items + self.failed_items
            
            if processed_items == 0:
                if self.status not in ['pending', 'processing']:
                    self.status = 'pending'
            elif processed_items == self.total_items:
                if self.failed_items == 0:
                    self.status = 'completed'
                elif self.completed_items == 0:
                    self.status = 'failed'
                else:
                    self.status = 'partially_completed'
            else:
                self.status = 'processing'
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def progress_percentage(self):
        """Calculate completion percentage."""
        if self.total_items == 0:
            return 0
        return round((self.completed_items + self.failed_items) / self.total_items * 100, 1)
    
    @property
    def success_rate(self):
        """Calculate success rate percentage."""
        processed_items = self.completed_items + self.failed_items
        if processed_items == 0:
            return 0
        return round(self.completed_items / processed_items * 100, 1)
    
    def increment_completed(self):
        """Increment completed items counter."""
        self.completed_items += 1
        self.save(update_fields=['completed_items', 'status', 'updated_at'])
    
    def increment_failed(self):
        """Increment failed items counter."""
        self.failed_items += 1
        self.save(update_fields=['failed_items', 'status', 'updated_at'])
    
    def is_complete(self):
        """Check if batch job is complete."""
        return self.status in ['completed', 'failed', 'partially_completed']
    
    def get_summary(self):
        """Get job summary statistics."""
        return {
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'failed_items': self.failed_items,
            'pending_items': self.total_items - self.completed_items - self.failed_items,
            'progress_percentage': self.progress_percentage,
            'success_rate': self.success_rate,
            'status': self.status,
        }


class BatchJobItem(BaseModel):
    """
    Individual items within a batch job.
    Each item represents a single file or URL to be processed.
    """
    
    ITEM_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    batch_job = models.ForeignKey(
        BatchJob,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Batch job this item belongs to"
    )
    item_data = models.JSONField(
        help_text="URL, filename, or other item-specific data"
    )
    upload_id = models.CharField(
        max_length=64, 
        blank=True, 
        help_text="Upload/processing ID for status tracking"
    )
    status = models.CharField(
        max_length=20, 
        choices=ITEM_STATUS_CHOICES, 
        default='pending',
        help_text="Current status of this item"
    )
    result_data = models.JSONField(
        null=True, 
        blank=True, 
        help_text="Processing results"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if processing failed"
    )

    class Meta:
        ordering = ['created_at']
        verbose_name = "Batch Job Item"
        verbose_name_plural = "Batch Job Items"
        indexes = [
            models.Index(fields=["batch_job", "status"]),
            models.Index(fields=["batch_job", "created_at"]),
            models.Index(fields=["upload_id"]),
        ]

    def __str__(self):
        return f"BatchJobItem {self.id} - {self.status}"
    
    def clean(self):
        """Django model validation."""
        # Validate item_data is a dict
        if self.item_data is not None and not isinstance(self.item_data, dict):
            raise ValidationError("Item data must be a dictionary")
        
        # Validate result_data is a dict if provided
        if self.result_data is not None and not isinstance(self.result_data, dict):
            raise ValidationError("Result data must be a dictionary")
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation and update parent job."""
        old_status = None
        if self.pk:
            try:
                old_instance = BatchJobItem.objects.get(pk=self.pk)
                old_status = old_instance.status
            except BatchJobItem.DoesNotExist:
                pass
        
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Update parent batch job counters if status changed
        if old_status != self.status:
            self._update_batch_job_counters(old_status, self.status)
    
    def _update_batch_job_counters(self, old_status, new_status):
        """Update parent batch job item counters."""
        # Decrement old status counter
        if old_status == 'completed':
            self.batch_job.completed_items = max(0, self.batch_job.completed_items - 1)
        elif old_status == 'failed':
            self.batch_job.failed_items = max(0, self.batch_job.failed_items - 1)
        
        # Increment new status counter
        if new_status == 'completed':
            self.batch_job.completed_items += 1
        elif new_status == 'failed':
            self.batch_job.failed_items += 1
        
        # Save the batch job to trigger status update
        self.batch_job.save()
    
    def mark_completed(self, result_data=None):
        """Mark item as completed with optional result data."""
        self.status = 'completed'
        if result_data:
            self.result_data = result_data
        self.error_message = ''
        self.save()
    
    def mark_failed(self, error_message=''):
        """Mark item as failed with optional error message."""
        self.status = 'failed'
        self.error_message = error_message
        self.save()
    
    def get_display_name(self):
        """Get display name for this item based on item_data."""
        if isinstance(self.item_data, dict):
            return (self.item_data.get('filename') or 
                   self.item_data.get('url') or 
                   self.item_data.get('name') or 
                   f'Item {self.id}')
        return f'Item {self.id}'