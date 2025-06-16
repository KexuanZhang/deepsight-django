# notebooks/models.py
import uuid
import os
from django.db import models
from django.conf import settings
from django.utils import timezone

def upload_to_notebook(instance, filename):
    # e.g. uploads/notebooks/<notebook_id>/<uuid>_<orig_fn>
    ext = os.path.splitext(filename)[1]
    return f"uploads/notebooks/{instance.notebook.id}/{instance.upload_file_id}{ext}"

class Notebook(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notebooks"
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UploadedFile(models.Model):
    # Unique identifier you can return immediately to the frontend
    upload_file_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True
    )

    notebook = models.ForeignKey(
        Notebook,
        on_delete=models.CASCADE,
        related_name="uploaded_files"
    )
    # The actual file saved on disk/S3/etc.
    file = models.FileField(upload_to=upload_to_notebook)

    # Metadata populated either on save() or in your upload processor
    original_filename = models.CharField(max_length=255)
    file_extension   = models.CharField(max_length=10, blank=True)
    content_type     = models.CharField(max_length=100, blank=True)
    file_size        = models.PositiveIntegerField(null=True, blank=True)

    # Processing status
    STATUS_PENDING    = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED  = "completed"
    STATUS_ERROR      = "error"
    STATUS_CHOICES = [
        (STATUS_PENDING,    "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED,  "Completed"),
        (STATUS_ERROR,      "Error"),
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
        help_text="Track parsing (validation → content checks → completed)",
    )

    # JSON blobs for validator output + processing results
    validation_result = models.JSONField(
        default=dict,
        blank=True,
        help_text="Output of FileValidator.validate_file()"
    )
    processing_result = models.JSONField(
        default=dict,
        blank=True,
        help_text="Output of UploadProcessor.process_upload()"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["upload_file_id"]),
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        # Populate extension, content_type and size on first save
        if not self.pk:
            self.original_filename = os.path.basename(self.file.name)
            self.file_extension = os.path.splitext(self.original_filename)[1].lower()
            # content_type will be set by your view/processor
            try:
                self.file_size = self.file.size
            except Exception:
                self.file_size = None
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.original_filename} ({self.upload_file_id})"

class NotebookSource(models.Model):
    SOURCE_TYPE_PUBLICATION = 'publication'
    SOURCE_TYPE_EVENT = 'event'
    SOURCE_TYPE_CHOICES = [
        (SOURCE_TYPE_PUBLICATION, 'Publication'),
        (SOURCE_TYPE_EVENT, 'Event'),
    ]

    source_id = models.AutoField(primary_key=True)
    notebook = models.ForeignKey(
        Notebook,
        on_delete=models.CASCADE,
        related_name='sources'
    )
    source_type = models.CharField(
        max_length=50,
        choices=SOURCE_TYPE_CHOICES
    )
    # publication = models.ForeignKey(
    #     'publications.Publication',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True
    # )
    # event = models.ForeignKey(
    #     'events.Event',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True
    # )

    def __str__(self):
        return f"{self.get_source_type_display()} in {self.notebook.name}"
