# Generated migration for PodcastJob model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PodcastJob",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "job_id",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                (
                    "title",
                    models.CharField(default="Generated Podcast", max_length=200),
                ),
                ("description", models.TextField(blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("generating", "Generating"),
                            ("completed", "Completed"),
                            ("error", "Error"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("progress", models.TextField(default="Job queued for processing")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "audio_file",
                    models.FileField(
                        blank=True, null=True, upload_to="podcasts/audio/"
                    ),
                ),
                ("conversation_text", models.TextField(blank=True, default="")),
                ("error_message", models.TextField(blank=True, default="")),
                ("source_file_ids", models.JSONField(default=list)),
                ("source_metadata", models.JSONField(default=dict)),
                ("duration_seconds", models.IntegerField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="podcastjob",
            index=models.Index(fields=["status"], name="podcast_pod_status_6ec0e4_idx"),
        ),
        migrations.AddIndex(
            model_name="podcastjob",
            index=models.Index(
                fields=["user", "created_at"], name="podcast_pod_user_id_d04c5d_idx"
            ),
        ),
    ]
