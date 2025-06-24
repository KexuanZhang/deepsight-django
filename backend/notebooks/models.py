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

    def __str__(self):
        return f"{self.get_source_type_display()} — {self.title or self.pk}"


# File upload path functions


def user_knowledge_base_path(instance, filename):
    """
    Generate organized path for knowledge base files.

    New organized structure: Users/u_user_id/knowledge_base_item/yyyy-mm/f_file_id/content/extracted_content.md
    The FileStorageService will pass the full path including directory structure.
    """
    # The FileStorageService provides the full organized path
    return filename


def user_report_path(instance, filename):
    """Generate path for report files."""
    # Assuming instance has a user attribute or user_id
    user_id = getattr(instance, "user_id", None) or getattr(instance.user, "pk", None)
    current_date = datetime.now()
    year_month = current_date.strftime("%Y-%m")
    # Use instance ID as report ID if available
    report_id = getattr(instance, "id", "temp")
    return f"Users/u_{user_id}/report/{year_month}/r_{report_id}/{filename}"


def user_podcast_path(instance, filename):
    """Generate path for podcast files."""
    # Assuming instance has a user attribute or user_id
    user_id = getattr(instance, "user_id", None) or getattr(instance.user, "pk", None)
    current_date = datetime.now()
    year_month = current_date.strftime("%Y-%m")
    # Use instance ID as podcast ID if available
    podcast_id = getattr(instance, "id", "temp")
    return f"Users/u_{user_id}/podcast/{year_month}/p_{podcast_id}/{filename}"


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
        upload_to=user_knowledge_base_path,
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
    result_file = models.FileField(
        upload_to=user_knowledge_base_path,
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
    file = models.FileField(
        upload_to=user_knowledge_base_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["md", "txt"])],
        help_text="Processed content file in the user's knowledge base",
    )
    original_file = models.FileField(
        upload_to=user_knowledge_base_path,
        blank=True,
        null=True,
        help_text="Original binary file (PDF, audio, video, etc.) in the user's knowledge base",
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
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "source_hash"]),
            models.Index(fields=["user", "content_type"]),
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
        help_text="Original source that created this knowledge item (if any)",
    )
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(
        blank=True, help_text="Notebook-specific notes about this knowledge item"
    )

    class Meta:
        ordering = ["-added_at"]
        unique_together = ["notebook", "knowledge_base_item"]
        indexes = [
            models.Index(fields=["notebook", "-added_at"]),
        ]

    def clean(self):
        # Ensure the knowledge base item belongs to the same user as the notebook
        if self.knowledge_base_item and self.notebook:
            if self.knowledge_base_item.user != self.notebook.user:
                raise ValidationError(
                    "Knowledge base item must belong to the same user as the notebook"
                )

    def __str__(self):
        return f"{self.notebook.name} -> {self.knowledge_base_item.title}"
