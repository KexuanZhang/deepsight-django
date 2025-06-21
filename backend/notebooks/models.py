import os
import mimetypes
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


class Notebook(models.Model):
    """
    Represents a user-created notebook to organize sources and knowledge items.
    """
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
    SOURCE_TYPE_CHOICES = [
        ("file", "File Upload"),
        ("url",  "URL"),
        ("text", "Pasted Text"),
    ]
    PROCESSING_STATUS_CHOICES = [
        ("pending",     "Pending"),
        ("in_progress", "In Progress"),
        ("done",        "Done"),
        ("error",       "Error"),
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

    def __str__(self):
        return f"{self.get_source_type_display()} — {self.title or self.pk}"


# Optimized file upload path functions with proper date formatting
def user_notebook_source_upload_path(instance, filename):
    """Generate organized upload path for source files with proper date formatting."""
    user_id = instance.source.notebook.user.pk
    notebook_id = instance.source.notebook.pk
    now = timezone.now()
    
    # Create a clean, organized path structure
    # Format: source_uploads/user_1/notebook_2/2024/12/20/filename.pdf
    return f"source_uploads/user_{user_id}/notebook_{notebook_id}/{now.year:04d}/{now.month:02d}/{now.day:02d}/{filename}"


def user_notebook_pasted_text_path(instance, filename):
    """Generate organized upload path for pasted text files with proper date formatting."""
    user_id = instance.source.notebook.user.pk
    notebook_id = instance.source.notebook.pk
    now = timezone.now()
    
    # Format: pasted_text/user_1/notebook_2/2024/12/20/paste_123456789.txt
    return f"pasted_text/user_{user_id}/notebook_{notebook_id}/{now.year:04d}/{now.month:02d}/{now.day:02d}/{filename}"


def user_knowledge_base_path(instance, filename):
    """Generate organized path for knowledge base processed content with proper date formatting."""
    user_id = instance.user.pk
    now = timezone.now()
    
    # Format: knowledge_base/user_1/2024/12/20/processed_content.md
    return f"knowledge_base/user_{user_id}/{now.year:04d}/{now.month:02d}/{now.day:02d}/{filename}"


def user_url_processing_path(instance, filename):
    """Generate organized path for URL processing downloads with proper date formatting."""
    user_id = instance.source.notebook.user.pk
    notebook_id = instance.source.notebook.pk
    now = timezone.now()
    
    # Format: url_downloads/user_1/notebook_2/2024/12/20/downloaded_file.ext
    return f"url_downloads/user_{user_id}/notebook_{notebook_id}/{now.year:04d}/{now.month:02d}/{now.day:02d}/{filename}"


def user_processing_results_path(instance, filename):
    """Generate organized path for processing result files with proper date formatting."""
    user_id = instance.source.notebook.user.pk
    notebook_id = instance.source.notebook.pk
    now = timezone.now()
    
    # Format: processing_results/user_1/notebook_2/2024/12/20/result_file.md
    return f"processing_results/user_{user_id}/notebook_{notebook_id}/{now.year:04d}/{now.month:02d}/{now.day:02d}/{filename}"


class UploadedFile(models.Model):
    """
    Stores any binary the user uploaded for a Source of type "file."
    These are notebook-specific raw files.
    """
    source = models.OneToOneField(
        Source,
        on_delete=models.CASCADE,
        related_name="upload",
    )
    file = models.FileField(
        upload_to=user_notebook_source_upload_path,
        help_text="Original user-uploaded file (PDF, MP3, MP4, etc.) - notebook specific",
    )
    content_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Guessed MIME type, e.g. application/pdf, audio/mpeg…",
    )
    original_name = models.CharField(
        max_length=255,
        help_text="Filename as uploaded by the user",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # On first save, auto-populate MIME type and original name
        if not self.pk:
            self.content_type = mimetypes.guess_type(self.file.name)[0] or ""
            self.original_name = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.original_name


class PastedTextFile(models.Model):
    """
    When the user pastes raw text, we write it out as a .txt and store it here.
    These are notebook-specific.
    """
    source = models.OneToOneField(
        Source,
        on_delete=models.CASCADE,
        related_name="pasted_text_file",
    )
    file = models.FileField(
        upload_to=user_notebook_pasted_text_path,
        validators=[FileExtensionValidator(allowed_extensions=["txt"] )],
        help_text="Auto-generated .txt of pasted content - notebook specific",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # You must assign self._raw_text before calling save()
        if not self.pk and hasattr(self, "_raw_text"):
            filename = f"paste-{self.source.pk}-{int(timezone.now().timestamp())}.txt"
            from django.core.files.base import ContentFile

            self.file.save(filename, ContentFile(self._raw_text), save=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return os.path.basename(self.file.name)


class URLProcessingResult(models.Model):
    """
    Holds the result of crawling or downloading when the user provides a URL.
    These are notebook-specific.
    """
    source = models.OneToOneField(
        Source,
        on_delete=models.CASCADE,
        related_name="url_result",
    )
    content_md = models.TextField(
        blank=True,
        help_text="Markdown extracted from a webpage, if applicable",
    )
    downloaded_file = models.FileField(
        upload_to=user_url_processing_path,
        blank=True,
        null=True,
        help_text="Media file downloaded from the URL, if any",
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error details if crawl or download failed",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"URLResult for Source {self.source_id}"


class ProcessingJob(models.Model):
    """
    A background job to process binaries or downloaded media (OCR, transcription, PDF→MD, etc.).
    """
    JOB_STATUS_CHOICES = [
        ("queued",   "Queued"),
        ("running",  "Running"),
        ("finished", "Finished"),
        ("failed",   "Failed"),
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
    result_file = models.FileField(
        upload_to=user_processing_results_path,
        blank=True,
        null=True,
        help_text="Generated .md or other output file",
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error details if processing failed",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.job_type} [{self.status}] for Source {self.source_id}"


class KnowledgeBaseItem(models.Model):
    """
    User-wide knowledge base items that can be shared across notebooks.
    These are the processed, searchable content items.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="knowledge_base_items",
        help_text="Owner of this knowledge item"
    )
    title = models.CharField(
        max_length=512,
        help_text="Title or identifier for this knowledge item"
    )
    content_type = models.CharField(
        max_length=50,
        choices=[
            ('text', 'Text Content'),
            ('document', 'Document'),
            ('webpage', 'Webpage'),
            ('media', 'Media File'),
        ],
        default='text'
    )
    file = models.FileField(
        upload_to=user_knowledge_base_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["md", "txt"])],
        help_text="Processed content file in the user's knowledge base",
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'source_hash']),
            models.Index(fields=['user', 'content_type']),
        ]

    def __str__(self):
        return f"{self.title} ({self.content_type})"


class KnowledgeItem(models.Model):
    """
    Links between notebooks and knowledge base items.
    This allows sharing knowledge items across multiple notebooks.
    """
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
        help_text="Original source that created this knowledge item (if any)"
    )
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(
        blank=True,
        help_text="Notebook-specific notes about this knowledge item"
    )

    class Meta:
        ordering = ["-added_at"]
        unique_together = ['notebook', 'knowledge_base_item']
        indexes = [
            models.Index(fields=['notebook', '-added_at']),
        ]

    def clean(self):
        # Ensure the knowledge base item belongs to the same user as the notebook
        if self.knowledge_base_item and self.notebook:
            if self.knowledge_base_item.user != self.notebook.user:
                raise ValidationError("Knowledge base item must belong to the same user as the notebook")

    def __str__(self):
        return f"{self.notebook.name} -> {self.knowledge_base_item.title}"
