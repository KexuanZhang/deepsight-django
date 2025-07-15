from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class PodcastJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("generating", "Generating"),
        ("completed", "Completed"),
        ("error", "Error"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Required linking to a notebook - breaking change for dev phase
    notebooks = models.ForeignKey(
        'notebooks.Notebook',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name='podcasts',
        help_text="Associated notebook (required)"
    )
    
    # Celery task tracking
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)

    # Job metadata
    title = models.CharField(max_length=200, default="Generated Podcast")
    description = models.TextField(blank=True, default="")

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    progress = models.TextField(default="Job queued for processing")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # MinIO-native storage (replaces Django FileField)
    audio_object_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        db_index=True,
        help_text="MinIO object key for generated audio file"
    )
    
    # File metadata stored in database
    file_metadata = models.JSONField(
        default=dict, 
        help_text="Audio file metadata (filename, size, duration, etc.)"
    )
    
    # Results
    conversation_text = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    # Source files reference (JSON field to store file IDs)
    source_file_ids = models.JSONField(default=list)
    source_metadata = models.JSONField(default=dict)

    # Audio metadata
    duration_seconds = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["user", "created_at"]),
            # MinIO-specific indexes
            models.Index(fields=["audio_object_key"]),
        ]

    def __str__(self):
        return f"PodcastJob {self.job_id} - {self.title} ({self.status})"

    def get_audio_url(self, expires=3600):
        """Get pre-signed URL for audio access"""
        if self.audio_object_key:
            try:
                from notebooks.utils.minio_backend import get_minio_backend
                backend = get_minio_backend()
                return backend.get_file_url(self.audio_object_key, expires)
            except Exception:
                return None
        return None

    @property
    def audio_url(self):
        """Legacy property for backward compatibility"""
        return self.get_audio_url()

    def get_result_dict(self):
        """Return result data as dictionary"""
        return {
            "job_id": str(self.job_id),
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "audio_url": self.get_audio_url(),
            "conversation_text": self.conversation_text,
            "duration_seconds": self.duration_seconds,
            "source_file_ids": self.source_file_ids,
            "created_at": self.created_at.isoformat(),
            "error_message": self.error_message,
        }
