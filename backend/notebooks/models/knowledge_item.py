"""
Knowledge base item and image models for processed content storage.
"""

import uuid
from django.db import models
from django.core.exceptions import ValidationError
from core.mixins import BaseModel
from .managers import KnowledgeBaseItemManager


class KnowledgeBaseItem(BaseModel):
    """
    Notebook-specific knowledge base items containing processed, searchable content.
    Each item belongs to a specific notebook and contains processed content from sources.
    """
    
    PARSING_STATUS_CHOICES = [
        ("queueing", "Queueing"),
        ("parsing", "Parsing"),
        ("done", "Done"),
    ]
    
    CONTENT_TYPE_CHOICES = [
        ("text", "Text Content"),
        ("document", "Document"),
        ("webpage", "Webpage"),
        ("media", "Media File"),
    ]
    
    notebook = models.ForeignKey(
        'notebooks.Notebook',
        on_delete=models.CASCADE,
        related_name="knowledge_base_items",
        help_text="Notebook this knowledge item belongs to",
    )
    parsing_status = models.CharField(
        max_length=20,
        choices=PARSING_STATUS_CHOICES,
        default="queueing",
        help_text="Parsing status of this knowledge base item",
        db_index=True,
    )
    title = models.CharField(
        max_length=512, 
        help_text="Title or identifier for this knowledge item"
    )
    content_type = models.CharField(
        max_length=50,
        choices=CONTENT_TYPE_CHOICES,
        default="text",
        db_index=True,
    )
    content = models.TextField(
        blank=True,
        help_text="Inline text content if not stored as file",
    )
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Source metadata, processing info, etc.",
    )
    source_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="Hash of original content to detect duplicates",
        db_index=True,
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for categorization and search",
    )
    notes = models.TextField(
        blank=True,
        help_text="User notes about this knowledge item",
    )
    
    # MinIO-native storage fields
    file_object_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        db_index=True,
        help_text="MinIO object key for processed content file"
    )
    original_file_object_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        db_index=True,
        help_text="MinIO object key for original file"
    )
    file_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="File metadata stored in database"
    )
    
    # RagFlow integration fields
    ragflow_document_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="RagFlow document ID linking to uploaded document in RagFlow dataset"
    )
    ragflow_processing_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("uploading", "Uploading"),
            ("parsing", "Parsing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
        db_index=True,
        help_text="RagFlow document processing status"
    )
    
    # Custom manager
    objects = KnowledgeBaseItemManager()
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Knowledge Base Item"
        verbose_name_plural = "Knowledge Base Items"
        indexes = [
            models.Index(fields=["notebook", "-created_at"]),
            models.Index(fields=["notebook", "parsing_status"]),
            models.Index(fields=["notebook", "content_type"]),
            models.Index(fields=["notebook", "source_hash"]),
            models.Index(fields=["file_object_key"]),
            models.Index(fields=["original_file_object_key"]),
            models.Index(fields=["ragflow_document_id"]),
            models.Index(fields=["notebook", "ragflow_processing_status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(title=""),
                name='knowledge_item_title_not_empty'
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.content_type})"
    
    def clean(self):
        """Django model validation."""
        if not self.title or not self.title.strip():
            raise ValidationError("Knowledge item title cannot be empty")
        
        # Normalize title
        self.title = self.title.strip()
        
        # Validate tags is a list
        if self.tags is not None and not isinstance(self.tags, list):
            raise ValidationError("Tags must be a list")
        
        # Validate metadata is a dict
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise ValidationError("Metadata must be a dictionary")
        
        # Validate file_metadata is a dict
        if self.file_metadata is not None and not isinstance(self.file_metadata, dict):
            raise ValidationError("File metadata must be a dictionary")
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_file_url(self, expires=86400):
        """Get pre-signed URL for processed file."""
        if self.file_object_key:
            try:
                from infrastructure.storage.adapters import get_storage_adapter
                storage = get_storage_adapter()
                return storage.get_file_url(self.file_object_key, expires)
            except Exception:
                return None
        return None
    
    def get_original_file_url(self, expires=86400):
        """Get pre-signed URL for original file."""
        if self.original_file_object_key:
            try:
                from infrastructure.storage.adapters import get_storage_adapter
                storage = get_storage_adapter()
                return storage.get_file_url(self.original_file_object_key, expires)
            except Exception:
                return None
        return None
    
    def has_minio_storage(self):
        """Check if this item uses MinIO storage."""
        return bool(self.file_object_key or self.original_file_object_key)
    
    def get_storage_info(self):
        """Get storage information for this item."""
        return {
            'has_processed_file': bool(self.file_object_key),
            'has_original_file': bool(self.original_file_object_key),
            'file_metadata': self.file_metadata,
        }
    
    def mark_parsing_complete(self):
        """Mark item as parsing complete."""
        self.parsing_status = 'done'
        self.save(update_fields=['parsing_status', 'updated_at'])
    
    def mark_parsing_started(self):
        """Mark item as currently parsing."""
        self.parsing_status = 'parsing'
        self.save(update_fields=['parsing_status', 'updated_at'])
    
    def add_tag(self, tag):
        """Add a tag to this knowledge item."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
            self.save(update_fields=['tags', 'updated_at'])
    
    def remove_tag(self, tag):
        """Remove a tag from this knowledge item."""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
            self.save(update_fields=['tags', 'updated_at'])
    
    def has_content(self):
        """Check if item has actual content."""
        return bool((self.content and self.content.strip()) or 
                   self.file_object_key or 
                   self.original_file_object_key)
    
    # RagFlow integration methods
    def is_uploaded_to_ragflow(self):
        """Check if item has been uploaded to RagFlow."""
        return bool(self.ragflow_document_id and self.ragflow_document_id.strip())
    
    def is_ragflow_processing_complete(self):
        """Check if RagFlow processing is complete."""
        return self.ragflow_processing_status == 'completed'
    
    def is_ragflow_processing_failed(self):
        """Check if RagFlow processing failed."""
        return self.ragflow_processing_status == 'failed'
    
    def mark_ragflow_uploading(self):
        """Mark as being uploaded to RagFlow."""
        self.ragflow_processing_status = 'uploading'
        self.save(update_fields=['ragflow_processing_status', 'updated_at'])
    
    def mark_ragflow_parsing(self):
        """Mark as being parsed by RagFlow."""
        self.ragflow_processing_status = 'parsing'
        self.save(update_fields=['ragflow_processing_status', 'updated_at'])
    
    def mark_ragflow_completed(self, ragflow_document_id: str):
        """Mark RagFlow processing as completed."""
        self.ragflow_document_id = ragflow_document_id
        self.ragflow_processing_status = 'completed'
        self.save(update_fields=['ragflow_document_id', 'ragflow_processing_status', 'updated_at'])
    
    def mark_ragflow_failed(self, error_message: str = ""):
        """Mark RagFlow processing as failed."""
        self.ragflow_processing_status = 'failed'
        if error_message:
            # Store error in metadata
            if not isinstance(self.metadata, dict):
                self.metadata = {}
            self.metadata['ragflow_error'] = error_message
        self.save(update_fields=['ragflow_processing_status', 'metadata', 'updated_at'])
    
    def get_ragflow_error(self):
        """Get RagFlow error message from metadata."""
        if isinstance(self.metadata, dict):
            return self.metadata.get('ragflow_error', '')
        return ''


class KnowledgeBaseImage(BaseModel):
    """
    Store image metadata for knowledge base items.
    Each image is linked to a knowledge base item and stored in MinIO.
    """
    
    figure_id = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        help_text="Unique figure identifier, different from primary key"
    )
    knowledge_base_item = models.ForeignKey(
        KnowledgeBaseItem,
        on_delete=models.CASCADE,
        related_name="images",
        help_text="Knowledge base item this image belongs to"
    )
    
    # Image identification and metadata
    image_caption = models.TextField(
        blank=True,
        help_text="Description or caption for the image"
    )
    
    # MinIO storage fields
    minio_object_key = models.CharField(
        max_length=255,
        db_index=True,
        help_text="MinIO object key for the image file"
    )
    
    # Image metadata and properties
    image_metadata = models.JSONField(
        default=dict,
        help_text="Image metadata including dimensions, format, size, etc."
    )
    content_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="MIME type of the image (image/png, image/jpeg, etc.)"
    )
    file_size = models.PositiveIntegerField(
        default=0,
        help_text="File size in bytes"
    )
    
    class Meta:
        ordering = ["knowledge_base_item", "created_at"]
        verbose_name = "Knowledge Base Image"
        verbose_name_plural = "Knowledge Base Images"
        indexes = [
            models.Index(fields=["knowledge_base_item", "created_at"]),
            models.Index(fields=["minio_object_key"]),
            models.Index(fields=["figure_id"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(minio_object_key=""),
                name='image_object_key_not_empty'
            )
        ]
    
    def __str__(self):
        return f"Image for {self.knowledge_base_item.title} - {self.figure_id}"
    
    def clean(self):
        """Django model validation."""
        if not self.minio_object_key or not self.minio_object_key.strip():
            raise ValidationError("MinIO object key cannot be empty")
        
        # Normalize object key
        self.minio_object_key = self.minio_object_key.strip()
        
        # Validate image_metadata is a dict
        if self.image_metadata is not None and not isinstance(self.image_metadata, dict):
            raise ValidationError("Image metadata must be a dictionary")
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_image_url(self, expires=86400):
        """Get pre-signed URL for image access."""
        if self.minio_object_key:
            try:
                from infrastructure.storage.adapters import get_storage_adapter
                storage = get_storage_adapter()
                return storage.get_file_url(self.minio_object_key, expires)
            except Exception:
                return None
        return None
    
    def get_image_content(self):
        """Get image content as bytes from MinIO."""
        if self.minio_object_key:
            try:
                from infrastructure.storage.adapters import get_storage_adapter
                storage = get_storage_adapter()
                return storage.get_file_content(self.minio_object_key)
            except Exception:
                return None
        return None
    
    def to_figure_data_dict(self):
        """
        Convert to figure_data.json compatible dictionary format.
        Maintains compatibility with existing code.
        """
        return {
            'figure_id': str(self.figure_id),
            'caption': self.image_caption,
        }
    
    @classmethod
    def create_from_figure_data(cls, knowledge_base_item, figure_data_dict, minio_object_key=None):
        """
        Create KnowledgeBaseImage instance from figure_data.json dictionary format.
        Helps migrate from old figure_data.json system.
        """
        return cls.objects.create(
            knowledge_base_item=knowledge_base_item,
            image_caption=figure_data_dict.get('caption', ''),
            minio_object_key=minio_object_key or '',
            content_type=figure_data_dict.get('content_type', ''),
            file_size=figure_data_dict.get('file_size', 0),
            image_metadata=figure_data_dict,
        )