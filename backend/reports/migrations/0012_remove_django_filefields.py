# Generated migration to remove Django FileFields and complete MinIO migration for reports

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0010_merge_20250710_1949'),
    ]

    operations = [
        # Remove Django FileField from Report
        migrations.RemoveField(
            model_name='report',
            name='main_report_file',
        ),
        
        # Remove the old figure_data_path CharField
        migrations.RemoveField(
            model_name='report',
            name='figure_data_path',
        ),
        
        # Add MinIO storage fields to Report
        migrations.AddField(
            model_name='report',
            name='storage_uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
        ),
        migrations.AddField(
            model_name='report',
            name='main_report_object_key',
            field=models.CharField(max_length=255, blank=True, null=True, db_index=True,
                                 help_text="MinIO object key for main report file"),
        ),
        migrations.AddField(
            model_name='report',
            name='file_metadata',
            field=models.JSONField(default=dict, help_text="All file paths, names, sizes, etc."),
        ),
        migrations.AddField(
            model_name='report',
            name='figure_data_object_key',
            field=models.CharField(max_length=255, blank=True, null=True,
                                 help_text="MinIO object key for combined figure_data.json file"),
        ),
        
        # Update generated_files field help text to reflect object keys
        migrations.AlterField(
            model_name='report',
            name='generated_files',
            field=models.JSONField(default=list, blank=True, 
                                 help_text="List of generated file object keys"),
        ),
        
        # Create new indexes for MinIO object key lookups
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_report_storage_uuid ON reports_report(storage_uuid);",
            reverse_sql="DROP INDEX IF EXISTS idx_report_storage_uuid;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_report_main_report_object_key ON reports_report(main_report_object_key) WHERE main_report_object_key IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_report_main_report_object_key;"
        ),
    ] 