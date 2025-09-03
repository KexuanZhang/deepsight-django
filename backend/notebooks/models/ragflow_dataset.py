"""
RagFlow Dataset model for managing RagFlow datasets linked to notebooks.
"""

from django.db import models
from django.core.exceptions import ValidationError
from core.mixins import BaseModel


class RagFlowDataset(BaseModel):
    """
    RagFlow dataset linked to a notebook for RAG functionality.
    
    Each notebook has exactly one RagFlow dataset that contains all the
    processed content from the notebook's knowledge base items.
    """
    
    STATUS_CHOICES = [
        ("creating", "Creating"),
        ("active", "Active"),
        ("error", "Error"),
        ("deleting", "Deleting"),
    ]
    
    notebook = models.OneToOneField(
        'notebooks.Notebook',
        on_delete=models.CASCADE,
        related_name="ragflow_dataset",
        help_text="Notebook this dataset belongs to"
    )
    ragflow_dataset_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="RagFlow dataset ID from RagFlow API"
    )
    dataset_name = models.CharField(
        max_length=255,
        help_text="Human-readable dataset name (generated from notebook name + user ID)"
    )
    ragflow_chat_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="RagFlow chat assistant ID for this dataset"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="creating",
        help_text="Current status of the dataset",
        db_index=True,
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if dataset creation/management failed"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="RagFlow configuration and statistics"
    )
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "RagFlow Dataset"
        verbose_name_plural = "RagFlow Datasets"
        indexes = [
            models.Index(fields=["notebook", "status"]),
            models.Index(fields=["ragflow_dataset_id"]),
            models.Index(fields=["status", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(ragflow_dataset_id=""),
                name='ragflow_dataset_id_not_empty'
            ),
            models.CheckConstraint(
                check=~models.Q(dataset_name=""),
                name='dataset_name_not_empty'
            )
        ]
    
    def __str__(self):
        return f"RagFlow Dataset for {self.notebook.name} ({self.status})"
    
    def clean(self):
        """Django model validation."""
        if not self.ragflow_dataset_id or not self.ragflow_dataset_id.strip():
            raise ValidationError("RagFlow dataset ID cannot be empty")
        
        if not self.dataset_name or not self.dataset_name.strip():
            raise ValidationError("Dataset name cannot be empty")
        
        # Normalize fields
        self.ragflow_dataset_id = self.ragflow_dataset_id.strip()
        self.dataset_name = self.dataset_name.strip()
        
        # Validate metadata is a dict
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise ValidationError("Metadata must be a dictionary")
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def is_ready(self):
        """Check if dataset is ready for use."""
        return self.status == "active"
    
    def has_error(self):
        """Check if dataset has an error."""
        return self.status == "error"
    
    def mark_active(self):
        """Mark dataset as active and ready for use."""
        self.status = "active"
        self.error_message = ""
        self.save(update_fields=['status', 'error_message', 'updated_at'])
    
    def mark_error(self, error_message: str):
        """Mark dataset as having an error."""
        self.status = "error"
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])
    
    def mark_deleting(self):
        """Mark dataset as being deleted."""
        self.status = "deleting"
        self.save(update_fields=['status', 'updated_at'])
    
    def get_stats(self):
        """Get dataset statistics from metadata."""
        return self.metadata.get('stats', {})
    
    def update_stats(self, stats_data: dict):
        """Update dataset statistics in metadata."""
        if not isinstance(self.metadata, dict):
            self.metadata = {}
        self.metadata['stats'] = stats_data
        self.save(update_fields=['metadata', 'updated_at'])
    
    def get_ragflow_config(self):
        """Get RagFlow configuration from metadata."""
        return self.metadata.get('config', {})
    
    def update_ragflow_config(self, config_data: dict):
        """Update RagFlow configuration in metadata."""
        if not isinstance(self.metadata, dict):
            self.metadata = {}
        self.metadata['config'] = config_data
        self.save(update_fields=['metadata', 'updated_at'])
    
    @classmethod
    def generate_dataset_name(cls, notebook):
        """Generate a unique dataset name for the notebook."""
        # Use notebook name + user ID to ensure uniqueness
        safe_notebook_name = "".join(c for c in notebook.name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_notebook_name = safe_notebook_name.replace(' ', '_')
        return f"{safe_notebook_name}_user_{notebook.user.id}"
    
    def get_document_count(self):
        """Get count of documents in this dataset."""
        return self.notebook.knowledge_base_items.exclude(
            ragflow_document_id__isnull=True
        ).exclude(
            ragflow_document_id=""
        ).count()