from django.db import models
from django.contrib.auth import get_user_model
import uuid
from storages.backends.s3boto3 import S3Boto3Storage
import json

User = get_user_model()


class PodcastJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("generating", "Generating"),
        ("completed", "Completed"),
        ("error", "Error"),
        ("cancelled", "Cancelled"),
    ]

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

    # Results
    audio_file = models.FileField(null=True, blank=True, storage=S3Boto3Storage(),)
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
            models.Index(fields=["notebooks", "created_at"]),
        ]

    def __str__(self):
        return f"Podcast Job {self.job_id} - {self.title} (Notebook: {self.notebooks.title})"

    @property
    def audio_url(self):
        """Return the audio file URL if available"""
        if self.audio_file:
            return self.audio_file.url
        return None

    def get_result_dict(self):
        """Return job result as dictionary for API responses"""
        return {
            "job_id": str(self.job_id),
            "title": self.title,
            "description": self.description,
            "audio_url": self.audio_url,
            "source_files": self.source_metadata,
            "conversation_text": self.conversation_text,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "notebook_id": self.notebooks.pk,
        }
