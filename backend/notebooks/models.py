import os
import mimetypes

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
    A generic “source” that the user adds to a notebook:
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


class UploadedFile(models.Model):
    """
    Stores any binary the user uploaded for a Source of type “file.”
    """
    source = models.OneToOneField(
        Source,
        on_delete=models.CASCADE,
        related_name="upload",
    )
    file = models.FileField(
        upload_to="source_uploads/%Y/%m/%d/",
        help_text="Original user-uploaded file (PDF, MP3, MP4, etc.)",
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
    """
    source = models.OneToOneField(
        Source,
        on_delete=models.CASCADE,
        related_name="pasted_text_file",
    )
    file = models.FileField(
        upload_to="pasted_text/%Y/%m/%d/",
        validators=[FileExtensionValidator(allowed_extensions=["txt"] )],
        help_text="Auto-generated .txt of pasted content",
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
        upload_to="downloaded_media/%Y/%m/%d/",
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
        upload_to="processing_results/%Y/%m/%d/",
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


# class SearchResult(models.Model):
#     """
#     (Optional) Stores snippets when the user “searches existing” sources.
#     """
#     source = models.ForeignKey(
#         Source,
#         on_delete=models.CASCADE,
#         related_name="search_results",
#     )
#     snippet = models.TextField()
#     metadata = models.JSONField(
#         blank=True,
#         null=True,
#         help_text="Optional structured metadata about this snippet",
#     )
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.snippet[:75] + ("…" if len(self.snippet) > 75 else "")


class KnowledgeItem(models.Model):
    """
    The final chunks of text or standalone .md/.txt files
    imported into the notebook’s long-term store.
    """
    notebook = models.ForeignKey(
        Notebook,
        on_delete=models.CASCADE,
        related_name="knowledge_items",
    )
    source = models.ForeignKey(
        Source,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="knowledge_items",
    )
    content = models.TextField(
        blank=True,
        help_text="Inline text for imported/pasted/URL-converted items",
    )
    file = models.FileField(
        upload_to="knowledge_items/%Y/%m/%d/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["md", "txt"])],
        help_text="Standalone .md or .txt file, if this item was stored on disk",
    )
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Optional structural metadata (headings, timestamps, etc.)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["notebook", "source"]),
        ]

    def clean(self):
        super().clean()
        if not (self.content or self.file):
            raise ValidationError("Either `content` or `file` must be set.")
        if self.content and self.file:
            raise ValidationError("Provide either `content` or `file`, not both.")

    def __str__(self):
        if self.file:
            return os.path.basename(self.file.name)
        return (self.content[:75] + "…") if len(self.content) > 75 else self.content
