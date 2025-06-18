import os
import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone


def upload_to_notebook(instance, filename):
    """
    Store uploads under MEDIA_ROOT/uploads/<notebook_id>/<filename>.
    """
    notebook_id = getattr(instance, 'notebook_id', 'misc')
    return os.path.join('uploads', str(notebook_id), filename)


class Notebook(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notebooks_app_notebooks",     # <— a different name
        related_query_name="notebooks_app_notebook"
    )
    name       = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UploadedFile(models.Model):
    """
    A raw file upload (pdf, txt, mp3, mp4, etc.) belonging to a Notebook.
    """
    upload_file_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True
    )
    notebook = models.ForeignKey(
        Notebook,
        on_delete=models.CASCADE,
        related_name='uploaded_files'
    )
    file = models.FileField(upload_to=upload_to_notebook)

    original_name = models.CharField(max_length=255)
    file_extension    = models.CharField(max_length=10, blank=True)
    content_type      = models.CharField(max_length=100, blank=True)
    file_size         = models.PositiveIntegerField(null=True, blank=True)

    STATUS_PENDING    = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED  = 'completed'
    STATUS_ERROR      = 'error'
    STATUS_CHOICES    = [
        (STATUS_PENDING,    'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED,  'Completed'),
        (STATUS_ERROR,      'Error'),
    ]
    status         = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    parsing_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text='Track parsing (validate → process → done)',
    )

    validation_result = models.JSONField(default=dict, blank=True)
    processing_result = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['upload_file_id']),
            models.Index(fields=['status']),
        ]

    def save(self, *args, **kwargs):
        # On first save, populate metadata
        if not self.pk:
            self.original_filename = os.path.basename(self.file.name)
            self.file_extension    = os.path.splitext(self.original_filename)[1].lower()
            self.file_size         = getattr(self.file, 'size', None)
            # content_type can be set by your view or processor
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.original_filename} ({self.upload_file_id})'

    def extracted_path(self) -> str:
        """
        Location on disk where the .md extraction for this file lives.
        """
        base = Path(settings.MEDIA_ROOT) / 'extracted' / 'files' / str(self.pk)
        base.mkdir(parents=True, exist_ok=True)
        return str(base / 'content.md')


class UrlLink(models.Model):
    """
    A URL‐based source (web page, YouTube, etc.) belonging to a Notebook.
    """
    notebook     = models.ForeignKey(
        Notebook,
        on_delete=models.CASCADE,
        related_name='url_links'
    )
    url          = models.URLField(max_length=2000)
    source_title = models.CharField(max_length=255, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.source_title or self.url

    def extracted_path(self) -> str:
        """
        Location on disk where the .md extraction for this URL lives.
        """
        base = Path(settings.MEDIA_ROOT) / 'extracted' / 'links' / str(self.pk)
        base.mkdir(parents=True, exist_ok=True)
        return str(base / 'content.md')


class NotebookSource(models.Model):
    """
    Generic “source” pointer for a Notebook: either an UploadedFile or a UrlLink.
    """
    SOURCE_FILE = 'file'
    SOURCE_LINK = 'link'
    SOURCE_TEXT = 'text'
    SOURCE_TYPES = [
        (SOURCE_FILE, 'Uploaded File'),
        (SOURCE_LINK, 'Web Link'),
        (SOURCE_TEXT, 'Pasted Text'),
    ]

    notebook    = models.ForeignKey(
        Notebook,
        on_delete=models.CASCADE,
        related_name='sources'
    )
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPES)
    created_at  = models.DateTimeField(default=timezone.now)

    # Points to one of the above two, depending on type
    uploaded_file = models.OneToOneField(
        UploadedFile,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='source'
    )
    url_link = models.OneToOneField(
        UrlLink,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='source'
    )

    raw_text = models.TextField(
        null=True,
        blank=True,
        help_text='User‐pasted text (if source_type == text)'
    )

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        # Ensure exactly one of uploaded_file / url_link / raw_text is set
        from django.core.exceptions import ValidationError

        if self.source_type == self.SOURCE_FILE and not self.uploaded_file:
            raise ValidationError('File required for file source.')
        if self.source_type == self.SOURCE_LINK and not self.url_link:
            raise ValidationError('URL required for link source.')
        if self.source_type == self.SOURCE_TEXT and not self.raw_text:
            raise ValidationError('Text required for text source.')

    def __str__(self):
        label = {
            self.SOURCE_FILE: self.uploaded_file.original_filename,
            self.SOURCE_LINK: self.url_link.source_title or self.url_link.url,
            self.SOURCE_TEXT: f'Text ({len(self.raw_text or "")} chars)',
        }.get(self.source_type, 'Unknown')
        return f'{self.notebook.name} → {label}'
