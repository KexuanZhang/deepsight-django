# Generated migration to remove Django FileFields and complete MinIO migration for podcast

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('podcast', '0002_alter_podcastjob_audio_file'),
    ]

    operations = [
        # Remove Django FileField from PodcastJob
        migrations.RemoveField(
            model_name='podcastjob',
            name='audio_file',
        ),
        
        # Add MinIO storage fields to PodcastJob
        migrations.AddField(
            model_name='podcastjob',
            name='storage_uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
        ),
        migrations.AddField(
            model_name='podcastjob',
            name='audio_object_key',
            field=models.CharField(max_length=255, blank=True, null=True, db_index=True,
                                 help_text="MinIO object key for generated audio file"),
        ),
        migrations.AddField(
            model_name='podcastjob',
            name='file_metadata',
            field=models.JSONField(default=dict, 
                                 help_text="Audio file metadata (filename, size, duration, etc.)"),
        ),
        
        # Create new indexes for MinIO object key lookups
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_podcastjob_storage_uuid ON podcast_podcastjob(storage_uuid);",
            reverse_sql="DROP INDEX IF EXISTS idx_podcastjob_storage_uuid;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_podcastjob_audio_object_key ON podcast_podcastjob(audio_object_key) WHERE audio_object_key IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_podcastjob_audio_object_key;"
        ),
    ] 