# Generated migration for MinIO integration

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notebooks', '0001_initial'),
    ]

    operations = [
        # Add MinIO-specific fields to KnowledgeBaseItem
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='storage_uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
        ),
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='file_object_key',
            field=models.CharField(max_length=255, blank=True, null=True, db_index=True, 
                                 help_text="MinIO object key for processed content file"),
        ),
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='original_file_object_key',
            field=models.CharField(max_length=255, blank=True, null=True, db_index=True,
                                 help_text="MinIO object key for original file"),
        ),
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='file_metadata',
            field=models.JSONField(default=dict, help_text="File metadata stored in database"),
        ),
        
        # Create indexes for MinIO object key lookups
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_knowledgebaseitem_storage_uuid ON notebooks_knowledgebaseitem(storage_uuid);",
            reverse_sql="DROP INDEX IF EXISTS idx_knowledgebaseitem_storage_uuid;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_knowledgebaseitem_file_object_key ON notebooks_knowledgebaseitem(file_object_key) WHERE file_object_key IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_knowledgebaseitem_file_object_key;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_knowledgebaseitem_original_file_object_key ON notebooks_knowledgebaseitem(original_file_object_key) WHERE original_file_object_key IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_knowledgebaseitem_original_file_object_key;"
        ),
        
        # Create composite index for object key queries
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_knowledgebaseitem_object_keys ON notebooks_knowledgebaseitem(file_object_key, original_file_object_key) WHERE file_object_key IS NOT NULL OR original_file_object_key IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_knowledgebaseitem_object_keys;"
        ),
    ]