# Generated consolidated migration reflecting current model state

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
            name='Notebook',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notebooks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Notebook',
                'verbose_name_plural': 'Notebooks',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='KnowledgeBaseItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('processing_status', models.CharField(choices=[('processing', 'Processing'), ('done', 'Done'), ('failed', 'Failed')], default='processing', help_text='Processing status of this knowledge base item', max_length=20)),
                ('title', models.CharField(help_text='Title or identifier for this knowledge item', max_length=512)),
                ('content_type', models.CharField(choices=[('text', 'Text Content'), ('document', 'Document'), ('webpage', 'Webpage'), ('media', 'Media File')], default='text', max_length=50)),
                ('content', models.TextField(blank=True, help_text='Inline text content if not stored as file')),
                ('metadata', models.JSONField(blank=True, help_text='Source metadata, processing info, etc.', null=True)),
                ('source_hash', models.CharField(blank=True, db_index=True, help_text='Hash of original content to detect duplicates', max_length=64)),
                ('tags', models.JSONField(default=list, help_text='Tags for categorization and search')),
                ('notes', models.TextField(blank=True, help_text='User notes about this knowledge item')),
                ('file_object_key', models.CharField(blank=True, db_index=True, help_text='MinIO object key for processed content file', max_length=255, null=True)),
                ('original_file_object_key', models.CharField(blank=True, db_index=True, help_text='MinIO object key for original file', max_length=255, null=True)),
                ('file_metadata', models.JSONField(default=dict, help_text='File metadata stored in database (replaces file system metadata)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('notebook', models.ForeignKey(help_text='Notebook this knowledge item belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='knowledge_base_items', to='notebooks.notebook')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BatchJob',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('job_type', models.CharField(choices=[('url_parse', 'URL Parse'), ('url_parse_media', 'URL Parse with Media'), ('file_upload', 'File Upload')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed'), ('partially_completed', 'Partially Completed')], default='pending', max_length=20)),
                ('total_items', models.IntegerField(default=0)),
                ('completed_items', models.IntegerField(default=0)),
                ('failed_items', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('notebook', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='batch_jobs', to='notebooks.notebook')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BatchJobItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('item_data', models.JSONField(help_text='URL, filename, or other item-specific data')),
                ('upload_id', models.CharField(blank=True, help_text='Upload/processing ID for status tracking', max_length=64)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('result_data', models.JSONField(blank=True, help_text='Processing results', null=True)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('batch_job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='notebooks.batchjob')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='NotebookChatMessage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('sender', models.CharField(choices=[('user', 'User'), ('assistant', 'Assistant')], max_length=10)),
                ('message', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('notebook', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_messages', to='notebooks.notebook')),
            ],
            options={
                'ordering': ['timestamp'],
            },
        ),
        migrations.CreateModel(
            name='KnowledgeBaseImage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('figure_id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='Unique figure identifier, different from primary key')),
                ('image_caption', models.TextField(blank=True, help_text='Description or caption for the image')),
                ('minio_object_key', models.CharField(db_index=True, help_text='MinIO object key for the image file', max_length=255)),
                ('image_metadata', models.JSONField(default=dict, help_text='Image metadata including dimensions, format, size, etc.')),
                ('content_type', models.CharField(blank=True, help_text='MIME type of the image (image/png, image/jpeg, etc.)', max_length=100)),
                ('file_size', models.PositiveIntegerField(default=0, help_text='File size in bytes')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('knowledge_base_item', models.ForeignKey(help_text='Knowledge base item this image belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='images', to='notebooks.knowledgebaseitem')),
            ],
            options={
                'verbose_name': 'Knowledge Base Image',
                'verbose_name_plural': 'Knowledge Base Images',
                'ordering': ['knowledge_base_item', 'created_at'],
            },
        ),
        # Add indexes for optimal query performance
        migrations.AddIndex(
            model_name='knowledgebaseitem',
            index=models.Index(fields=['notebook', '-created_at'], name='notebooks_kb_notebook_created_idx'),
        ),
        migrations.AddIndex(
            model_name='knowledgebaseitem',
            index=models.Index(fields=['notebook', 'source_hash'], name='notebooks_kb_notebook_hash_idx'),
        ),
        migrations.AddIndex(
            model_name='knowledgebaseitem',
            index=models.Index(fields=['notebook', 'content_type'], name='notebooks_kb_notebook_type_idx'),
        ),
        migrations.AddIndex(
            model_name='knowledgebaseitem',
            index=models.Index(fields=['file_object_key'], name='notebooks_kb_file_key_idx'),
        ),
        migrations.AddIndex(
            model_name='knowledgebaseitem',
            index=models.Index(fields=['original_file_object_key'], name='notebooks_kb_orig_file_key_idx'),
        ),
        migrations.AddIndex(
            model_name='knowledgebaseimage',
            index=models.Index(fields=['knowledge_base_item', 'created_at'], name='notebooks_kbi_kb_created_idx'),
        ),
        migrations.AddIndex(
            model_name='knowledgebaseimage',
            index=models.Index(fields=['minio_object_key'], name='notebooks_kbi_minio_key_idx'),
        ),
    ]