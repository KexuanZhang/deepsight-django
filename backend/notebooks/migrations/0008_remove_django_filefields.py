# Generated migration to remove Django FileFields and complete MinIO migration

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notebooks', '0007_alter_knowledgebaseitem_file_metadata_and_more'),
    ]

    operations = [
        # Remove Django FileFields from URLProcessingResult
        migrations.RemoveField(
            model_name='urlprocessingresult',
            name='downloaded_file',
        ),
        
        # Remove Django FileFields from ProcessingJob
        migrations.RemoveField(
            model_name='processingjob',
            name='result_file',
        ),
        
        # Remove Django FileFields from KnowledgeBaseItem
        migrations.RemoveField(
            model_name='knowledgebaseitem',
            name='file',
        ),
        migrations.RemoveField(
            model_name='knowledgebaseitem',
            name='original_file',
        ),
        
        # Add MinIO storage fields to URLProcessingResult
        migrations.AddField(
            model_name='urlprocessingresult',
            name='storage_uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
        ),
        migrations.AddField(
            model_name='urlprocessingresult',
            name='downloaded_file_object_key',
            field=models.CharField(max_length=255, blank=True, null=True, db_index=True, 
                                 help_text="MinIO object key for downloaded media file"),
        ),
        migrations.AddField(
            model_name='urlprocessingresult',
            name='file_metadata',
            field=models.JSONField(default=dict, help_text="Downloaded file metadata"),
        ),
        
        # Add MinIO storage fields to ProcessingJob
        migrations.AddField(
            model_name='processingjob',
            name='storage_uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
        ),
        migrations.AddField(
            model_name='processingjob',
            name='result_file_object_key',
            field=models.CharField(max_length=255, blank=True, null=True, db_index=True,
                                 help_text="MinIO object key for generated result file"),
        ),
        migrations.AddField(
            model_name='processingjob',
            name='result_file_metadata',
            field=models.JSONField(default=dict, help_text="Result file metadata"),
        ),
        
        # Create new indexes for MinIO object key lookups
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_urlprocessingresult_storage_uuid ON notebooks_urlprocessingresult(storage_uuid);",
            reverse_sql="DROP INDEX IF EXISTS idx_urlprocessingresult_storage_uuid;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_urlprocessingresult_downloaded_file_object_key ON notebooks_urlprocessingresult(downloaded_file_object_key) WHERE downloaded_file_object_key IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_urlprocessingresult_downloaded_file_object_key;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_processingjob_storage_uuid ON notebooks_processingjob(storage_uuid);",
            reverse_sql="DROP INDEX IF EXISTS idx_processingjob_storage_uuid;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_processingjob_result_file_object_key ON notebooks_processingjob(result_file_object_key) WHERE result_file_object_key IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_processingjob_result_file_object_key;"
        ),
    ] 