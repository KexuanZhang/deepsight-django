import os
import mimetypes
import uuid
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
import logging


logger = logging.getLogger(__name__)


class KnowledgeBaseItemManager(models.Manager):
    """Custom manager for KnowledgeBaseItem with content retrieval methods."""
    
    def get_content(self, item_id: str, user_id: int):
        """
        Get content for a knowledge base item using the same logic as FileContentView.
        
        Args:
            item_id: Knowledge base item ID
            user_id: User ID for security verification
            
        Returns:
            Content string or None if not found
        """
        try:
            from django.contrib.auth import get_user_model
            from .utils.storage_adapter import get_storage_adapter
            
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            # Security: Find knowledge base item through user's notebooks
            item = self.select_related('notebook').get(
                id=item_id, 
                notebook__user=user
            )
            
            # Use storage adapter to get content (same as FileContentView)
            storage_adapter = get_storage_adapter()
            content = storage_adapter.get_file_content(item_id, user_id=user_id)
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to get content for KB item {item_id}: {e}")
            return None
    
    def get_multiple_contents(self, item_ids: list, user_id: int):
        """
        Get content for multiple knowledge base items.
        
        Args:
            item_ids: List of knowledge base item IDs
            user_id: User ID for security verification
            
        Returns:
            Dictionary mapping item_id to content (or None if not found)
        """
        results = {}
        for item_id in item_ids:
            content = self.get_content(item_id, user_id)
            results[item_id] = content
        return results
    
    def get_items_with_content(self, item_ids: list, user_id: int):
        """
        Get knowledge base items with their content and metadata.
        Only returns items that have actual content.
        
        Args:
            item_ids: List of knowledge base item IDs  
            user_id: User ID for security verification
            
        Returns:
            List of dictionaries with item data and content
        """
        try:
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            # Security: Find items through user's notebooks
            items = self.select_related('notebook').filter(
                id__in=item_ids,
                notebook__user=user
            )
            
            results = []
            for item in items:
                content = self.get_content(str(item.id), user_id)
                
                # Skip items with no content
                if not content or not content.strip():
                    logger.debug(f"Skipping item {item.id} - no content available")
                    continue
                    
                results.append({
                    'id': str(item.id),
                    'title': item.title,
                    'content': content,
                    'content_type': item.content_type,
                    'metadata': item.metadata or {},
                    'processing_status': item.processing_status,
                })
                
            logger.info(f"Retrieved {len(results)} items with content out of {len(item_ids)} requested")
            return results
            
        except Exception as e:
            logger.error(f"Failed to get knowledge base items with content: {e}")
            return []
    
    def get_content_with_minio_urls(self, item_id: str, user_id: int, expires: int = 86400):
        """
        Get content with all image links converted to direct MinIO pre-signed URLs.
        
        Args:
            item_id: Knowledge base item ID
            user_id: User ID for access control
            expires: URL expiration time in seconds (default: 24 hours)
            
        Returns:
            Content with MinIO URLs for images
        """
        try:
            from django.contrib.auth import get_user_model
            from django.apps import apps
            from .utils.storage import get_minio_backend
            
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            # Security: Find knowledge base item through user's notebooks  
            item = self.select_related('notebook').get(
                id=item_id,
                notebook__user=user
            )
            
            # Get base content using our standard method
            content = self.get_content(item_id, user_id)
            if not content:
                return None
            
            # Get all images for this knowledge base item
            KnowledgeBaseImage = apps.get_model('notebooks', 'KnowledgeBaseImage')
            images = KnowledgeBaseImage.objects.filter(knowledge_base_item=item)
            
            # Create mapping of filenames to MinIO URLs
            image_url_mapping = {}
            minio_backend = get_minio_backend()
            
            for image in images:
                try:
                    presigned_url = minio_backend.get_presigned_url(image.minio_object_key, expires)
                    # Extract filename from object key or use figure_id as fallback
                    import os
                    filename = os.path.basename(image.minio_object_key) if image.minio_object_key else f"{image.figure_id}.jpg"
                    image_url_mapping[filename] = presigned_url
                except Exception as e:
                    logger.error(f"Failed to generate URL for image {image.figure_id}: {e}")
            
            # Update content with MinIO URLs
            if image_url_mapping:
                content = self._update_image_links_to_minio_urls(content, image_url_mapping)
                logger.info(f"Retrieved content with {len(image_url_mapping)} MinIO image URLs")
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to get content with MinIO URLs for {item_id}: {e}")
            return None
    
    def _update_image_links_to_minio_urls(self, content: str, image_url_mapping: dict) -> str:
        """
        Update all image links in content to use MinIO pre-signed URLs.
        
        Args:
            content: Original content with image references
            image_url_mapping: Dictionary mapping filenames to MinIO URLs
            
        Returns:
            Updated content with MinIO URLs
        """
        import re
        import os
        
        # Pattern to match markdown image syntax: ![alt](filename)
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        def replace_image_url(match):
            alt_text = match.group(1)
            original_filename = match.group(2)
            
            # Extract just the filename (remove path if present)
            filename = os.path.basename(original_filename)
            
            # Get MinIO URL for this filename
            minio_url = image_url_mapping.get(filename)
            if minio_url:
                return f'![{alt_text}]({minio_url})'
            else:
                # Keep original if no mapping found
                return match.group(0)
        
        # Replace all image URLs
        updated_content = re.sub(pattern, replace_image_url, content)
        
        return updated_content


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




class KnowledgeBaseItem(models.Model):
    """
    Notebook-specific knowledge base items that contain processed, searchable content.
    Each item belongs to a specific notebook.
    """
    
    PROCESSING_STATUS_CHOICES = [
        ("processing", "Processing"),
        ("in_progress", "In Progress"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notebook = models.ForeignKey(
        Notebook,
        on_delete=models.CASCADE,
        related_name="knowledge_base_items",
        help_text="Notebook this knowledge item belongs to",
    )
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default="processing",
        help_text="Processing status of this knowledge base item",
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
    notes = models.TextField(
        blank=True,
        help_text="User notes about this knowledge item",
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

    # Custom manager for content retrieval
    objects = KnowledgeBaseItemManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["notebook", "-created_at"]),
            models.Index(fields=["notebook", "source_hash"]),
            models.Index(fields=["notebook", "content_type"]),
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

    # Removed get_file_content() instance method - use KnowledgeBaseItem.objects.get_content() instead

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
    figure_id = models.UUIDField(default=uuid.uuid4, editable=False, help_text="Unique figure identifier, different from primary key")
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
    
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["knowledge_base_item", "created_at"]
        verbose_name = "Knowledge Base Image"
        verbose_name_plural = "Knowledge Base Images"
        indexes = [
            models.Index(fields=["knowledge_base_item", "created_at"]),
            models.Index(fields=["minio_object_key"]),
        ]
        unique_together = []
    
    def __str__(self):
        return f"Image for {self.knowledge_base_item.title} - {self.id}"
    
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
            'figure_id': str(self.figure_id),
            'caption': self.image_caption,
        }
    
    @classmethod
    def create_from_figure_data(cls, knowledge_base_item, figure_data_dict, minio_object_key=None):
        """
        Create KnowledgeBaseImage instance from figure_data.json dictionary format.
        This helps migrate from the old figure_data.json system.
        """
        return cls.objects.create(
            knowledge_base_item=knowledge_base_item,
            image_caption=figure_data_dict.get('caption', ''),
            minio_object_key=minio_object_key or '',
            content_type=figure_data_dict.get('content_type', ''),
            file_size=figure_data_dict.get('file_size', 0),
            image_metadata=figure_data_dict,
        )

