import os
import mimetypes
import uuid
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Notebook(models.Model):
    """
    Represents a user-created notebook to organize sources and knowledge items.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notebooks",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notebook"
        verbose_name_plural = "Notebooks"

    def __str__(self):
        return self.name


class Source(models.Model):
    """
    A generic "source" that the user adds to a notebook:
    • File upload
    • URL
    • Pasted text
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    SOURCE_TYPE_CHOICES = [
        ("file", "File Upload"),
        ("url", "URL"),
        ("text", "Pasted Text"),
    ]
    PROCESSING_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("done", "Done"),
        ("error", "Error"),
    ]

    notebook = models.ForeignKey(
        Notebook,
        on_delete=models.CASCADE,
        related_name="sources",
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
    )
    title = models.CharField(
        max_length=512,
        blank=True,
        help_text="Optional display title or original filename/URL",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    needs_processing = models.BooleanField(
        default=False,
        help_text="Whether this source must go through a background processing job",
    )
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default="pending",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or f"Source {self.id}"


class URLProcessingResult(models.Model):
    """
    Holds the result of crawling or downloading when the user provides a URL.
    These are notebook-specific.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.OneToOneField(
        Source,
        on_delete=models.CASCADE,
        related_name="url_result",
    )
    content_md = models.TextField(
        blank=True,
        help_text="Markdown extracted from a webpage, if applicable",
    )
    
    # MinIO-native storage
    downloaded_file_object_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        db_index=True,
        help_text="MinIO object key for downloaded media file"
    )
    file_metadata = models.JSONField(
        default=dict,
        help_text="Downloaded file metadata (name, size, content_type, etc.)"
    )
    
    error_message = models.TextField(
        blank=True,
        help_text="Error details if crawl or download failed",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"URLResult for Source {self.source_id}"
    
    def get_downloaded_file_url(self, expires=86400):
        """Get pre-signed URL for downloaded file"""
        if self.downloaded_file_object_key:
            try:
                from .utils.storage import get_minio_backend
                backend = get_minio_backend()
                return backend.get_presigned_url(self.downloaded_file_object_key, expires)
            except Exception:
                return None
        return None


class ProcessingJob(models.Model):
    """
    A background job to process binaries or downloaded media (OCR, transcription, PDF→MD, etc.).
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    JOB_STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("finished", "Finished"),
        ("failed", "Failed"),
    ]

    source = models.ForeignKey(
        Source,
        on_delete=models.CASCADE,
        related_name="jobs",
    )
    job_type = models.CharField(
        max_length=50,
        help_text="E.g. ocr, transcribe, pdf2md…",
    )
    status = models.CharField(
        max_length=20,
        choices=JOB_STATUS_CHOICES,
        default="queued",
    )
    
    # MinIO-native storage
    result_file_object_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        db_index=True,
        help_text="MinIO object key for generated result file"
    )
    result_file_metadata = models.JSONField(
        default=dict,
        help_text="Result file metadata (name, size, content_type, etc.)"
    )
    
    error_message = models.TextField(
        blank=True,
        help_text="Error details if processing failed",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ProcessingJob {self.id} ({self.job_type}) for Source {self.source_id}"
    
    def get_result_file_url(self, expires=86400):
        """Get pre-signed URL for result file"""
        if self.result_file_object_key:
            try:
                from .utils.storage import get_minio_backend
                backend = get_minio_backend()
                return backend.get_presigned_url(self.result_file_object_key, expires)
            except Exception:
                return None
        return None


class KnowledgeBaseItem(models.Model):
    """
    User-wide knowledge base items that can be shared across notebooks.
    These are the processed, searchable content items.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="knowledge_base_items",
        help_text="Owner of this knowledge item",
    )
    title = models.CharField(
        max_length=512, help_text="Title or identifier for this knowledge item"
    )
    content_type = models.CharField(
        max_length=50,
        choices=[
            ("text", "Text Content"),
            ("document", "Document"),
            ("webpage", "Webpage"),
            ("media", "Media File"),
        ],
        default="text",
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
        help_text="Tags for categorization and search",
    )
    
    # MinIO-native storage fields (replaces Django FileFields)
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
        help_text="File metadata stored in database (replaces file system metadata)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "source_hash"]),
            models.Index(fields=["user", "content_type"]),
            # MinIO-specific indexes
            models.Index(fields=["file_object_key"]),
            models.Index(fields=["original_file_object_key"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.content_type})"
    
    def get_file_url(self, expires=86400):
        """Get pre-signed URL for processed file"""
        if self.file_object_key:
            try:
                from .utils.storage import get_minio_backend
                backend = get_minio_backend()
                return backend.get_presigned_url(self.file_object_key, expires)
            except Exception:
                return None
        return None
    
    def get_original_file_url(self, expires=86400):
        """Get pre-signed URL for original file"""
        if self.original_file_object_key:
            try:
                from .utils.storage import get_minio_backend
                backend = get_minio_backend()
                return backend.get_presigned_url(self.original_file_object_key, expires)
            except Exception:
                return None
        return None

    def get_file_content(self):
        """Get the content from either inline field, processed file, or original file"""
        if self.content:
            return self.content
        elif self.file_object_key:
            try:
                from .utils.storage import get_minio_backend
                backend = get_minio_backend()
                content = backend.get_file(self.file_object_key)
                return content.decode('utf-8') if isinstance(content, bytes) else content
            except Exception:
                pass  # Fall through to try original file
        
        # If no processed content, try the original file (useful for .md files)
        if self.original_file_object_key:
            try:
                from .utils.storage import get_minio_backend
                backend = get_minio_backend()
                content = backend.get_file(self.original_file_object_key)
                return content.decode('utf-8') if isinstance(content, bytes) else content
            except Exception:
                pass
        
        return ""

    def has_minio_storage(self):
        """Check if this item uses MinIO storage"""
        return bool(self.file_object_key or self.original_file_object_key)

    def get_storage_info(self):
        """Get storage information for this item"""
        return {
            'has_processed_file': bool(self.file_object_key),
            'has_original_file': bool(self.original_file_object_key),
            'file_metadata': self.file_metadata,
        }


class KnowledgeItem(models.Model):
    """
    Links between notebooks and knowledge base items.
    This allows sharing knowledge items across multiple notebooks.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notebook = models.ForeignKey(
        Notebook,
        on_delete=models.CASCADE,
        related_name="knowledge_items",
    )
    knowledge_base_item = models.ForeignKey(
        KnowledgeBaseItem,
        on_delete=models.CASCADE,
        related_name="notebook_links",
    )
    source = models.ForeignKey(
        Source,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="knowledge_items",
        help_text="Original source that created this knowledge item (if any)",
    )
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(
        blank=True,
        help_text="User notes about this knowledge item in this notebook",
    )

    class Meta:
        ordering = ["-added_at"]
        unique_together = ["notebook", "knowledge_base_item"]
        indexes = [
            models.Index(fields=["notebook", "-added_at"]),
            models.Index(fields=["knowledge_base_item"]),
        ]

    def clean(self):
        # Ensure the knowledge base item belongs to the same user as the notebook
        if (
            self.notebook
            and self.knowledge_base_item
            and self.notebook.user != self.knowledge_base_item.user
        ):
            raise ValidationError(
                "Knowledge base item must belong to the same user as the notebook."
            )

    def __str__(self):
        return f"{self.notebook.name} -> {self.knowledge_base_item.title}"


class BatchJob(models.Model):
    """
    Tracks batch processing operations for multiple URLs/files.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
        Notebook,
        on_delete=models.CASCADE,
        related_name='batch_jobs'
    )
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=BATCH_STATUS_CHOICES, default='pending')
    total_items = models.IntegerField(default=0)
    completed_items = models.IntegerField(default=0)
    failed_items = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"BatchJob {self.id} ({self.job_type}) - {self.status}"


class BatchJobItem(models.Model):
    """
    Individual items within a batch job.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ITEM_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    batch_job = models.ForeignKey(
        BatchJob,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item_data = models.JSONField(help_text="URL, filename, or other item-specific data")
    upload_id = models.CharField(max_length=64, blank=True, help_text="Upload/processing ID for status tracking")
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='pending')
    result_data = models.JSONField(null=True, blank=True, help_text="Processing results")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"BatchJobItem {self.id} - {self.status}"


class NotebookChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notebook = models.ForeignKey(
        "Notebook",
        on_delete=models.CASCADE,
        related_name="chat_messages"
    )
    sender = models.CharField(
        max_length=10,
        choices=[("user", "User"), ("assistant", "Assistant")]
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.sender}: {self.message[:50]}..."


class KnowledgeBaseImage(models.Model):
    """
    Store image metadata for knowledge base items, replacing figure_data.json files.
    Each image is linked to a knowledge base item and stored in MinIO.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    knowledge_base_item = models.ForeignKey(
        KnowledgeBaseItem,
        on_delete=models.CASCADE,
        related_name="images",
        help_text="Knowledge base item this image belongs to"
    )
    
    # Image identification and metadata
    figure_name = models.CharField(
        max_length=100,
        default="Figure 1",
        help_text="Figure name like 'Figure 1', 'Figure 2', extracted from PDF or auto-generated"
    )
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
    
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["knowledge_base_item", "figure_name"]
        verbose_name = "Knowledge Base Image"
        verbose_name_plural = "Knowledge Base Images"
        indexes = [
            models.Index(fields=["knowledge_base_item", "figure_name"]),
            models.Index(fields=["minio_object_key"]),
        ]
        unique_together = [
            ["knowledge_base_item", "figure_name"],  # Unique figure_name per knowledge base item
        ]
    
    def __str__(self):
        return f"{self.figure_name} - {self.knowledge_base_item.title}"
    
    def get_image_url(self, expires=86400):
        """Get pre-signed URL for image access"""
        if self.minio_object_key:
            try:
                from .utils.storage import get_minio_backend
                backend = get_minio_backend()
                return backend.get_presigned_url(self.minio_object_key, expires)
            except Exception:
                return None
        return None
    
    def get_image_content(self):
        """Get image content as bytes from MinIO"""
        if self.minio_object_key:
            try:
                from .utils.storage import get_minio_backend
                backend = get_minio_backend()
                return backend.get_file(self.minio_object_key)
            except Exception:
                return None
        return None
    
    def to_figure_data_dict(self):
        """
        Convert to figure_data.json compatible dictionary format.
        This maintains compatibility with existing code that expects figure_data structure.
        """
        return {
            'image_id': str(self.id),
            'caption': self.image_caption,
        }
    
    @classmethod
    def create_from_figure_data(cls, knowledge_base_item, figure_data_dict, minio_object_key=None):
        """
        Create KnowledgeBaseImage instance from figure_data.json dictionary format.
        This helps migrate from the old figure_data.json system.
        """
        # Extract figure_name from figure_data_dict
        figure_name = figure_data_dict.get('figure_name', 'Figure 1')
        
        return cls.objects.create(
            knowledge_base_item=knowledge_base_item,
            image_caption=figure_data_dict.get('caption', ''),
            figure_name=figure_name,
            minio_object_key=minio_object_key or '',
            content_type=figure_data_dict.get('content_type', ''),
            file_size=figure_data_dict.get('file_size', 0),
            image_metadata=figure_data_dict,
        )
    
