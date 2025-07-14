# **Detailed MinIO Migration Plan for DeepSight Django Project**

## **🎯 Executive Summary**

This plan outlines the complete migration from local file storage to MinIO object storage for the DeepSight Django project. The migration will provide better scalability, cloud-native storage, and improved file management capabilities while maintaining the existing organized file structure.

## **📊 Current State Analysis**

### **Current Architecture**
- **Storage**: Local filesystem with organized directory structure
- **File Types**: PDFs, audio files, images, markdown content, reports, podcasts
- **Organization**: User-based hierarchical structure with temporal organization
- **Services**: FileStorageService, StorageService, DeepSightStorageConfig
- **Dependencies**: Django default storage, local file operations

### **Key Limitations**
- Single point of failure (local storage)
- No cloud scalability
- Limited concurrent access
- No built-in backup/replication
- Deployment challenges in containerized environments

---

## **🏗️ MinIO Architecture Design**

### **MinIO Bucket Strategy**

```

```

### **Storage Backend Configuration**

```python
# New MinIO Configuration
MINIO_SETTINGS = {
    'ENDPOINT': 'localhost:9000',  # or cloud endpoint
    'ACCESS_KEY': 'minioadmin',
    'SECRET_KEY': 'minioadmin',
    'BUCKET_NAME': 'deepsight-users',
    'SECURE': False,  # True for HTTPS
    'REGION': 'us-east-1',
}

# Storage Backend Selection
STORAGE_BACKEND = 'minio'  # or 'local' for backward compatibility
```

---

## **🗄️ Database Integration with MinIO File Storage**

### **Current Database Schema Overview**

The Django project uses a sophisticated database schema that's well-designed for MinIO integration:

#### **Core Models with MinIO-Native File Storage**

```python
# Key models handling file storage - MinIO-Native approach
import uuid
from django.db import models
from django.contrib.auth.models import User

class KnowledgeBaseItem(models.Model):
    # MinIO-native storage - no FileFields needed
    storage_uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    # Store MinIO object keys directly
    file_object_key = models.CharField(max_length=255, blank=True, null=True, db_index=True)           # Processed content object key
    original_file_object_key = models.CharField(max_length=255, blank=True, null=True, db_index=True)  # Original file object key
    
    # File metadata stored in database (replaces file system metadata)
    file_metadata = models.JSONField(default=dict)                      # filename, size, content_type, etc.
    
    # Database fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=50)
    content = models.TextField(blank=True)                              # Fallback content
    metadata = models.JSONField(default=dict)                          # Processing metadata
    source_hash = models.CharField(max_length=64, db_index=True)       # Deduplication
    tags = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'source_hash']),               # Deduplication index
            models.Index(fields=['user', 'content_type']),
            models.Index(fields=['storage_uuid']),                      # For MinIO lookups
            models.Index(fields=['file_object_key']),                   # Direct MinIO access
            models.Index(fields=['original_file_object_key']),          # Direct MinIO access
        ]
    
    def get_file_url(self, expires=3600):
        """Get pre-signed URL for processed file"""
        if self.file_object_key:
            from .utils.minio_backend import MinIOBackend
            backend = MinIOBackend()
            return backend.get_file_url(self.file_object_key, expires)
        return None
    
    def get_original_file_url(self, expires=3600):
        """Get pre-signed URL for original file"""
        if self.original_file_object_key:
            from .utils.minio_backend import MinIOBackend
            backend = MinIOBackend()
            return backend.get_file_url(self.original_file_object_key, expires)
        return None

class Report(models.Model):
    # MinIO-native storage
    storage_uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    # Store MinIO object keys directly
    main_report_object_key = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    
    # All file metadata stored in JSON (replaces multiple file fields)
    file_metadata = models.JSONField(default=dict)                     # All file paths, names, sizes, etc.
    
    # Database fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE, null=True)
    job_id = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['job_id']),
            models.Index(fields=['storage_uuid']),                      # For MinIO lookups
            models.Index(fields=['main_report_object_key']),            # Direct MinIO access
        ]
    
    def get_report_url(self, expires=3600):
        """Get pre-signed URL for report access"""
        if self.main_report_object_key:
            from .utils.minio_backend import MinIOBackend
            backend = MinIOBackend()
            return backend.get_file_url(self.main_report_object_key, expires)
        return None

class PodcastJob(models.Model):
    # MinIO-native storage
    storage_uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    # Store MinIO object key directly
    audio_object_key = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    
    # File metadata stored in database
    file_metadata = models.JSONField(default=dict)                     # filename, size, duration, etc.
    
    # Database fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, db_index=True)
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE)
    job_id = models.UUIDField(default=uuid.uuid4, unique=True)
    source_file_ids = models.JSONField(default=list)                   # References to source files
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['storage_uuid']),                      # For MinIO lookups
            models.Index(fields=['audio_object_key']),                  # Direct MinIO access
        ]
    
    def get_audio_url(self, expires=3600):
        """Get pre-signed URL for audio access"""
        if self.audio_object_key:
            from .utils.minio_backend import MinIOBackend
            backend = MinIOBackend()
            return backend.get_file_url(self.audio_object_key, expires)
        return None
```

### **Database-MinIO Integration Architecture**

#### **MinIO-Native Object Key Storage Strategy**

The database stores **MinIO-generated object keys** directly - no path functions needed:

```python
# Database stores MinIO auto-generated object keys like:
# "user_id/kb/20250711_143022_a1b2c3d4e5f6789a_8f4e2a1b.pdf"           # Knowledge base files
# "user_id/reports/20250711_143030_c3d4e5f6789abcde_ah6g4c3d.pdf"       # Generated reports  
# "user_id/podcasts/20250711_143035_d4e5f6789abcdef0_bi7h5d4e.mp3"      # Podcast audio
# "user_id/kb-images/20250711_143040_e5f6789abcdef012_cj8i6e5f.png"     # Extracted images

# MinIO handles the complete object storage:
# s3://deepsight-users/kb/20250711_143022_a1b2c3d4e5f6789a_8f4e2a1b.pdf
```

#### **No Upload Path Functions Needed**

```python
# ❌ OLD WAY: Custom upload_to functions
def user_knowledge_base_path(instance, filename):
    return f"users/u_{instance.user_id}/knowledge-base/{year_month}/f_{instance.id}/{filename}"

class KnowledgeBaseItem(models.Model):
    file = models.FileField(upload_to=user_knowledge_base_path)  # Complex logic

# ✅ NEW WAY: MinIO handles path generation automatically
class KnowledgeBaseItem(models.Model):
    # No FileFields or upload_to functions needed!
    file_object_key = models.CharField(max_length=255, db_index=True)
    file_metadata = models.JSONField(default=dict)
    
    # MinIO auto-generates optimal object keys:
    # "kb/20250711_143022_a1b2c3d4e5f6789a_8f4e2a1b.pdf"

# File upload workflow:
def upload_file(file_data):
    # 1. Let MinIO generate the object key
    object_key = minio_backend.save_file_with_auto_key(
        content=file_data,
        filename="document.pdf",
        prefix="kb"
    )
    
    # 2. Store MinIO-generated key in database
    kb_item.file_object_key = object_key  # "kb/20250711_143022_a1b2c3d4e5f6789a_8f4e2a1b.pdf"
    kb_item.save()
```

### **Database Schema Optimizations for MinIO**

#### **MinIO-Optimized Database Indexes**

```sql
-- Core indexes for MinIO-native operations
CREATE INDEX idx_knowledgebaseitem_user_created ON notebooks_knowledgebaseitem(user_id, created_at);
CREATE INDEX idx_knowledgebaseitem_user_hash ON notebooks_knowledgebaseitem(user_id, source_hash);
CREATE INDEX idx_knowledgebaseitem_user_type ON notebooks_knowledgebaseitem(user_id, content_type);

-- MinIO object key indexes for direct access
CREATE INDEX idx_knowledgebaseitem_storage_uuid ON notebooks_knowledgebaseitem(storage_uuid);
CREATE INDEX idx_knowledgebaseitem_file_object_key ON notebooks_knowledgebaseitem(file_object_key);
CREATE INDEX idx_knowledgebaseitem_original_file_object_key ON notebooks_knowledgebaseitem(original_file_object_key);

-- Report MinIO indexes
CREATE INDEX idx_report_user_status ON reports_report(user_id, status);
CREATE INDEX idx_report_job_id ON reports_report(job_id);
CREATE INDEX idx_report_storage_uuid ON reports_report(storage_uuid);
CREATE INDEX idx_report_main_report_object_key ON reports_report(main_report_object_key);

-- Podcast MinIO indexes
CREATE INDEX idx_podcastjob_user_created ON podcast_podcastjob(user_id, created_at);
CREATE INDEX idx_podcastjob_notebook_created ON podcast_podcastjob(notebook_id, created_at);
CREATE INDEX idx_podcastjob_storage_uuid ON podcast_podcastjob(storage_uuid);
CREATE INDEX idx_podcastjob_audio_object_key ON podcast_podcastjob(audio_object_key);
```

#### **MinIO-Specific Index Migration**

```python
# Migration for MinIO-native indexes
class Migration(migrations.Migration):
    dependencies = [
        ('notebooks', '0001_initial'),
    ]
    
    operations = [
        # Add MinIO-specific fields
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='storage_uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
        ),
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='file_object_key',
            field=models.CharField(max_length=255, blank=True, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='original_file_object_key',
            field=models.CharField(max_length=255, blank=True, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='file_metadata',
            field=models.JSONField(default=dict),
        ),
        
        # Index for object key lookups
        migrations.RunSQL(
            "CREATE INDEX idx_knowledgebaseitem_object_keys ON notebooks_knowledgebaseitem(file_object_key, original_file_object_key) WHERE file_object_key IS NOT NULL OR original_file_object_key IS NOT NULL;",
            reverse_sql="DROP INDEX idx_knowledgebaseitem_object_keys;"
        ),
        
        # Index for MinIO prefix queries
        migrations.RunSQL(
            "CREATE INDEX idx_knowledgebaseitem_prefix_search ON notebooks_knowledgebaseitem USING gin ((file_object_key || ' ' || original_file_object_key) gin_trgm_ops);",
            reverse_sql="DROP INDEX idx_knowledgebaseitem_prefix_search;"
        ),
    ]
```

### **Database-MinIO Workflow Examples**

#### **1. MinIO-Native File Upload and Storage Workflow**

```python
def upload_file_workflow(user, file_data, notebook_id):
    """Complete MinIO-native file upload workflow - no custom paths needed"""
    
    # Step 1: Create database record (no file fields yet)
    kb_item = KnowledgeBaseItem.objects.create(
        user=user,
        title=file_data['title'],
        content_type='document',
        metadata={
            'processing_metadata': {
                'upload_timestamp': timezone.now().isoformat(),
                'source': 'api_upload'
            }
        }
        # storage_uuid auto-generated by Django
    )
    
    # Step 2: Let MinIO generate the object key automatically
    minio_backend = MinIOBackend()
    object_key = minio_backend.save_file_with_auto_key(
        content=file_data['content'],
        filename=file_data['filename'],
        prefix='kb',  # Knowledge base prefix
        metadata={
            'user_id': str(user.id),
            'kb_item_id': str(kb_item.id),
            'file_type': 'original_file',
            'upload_source': 'api'
        }
    )
    
    # Step 3: Store MinIO-generated object key in database
    kb_item.original_file_object_key = object_key
    kb_item.file_metadata = {
        'filename': file_data['filename'],
        'size': file_data['size'],
        'content_type': file_data.get('content_type', 'application/octet-stream'),
        'upload_timestamp': timezone.now().isoformat()
    }
    kb_item.save()
    
    # MinIO auto-generated object key example:
    # "kb/20250711_143022_a1b2c3d4e5f6789a_8f4e2a1b.pdf"
    
    # Step 4: Link to notebook
    KnowledgeItem.objects.create(
        notebook_id=notebook_id,
        knowledge_base_item=kb_item,
        notes=f"Uploaded from {file_data['filename']}"
    )
    
    return kb_item.id
```

#### **2. MinIO-Native File Retrieval Workflow**

```python
def get_file_workflow(user, file_id):
    """Retrieve file using MinIO object key - simple and direct"""
    
    # Step 1: Database query with user isolation
    kb_item = KnowledgeBaseItem.objects.select_related('user').get(
        id=file_id,
        user=user
    )
    
    # Step 2: Get MinIO object key from database (no path calculations)
    object_key = kb_item.original_file_object_key
    # Example: "kb/20250711_143022_a1b2c3d4e5f6789a_8f4e2a1b.pdf"
    
    if not object_key:
        raise ValueError("No file associated with this item")
    
    # Step 3: Generate pre-signed URL directly from object key
    minio_backend = MinIOBackend()
    file_url = minio_backend.get_file_url(object_key, expires=3600)
    
    return {
        'file_url': file_url,
        'filename': kb_item.file_metadata.get('filename', 'file'),
        'size': kb_item.file_metadata.get('size', 0),
        'content_type': kb_item.file_metadata.get('content_type', 'application/octet-stream'),
        'expires_in': 3600
    }
    
    # Alternative: Use model method for cleaner code
    # file_url = kb_item.get_original_file_url(expires=3600)
```

#### **3. MinIO-Native Bulk File Migration Workflow**

```python
def migrate_user_files_to_minio_native(user_id, batch_size=100):
    """Migrate user's files from old FileField system to MinIO-native approach"""
    
    # Step 1: Query database for user's files (old FileField format)
    old_files = KnowledgeBaseItem.objects.filter(
        user_id=user_id,
        original_file_object_key__isnull=True  # Not yet migrated
    ).select_related('user')
    
    migrated_count = 0
    minio_backend = MinIOBackend()
    
    # Step 2: Process in batches
    for batch in old_files.iterator(chunk_size=batch_size):
        with transaction.atomic():
            try:
                # Step 3: Read old file content
                old_file_content = None
                if hasattr(batch, 'original_file') and batch.original_file:
                    try:
                        with batch.original_file.open('rb') as f:
                            old_file_content = f.read()
                    except (FileNotFoundError, OSError):
                        continue  # Skip missing files
                
                if not old_file_content:
                    continue
                
                # Step 4: Let MinIO generate new object key
                original_filename = batch.metadata.get('original_filename', 'migrated_file')
                new_object_key = minio_backend.save_file_with_auto_key(
                    content=old_file_content,
                    filename=original_filename,
                    prefix='kb',
                    metadata={
                        'user_id': str(user_id),
                        'kb_item_id': str(batch.id),
                        'migration_source': 'file_field_migration',
                        'migration_timestamp': timezone.now().isoformat()
                    }
                )
                
                # Step 5: Update database with MinIO object key
                batch.original_file_object_key = new_object_key
                batch.file_metadata = {
                    'filename': original_filename,
                    'size': len(old_file_content),
                    'content_type': batch.metadata.get('content_type', 'application/octet-stream'),
                    'migrated_from': 'file_field',
                    'migration_timestamp': timezone.now().isoformat()
                }
                batch.save()
                
                migrated_count += 1
                
                # Step 6: Clean up old file field (optional)
                # batch.original_file.delete(save=False)
                
            except Exception as e:
                print(f"Failed to migrate item {batch.id}: {str(e)}")
                continue
    
    return migrated_count
```

#### **4. MinIO-Native File Deletion Workflow**

```python
def delete_file_workflow(user, file_id):
    """Delete file from both database and MinIO using object keys"""
    
    # Step 1: Get file record with user permission check
    kb_item = KnowledgeBaseItem.objects.get(
        id=file_id,
        user=user
    )
    
    # Step 2: Delete from MinIO using object keys
    minio_backend = MinIOBackend()
    
    if kb_item.original_file_object_key:
        minio_backend.delete_file(kb_item.original_file_object_key)
    
    if kb_item.file_object_key:
        minio_backend.delete_file(kb_item.file_object_key)
    
    # Step 3: Delete associated images if any
    if 'image_objects' in kb_item.metadata:
        for image_obj in kb_item.metadata['image_objects']:
            if 'object_key' in image_obj:
                minio_backend.delete_file(image_obj['object_key'])
    
    # Step 4: Delete from database (cascades to related records)
    kb_item.delete()
    
    return True
```

### **Database Migration Strategy for MinIO**

#### **Phase 1: Schema Validation**
```python
# Check current schema compatibility
def validate_schema_for_minio():
    """Validate database schema is MinIO-ready"""
    
    # Check file field configurations
    file_fields = [
        ('KnowledgeBaseItem', 'file'),
        ('KnowledgeBaseItem', 'original_file'),
        ('Report', 'main_report_file'),
        ('PodcastJob', 'audio_file'),
    ]
    
    for model_name, field_name in file_fields:
        model = apps.get_model('notebooks', model_name)
        field = model._meta.get_field(field_name)
        
        assert isinstance(field, models.FileField), f"{model_name}.{field_name} must be FileField"
        assert field.upload_to, f"{model_name}.{field_name} must have upload_to function"
        
    print("✅ Schema is MinIO-ready")
```

#### **Phase 2: Data Migration**
```python
# Django management command for data migration
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Migrate files while preserving database paths
        for kb_item in KnowledgeBaseItem.objects.filter(original_file__isnull=False):
            # Path in database remains the same
            # Only the storage backend changes
            old_storage_path = kb_item.original_file.path
            minio_object_key = kb_item.original_file.name
            
            # Upload to MinIO with same object key
            self.upload_to_minio(old_storage_path, minio_object_key)
```

#### **Phase 3: Rollback Strategy**
```python
# Rollback mechanism preserves database integrity
def rollback_to_local_storage():
    """Rollback from MinIO to local storage"""
    
    # Download files from MinIO back to local storage
    for kb_item in KnowledgeBaseItem.objects.filter(original_file__isnull=False):
        minio_path = kb_item.original_file.name
        local_path = os.path.join(settings.MEDIA_ROOT, minio_path)
        
        # Download from MinIO
        minio_backend = MinIOBackend()
        file_content = minio_backend.get_file_content(minio_path)
        
        # Save to local filesystem
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'wb') as f:
            f.write(file_content)
    
    # No database changes needed - paths remain the same
```

### **Key Benefits of Current Database Design**

1. **Storage Backend Agnostic**: Paths work with any storage backend
2. **User Isolation**: Built-in user-based file isolation
3. **Efficient Queries**: Optimized indexes for common operations
4. **Deduplication**: Hash-based content deduplication
5. **Metadata Support**: Rich metadata storage for files
6. **Referential Integrity**: Proper foreign key relationships
7. **Migration Friendly**: Minimal database changes required

---

## **🎯 MinIO-Native Path Management (Recommended Approach)**

### **Problem with Current Custom Path Functions**

The current approach uses custom `upload_to` functions that create hierarchical paths:
```python
# Current approach - custom path generation
def user_knowledge_base_path(instance, filename):
    return f"users/u_{instance.user_id}/knowledge-base/{year_month}/f_{instance.id}/{filename}"
```

**Issues with this approach:**
- **Tight coupling** between application logic and storage paths
- **Complex path generation** that's hard to maintain
- **Not cloud-native** - doesn't leverage MinIO's strengths
- **Performance overhead** from path calculations
- **Limited scalability** with deep directory structures

### **MinIO Best Practices for Path Management**

MinIO recommends **flat object key structure** with meaningful prefixes:

```python
# MinIO-native approach - flat structure with prefixes
# Object keys: {prefix}/{uuid}/{filename}
# Examples:
# kb-files/550e8400-e29b-41d4-a716-446655440000/document.pdf
# reports/550e8400-e29b-41d4-a716-446655440001/report.pdf
# podcasts/550e8400-e29b-41d4-a716-446655440002/audio.mp3
```

### **Proposed MinIO-Native Architecture**

#### **1. Simplified Object Key Structure**

```python
# MinIO-native object keys
OBJECT_KEY_PATTERNS = {
    'knowledge_base': 'kb/{uuid}',
    'reports': 'reports/{uuid}',
    'podcasts': 'podcasts/{uuid}',
    'temp_uploads': 'temp/{uuid}',
}

# Examples:
# kb/550e8400-e29b-41d4-a716-446655440000/document.pdf
# reports/550e8400-e29b-41d4-a716-446655440001/report.pdf
# podcasts/550e8400-e29b-41d4-a716-446655440002/audio.mp3
```

#### **2. Fully MinIO-Native Django Models (No Custom Path Functions)**

```python
# backend/notebooks/models.py
import uuid
from django.db import models
from django.contrib.auth.models import User

class KnowledgeBaseItem(models.Model):
    # UUID serves as the primary object identifier - no upload_to needed!
    storage_uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    # Store object keys directly - let MinIO handle the paths
    file_object_key = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    original_file_object_key = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    
    # File metadata stored in database
    file_metadata = models.JSONField(default=dict)  # filename, size, content_type, etc.
    
    # Other fields remain the same
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=50)
    metadata = models.JSONField(default=dict)
    source_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'source_hash']),
            models.Index(fields=['storage_uuid']),  # For MinIO lookups
            models.Index(fields=['file_object_key']),  # For direct MinIO access
            models.Index(fields=['original_file_object_key']),
        ]
        
    def get_file_url(self, expires=3600):
        """Get pre-signed URL for file access"""
        if self.file_object_key:
            from .utils.minio_backend import MinIOBackend
            backend = MinIOBackend()
            return backend.get_file_url(self.file_object_key, expires)
        return None
    
    def get_original_file_url(self, expires=3600):
        """Get pre-signed URL for original file access"""
        if self.original_file_object_key:
            from .utils.minio_backend import MinIOBackend
            backend = MinIOBackend()
            return backend.get_file_url(self.original_file_object_key, expires)
        return None

class Report(models.Model):
    # UUID serves as the primary object identifier
    storage_uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    # Store object keys directly
    main_report_object_key = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    
    # Store all file metadata in JSON
    file_metadata = models.JSONField(default=dict)  # All file paths, names, sizes, etc.
    
    # Other fields remain the same
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE, null=True)
    job_id = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(max_length=20, default='pending')
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['storage_uuid']),
            models.Index(fields=['main_report_object_key']),
        ]
    
    def get_report_url(self, expires=3600):
        """Get pre-signed URL for report access"""
        if self.main_report_object_key:
            from .utils.minio_backend import MinIOBackend
            backend = MinIOBackend()
            return backend.get_file_url(self.main_report_object_key, expires)
        return None

class PodcastJob(models.Model):
    # UUID serves as the primary object identifier
    storage_uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    # Store object key directly
    audio_object_key = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    
    # Store file metadata
    file_metadata = models.JSONField(default=dict)  # filename, size, duration, etc.
    
    # Other fields remain the same
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE)
    job_id = models.UUIDField(default=uuid.uuid4, unique=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['storage_uuid']),
            models.Index(fields=['audio_object_key']),
        ]
    
    def get_audio_url(self, expires=3600):
        """Get pre-signed URL for audio access"""
        if self.audio_object_key:
            from .utils.minio_backend import MinIOBackend
            backend = MinIOBackend()
            return backend.get_file_url(self.audio_object_key, expires)
        return None
```

#### **3. MinIO Bucket Organization**

```python
# MinIO bucket structure (flat with prefixes)
deepsight-users/
├── kb/
│   ├── 550e8400-e29b-41d4-a716-446655440000/
│   │   ├── document.pdf
│   │   ├── content.md
│   │   └── image1.png
│   └── 550e8400-e29b-41d4-a716-446655440001/
│       └── presentation.pptx
├── reports/
│   ├── 550e8400-e29b-41d4-a716-446655440002/
│   │   ├── report.pdf
│   │   └── chart.png
│   └── 550e8400-e29b-41d4-a716-446655440003/
│       └── analysis.docx
├── podcasts/
│   ├── 550e8400-e29b-41d4-a716-446655440004/
│   │   └── episode.mp3
│   └── 550e8400-e29b-41d4-a716-446655440005/
│       └── conversation.wav
└── temp/
    └── 550e8400-e29b-41d4-a716-446655440006/
        └── upload.tmp
```

### **4. Fully MinIO-Native File Storage Service (No Path Functions)**

```python
# backend/notebooks/utils/file_storage.py
import uuid
import os
from django.conf import settings
from django.core.files.base import ContentFile
from .minio_backend import MinIOBackend

class FileStorageService:
    def __init__(self):
        self.storage_backend = MinIOBackend()
    
    def store_processed_file(self, content, metadata, processing_result, user_id, notebook_id, source_id=None):
        """Store processed file with fully MinIO-native approach - let MinIO handle all paths"""
        try:
            from ..models import KnowledgeBaseItem, KnowledgeItem, Notebook
            
            # Create knowledge base item with UUID (no file fields yet)
            kb_item = KnowledgeBaseItem.objects.create(
                user_id=user_id,
                title=self._generate_title_from_metadata(metadata),
                content_type=self._determine_content_type(metadata),
                metadata=metadata,
                source_hash=self._calculate_content_hash(content, metadata),
                # storage_uuid is auto-generated by Django
            )
            
            # Let MinIO generate the object keys using content-based naming
            content_object_key = None
            original_object_key = None
            
            # Store content file - MinIO generates the object key
            if content:
                content_object_key = self.storage_backend.save_file_with_auto_key(
                    content.encode('utf-8'),
                    filename='content.md',
                    prefix='kb',
                    metadata={
                        'content_type': 'text/markdown',
                        'kb_item_id': str(kb_item.id),
                        'user_id': str(user_id),
                        'file_type': 'processed_content'
                    }
                )
                
                # Store the MinIO-generated object key in database
                kb_item.file_object_key = content_object_key
                kb_item.file_metadata.update({
                    'filename': 'content.md',
                    'content_type': 'text/markdown',
                    'size': len(content.encode('utf-8'))
                })
            
            # Store original file if provided - MinIO generates the object key
            if 'original_file_path' in metadata:
                original_path = metadata['original_file_path']
                if os.path.exists(original_path):
                    with open(original_path, 'rb') as f:
                        file_data = f.read()
                        
                    original_object_key = self.storage_backend.save_file_with_auto_key(
                        file_data,
                        filename=metadata.get('original_filename', 'file'),
                        prefix='kb',
                        metadata={
                            'content_type': metadata.get('content_type', 'application/octet-stream'),
                            'kb_item_id': str(kb_item.id),
                            'user_id': str(user_id),
                            'file_type': 'original_file'
                        }
                    )
                    
                    # Store the MinIO-generated object key in database
                    kb_item.original_file_object_key = original_object_key
                    kb_item.file_metadata.update({
                        'original_filename': metadata.get('original_filename', 'file'),
                        'original_content_type': metadata.get('content_type', 'application/octet-stream'),
                        'original_size': len(file_data)
                    })
            
            # Store images as separate objects - MinIO generates all paths
            if 'images' in processing_result:
                self._store_images_minio_native(kb_item, processing_result['images'])
            
            # Save the updated object keys to database
            kb_item.save()
            
            # Link to notebook
            KnowledgeItem.objects.create(
                notebook_id=notebook_id,
                knowledge_base_item=kb_item,
                source_id=source_id,
                notes=f"Processed from {metadata.get('original_filename', 'unknown')}"
            )
            
            return str(kb_item.id)
            
        except Exception as e:
            self.log_operation("store_file_error", str(e), "error")
            raise
    
    def _store_images_minio_native(self, kb_item, images):
        """Store images using fully MinIO-native approach - let MinIO handle all paths"""
        image_object_keys = []
        
        for image_name, image_data in images.items():
            # Let MinIO generate the object key automatically
            image_object_key = self.storage_backend.save_file_with_auto_key(
                image_data,
                filename=image_name,
                prefix='kb-images',
                metadata={
                    'content_type': 'image',
                    'kb_item_id': str(kb_item.id),
                    'original_name': image_name,
                    'file_type': 'extracted_image'
                }
            )
            
            image_object_keys.append({
                'object_key': image_object_key,
                'original_name': image_name,
                'size': len(image_data)
            })
        
        # Store image object keys in metadata
        kb_item.metadata['image_objects'] = image_object_keys
        kb_item.save()
    
    def get_file_content(self, file_id, user_id=None):
        """Get file content using MinIO object key"""
        try:
            from ..models import KnowledgeBaseItem
            
            kb_item = KnowledgeBaseItem.objects.get(id=file_id, user_id=user_id)
            
            if kb_item.file_object_key:
                # Use MinIO backend to get content by object key
                return self.storage_backend.get_file_content(kb_item.file_object_key)
            
            return None
            
        except Exception as e:
            self.log_operation("get_content_error", str(e), "error")
            return None
    
    def get_file_url(self, file_id, user_id=None, expires=3600):
        """Get pre-signed URL using MinIO object key"""
        try:
            from ..models import KnowledgeBaseItem
            
            kb_item = KnowledgeBaseItem.objects.get(id=file_id, user_id=user_id)
            
            if kb_item.original_file_object_key:
                return self.storage_backend.get_file_url(kb_item.original_file_object_key, expires)
            elif kb_item.file_object_key:
                return self.storage_backend.get_file_url(kb_item.file_object_key, expires)
            
            return None
            
        except Exception as e:
            self.log_operation("get_file_url_error", str(e), "error")
            return None
```

### **5. MinIO Bucket Policies and Security**

```python
# backend/notebooks/utils/minio_security.py
from minio import Minio
from django.conf import settings
import json

class MinIOSecurityManager:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_SETTINGS['ENDPOINT'],
            access_key=settings.MINIO_SETTINGS['ACCESS_KEY'],
            secret_key=settings.MINIO_SETTINGS['SECRET_KEY'],
            secure=settings.MINIO_SETTINGS['SECURE']
        )
        self.bucket_name = settings.MINIO_SETTINGS['BUCKET_NAME']
    
    def setup_bucket_policies(self):
        """Setup MinIO bucket policies for security"""
        
        # Policy for knowledge base files - user-specific access
        kb_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self.bucket_name}/kb/*"],
                    "Condition": {
                        "StringEquals": {
                            "s3:ExistingObjectTag/user_id": "${aws:userid}"
                        }
                    }
                }
            ]
        }
        
        # Apply policy
        self.client.set_bucket_policy(self.bucket_name, json.dumps(kb_policy))
    
    def tag_object_with_user(self, object_name, user_id):
        """Tag MinIO object with user ID for access control"""
        from minio.commonconfig import Tags
        
        tags = Tags()
        tags['user_id'] = str(user_id)
        tags['created_at'] = timezone.now().isoformat()
        
        self.client.set_object_tags(self.bucket_name, object_name, tags)
```

### **6. Migration Script for MinIO-Native Approach**

```python
# backend/notebooks/management/commands/migrate_to_minio_native.py
from django.core.management.base import BaseCommand
from django.db import transaction
from notebooks.models import KnowledgeBaseItem
import uuid

class Command(BaseCommand):
    help = 'Migrate to MinIO-native file organization'
    
    def handle(self, *args, **options):
        self.stdout.write('Starting MinIO-native migration...')
        
        # Step 1: Add storage_uuid to existing records
        items_without_uuid = KnowledgeBaseItem.objects.filter(storage_uuid__isnull=True)
        
        for item in items_without_uuid:
            with transaction.atomic():
                # Generate UUID for existing item
                item.storage_uuid = uuid.uuid4()
                item.save()
                
                # Migrate files to new MinIO-native structure
                self._migrate_files_to_native_structure(item)
        
        self.stdout.write(self.style.SUCCESS('Migration completed'))
    
    def _migrate_files_to_native_structure(self, item):
        """Migrate files to MinIO-native structure"""
        minio_backend = MinIOBackend()
        
        # Migrate original file
        if item.original_file:
            old_path = item.original_file.name
            new_path = f"kb/{item.storage_uuid}/{os.path.basename(old_path)}"
            
            # Copy file to new location
            file_content = minio_backend.get_file_content(old_path)
            minio_backend.save_file(new_path, file_content)
            
            # Update database
            item.original_file.name = new_path
            item.save()
            
            # Delete old file
            minio_backend.delete_file(old_path)
        
        # Migrate processed file
        if item.file:
            old_path = item.file.name
            new_path = f"kb/{item.storage_uuid}/{os.path.basename(old_path)}"
            
            # Copy file to new location
            file_content = minio_backend.get_file_content(old_path)
            minio_backend.save_file(new_path, file_content)
            
            # Update database
            item.file.name = new_path
            item.save()
            
            # Delete old file
            minio_backend.delete_file(old_path)
```

### **Benefits of MinIO-Native Approach**

#### **1. Performance Benefits**
- **Faster object lookup**: Flat structure with UUID keys
- **Better caching**: MinIO can cache objects more efficiently
- **Reduced metadata overhead**: No deep directory traversal
- **Improved parallelism**: Better concurrent access patterns

#### **2. Scalability Benefits**
- **Horizontal scaling**: Objects distributed across MinIO nodes
- **No directory limits**: No filesystem directory entry limits
- **Better sharding**: UUID-based distribution
- **Reduced hotspots**: Even distribution of objects

#### **3. Operational Benefits**
- **Simpler backup/restore**: Flat structure easier to manage
- **Better monitoring**: Cleaner metrics and logging
- **Easier troubleshooting**: Direct object access by UUID
- **Cloud-native**: Follows S3/MinIO best practices

#### **4. Security Benefits**
- **Object-level tagging**: User-based access control
- **Simplified policies**: Prefix-based bucket policies
- **Better audit trails**: Clear object ownership
- **Reduced attack surface**: No path traversal vulnerabilities

### **Comparison: Custom vs MinIO-Native**

| Aspect | Custom Path Functions | MinIO-Native Approach |
|--------|----------------------|----------------------|
| **Path Structure** | `users/u_123/kb/2025-01/f_456/file.pdf` | `kb/550e8400-e29b-41d4-a716-446655440000/file.pdf` |
| **Performance** | Slower (deep hierarchy) | Faster (flat structure) |
| **Scalability** | Limited by directory depth | Unlimited horizontal scaling |
| **Maintainability** | Complex path logic | Simple UUID-based keys |
| **Security** | Path-based access control | Object-level tagging |
| **Cloud-Native** | Not optimized | Follows S3/MinIO best practices |
| **Migration Complexity** | High (path dependencies) | Low (UUID-based) |

### **Recommendation: Adopt MinIO-Native Approach**

The MinIO-native approach with UUID-based object keys is **strongly recommended** because:

1. **Better Performance**: Flat structure optimizes MinIO performance
2. **True Scalability**: Eliminates directory structure limitations  
3. **Simplified Code**: Removes complex path generation logic
4. **Enhanced Security**: Object-level access control and tagging
5. **Future-Proof**: Follows cloud storage best practices
6. **Easier Maintenance**: UUID-based keys are simpler to manage

This approach transforms the file storage from a traditional filesystem mindset to a modern object storage architecture, fully leveraging MinIO's capabilities.

---

## **🔥 Fully MinIO-Native Approach: Complete Example**

### **How MinIO Generates Object Keys Automatically**

Instead of using custom path functions, let MinIO handle all path generation:

```python
# ❌ OLD WAY: Custom path functions
def user_knowledge_base_path(instance, filename):
    return f"users/u_{instance.user_id}/knowledge-base/{year_month}/f_{instance.id}/{filename}"

# ✅ NEW WAY: Let MinIO generate object keys
# No upload_to functions needed at all!
```

### **Real-World Example: File Upload Flow**

```python
# 1. User uploads "research_paper.pdf"
uploaded_file = request.FILES['file']  # research_paper.pdf (2.5MB)

# 2. Create Django model (no file fields, just metadata)
kb_item = KnowledgeBaseItem.objects.create(
    user_id=123,
    title="Research Paper",
    content_type="document"
    # storage_uuid auto-generated: 550e8400-e29b-41d4-a716-446655440000
)

# 3. Let MinIO generate the object key automatically
minio_backend = MinIOBackend()
object_key = minio_backend.save_file_with_auto_key(
    content=uploaded_file.read(),
    filename="research_paper.pdf",
    prefix="kb",
    metadata={
        'user_id': '123',
        'kb_item_id': str(kb_item.id),
        'file_type': 'original_file'
    }
)

# 4. MinIO returns auto-generated object key
# object_key = "kb/20250711_143022_a1b2c3d4e5f6789a_8f4e2a1b.pdf"
#                  ^timestamp  ^content_hash  ^uuid   ^ext

# 5. Store the MinIO-generated key in database
kb_item.original_file_object_key = object_key
kb_item.file_metadata = {
    'filename': 'research_paper.pdf',
    'size': 2621440,  # 2.5MB
    'content_type': 'application/pdf'
}
kb_item.save()
```

### **MinIO Object Key Structure (Auto-Generated)**

```
# MinIO automatically generates keys like:
kb/20250711_143022_a1b2c3d4e5f6789a_8f4e2a1b.pdf
│  │                │                │        │
│  │                │                │        └── File extension
│  │                │                └── Short UUID (collision prevention)
│  │                └── Content hash (first 16 chars) - enables deduplication
│  └── Timestamp (YYYYMMDD_HHMMSS) - enables time-based queries
└── Prefix (kb/reports/podcasts) - enables categorization

# Examples of auto-generated keys:
kb/20250711_143022_a1b2c3d4e5f6789a_8f4e2a1b.pdf          # Knowledge base PDF
kb/20250711_143025_b2c3d4e5f6789abc_9g5f3b2c.md           # Processed content
reports/20250711_143030_c3d4e5f6789abcde_ah6g4c3d.pdf     # Generated report
podcasts/20250711_143035_d4e5f6789abcdef0_bi7h5d4e.mp3    # Podcast audio
kb-images/20250711_143040_e5f6789abcdef012_cj8i6e5f.png   # Extracted image
```

### **Benefits: No More Path Management**

#### **Before (Custom Paths)**
```python
# Complex path generation logic
def user_knowledge_base_path(instance, filename):
    from .utils.file_storage import file_storage_service
    user_id = instance.user_id
    year_month = datetime.now().strftime('%Y-%m')
    paths = file_storage_service._generate_knowledge_base_paths(
        user_id, filename, str(instance.id)
    )
    return paths['original_file_path']

# Results in paths like:
# "users/u_123/knowledge_base_item/2025-07/f_456/research_paper.pdf"
```

#### **After (MinIO Auto-Generated)**
```python
# No path functions needed at all!
# MinIO generates optimal object keys automatically:
# "kb/20250711_143022_a1b2c3d4e5f6789a_8f4e2a1b.pdf"

# Advantages:
# ✅ Content-based deduplication (same hash = same content)
# ✅ Time-based organization (timestamp prefix)
# ✅ Collision-free (UUID suffix)
# ✅ No directory structure limits
# ✅ Better performance (flat structure)
# ✅ Automatic optimization by MinIO
```

### **Database Migration Script**

```python
# Add object key fields to existing models
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('notebooks', '0001_initial'),
    ]
    
    operations = [
        # Add storage UUID
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='storage_uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
        ),
        
        # Add object key fields (replace FileField)
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='file_object_key',
            field=models.CharField(max_length=255, blank=True, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='original_file_object_key',
            field=models.CharField(max_length=255, blank=True, null=True, db_index=True),
        ),
        
        # Add file metadata field
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='file_metadata',
            field=models.JSONField(default=dict),
        ),
        
        # Remove old FileFields (after migration)
        # migrations.RemoveField(model_name='knowledgebaseitem', name='file'),
        # migrations.RemoveField(model_name='knowledgebaseitem', name='original_file'),
    ]
```

### **API Usage Example**

```python
# GET /api/files/456/url
def get_file_url(request, file_id):
    try:
        # Get file by ID
        kb_item = KnowledgeBaseItem.objects.get(
            id=file_id, 
            user=request.user
        )
        
        # Generate pre-signed URL (MinIO handles everything)
        file_url = kb_item.get_original_file_url(expires=3600)
        
        return JsonResponse({
            'file_url': file_url,
            'filename': kb_item.file_metadata.get('filename', 'file'),
            'size': kb_item.file_metadata.get('size', 0),
            'expires_in': 3600
        })
        
    except KnowledgeBaseItem.DoesNotExist:
        return JsonResponse({'error': 'File not found'}, status=404)

# Response:
{
    "file_url": "https://minio:9000/deepsight-users/kb/20250711_143022_a1b2c3d4e5f6789a_8f4e2a1b.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...",
    "filename": "research_paper.pdf",
    "size": 2621440,
    "expires_in": 3600
}
```

### **Performance Comparison**

| Operation | Custom Paths | MinIO Auto-Generated |
|-----------|-------------|---------------------|
| **Object Lookup** | O(log n) tree traversal | O(1) hash table lookup |
| **Deduplication** | Application-level logic | Built-in content hashing |
| **Concurrent Access** | File system locks | Lock-free object storage |
| **Scalability** | Limited by directory depth | Unlimited horizontal scaling |
| **Path Generation** | Complex algorithm | Simple hash + timestamp |
| **Storage Efficiency** | Directory overhead | Pure object storage |

### **Summary: Why Fully MinIO-Native is Better**

✅ **Zero Path Management**: No upload_to functions needed  
✅ **Auto-Deduplication**: Content hash prevents duplicate storage  
✅ **Time Organization**: Timestamp prefix enables time-based queries  
✅ **Collision-Free**: UUID suffix ensures uniqueness  
✅ **Better Performance**: Flat structure optimized for object storage  
✅ **Cloud-Native**: Follows S3/MinIO best practices  
✅ **Simplified Code**: Eliminates complex path generation logic  
✅ **Future-Proof**: Scales infinitely without restructuring

---

## **🔄 Migration Strategy**

### **Phase 1: Infrastructure Setup (Week 1)**

#### **1.1 MinIO Server Setup**
```yaml
# docker-compose.yml additions
services:
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    
  minio-client:
    image: minio/mc:latest
    depends_on:
      - minio
    entrypoint: >
      /bin/sh -c "
      /usr/bin/mc config host add minio http://minio:9000 minioadmin minioadmin;
      /usr/bin/mc mb minio/deepsight-users;
      /usr/bin/mc policy set public minio/deepsight-users;
      exit 0;
      "

volumes:
  minio_data:
```

#### **1.2 Dependencies Installation**
```bash
# Add to requirements.txt
django-storages==1.14.2
boto3==1.34.0
minio==7.2.0
```

### **Phase 2: Storage Abstraction Layer (Week 2)**

#### **2.1 Create Storage Backend Interface**
```python
# backend/notebooks/utils/storage_backends.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, BinaryIO
from django.core.files.base import ContentFile

class StorageBackend(ABC):
    @abstractmethod
    def save_file(self, path: str, content: BinaryIO, metadata: Dict[str, Any] = None) -> str:
        pass
    
    @abstractmethod
    def get_file_url(self, path: str, expires: int = 3600) -> str:
        pass
    
    @abstractmethod
    def delete_file(self, path: str) -> bool:
        pass
    
    @abstractmethod
    def file_exists(self, path: str) -> bool:
        pass
    
    @abstractmethod
    def get_file_content(self, path: str) -> bytes:
        pass
```

#### **2.2 Enhanced MinIO Backend with Auto-Key Generation**
```python
# backend/notebooks/utils/minio_backend.py
import io
import uuid
import hashlib
from datetime import datetime
from minio import Minio
from minio.error import S3Error
from django.conf import settings
from .storage_backends import StorageBackend

class MinIOBackend(StorageBackend):
    def __init__(self):
        self.client = Minio(
            settings.MINIO_SETTINGS['ENDPOINT'],
            access_key=settings.MINIO_SETTINGS['ACCESS_KEY'],
            secret_key=settings.MINIO_SETTINGS['SECRET_KEY'],
            secure=settings.MINIO_SETTINGS['SECURE']
        )
        self.bucket_name = settings.MINIO_SETTINGS['BUCKET_NAME']
        self._ensure_bucket_exists()
    
    def save_file_with_auto_key(self, content, filename: str, prefix: str = '', metadata: dict = None) -> str:
        """
        Save file to MinIO with auto-generated object key.
        MinIO handles the path generation using content hash + timestamp.
        
        Args:
            content: File content (bytes or BinaryIO)
            filename: Original filename for reference
            prefix: Optional prefix (kb, reports, podcasts, etc.)
            metadata: Additional metadata to store with object
            
        Returns:
            The MinIO-generated object key
        """
        try:
            # Convert content to bytes if needed
            if hasattr(content, 'read'):
                content_bytes = content.read()
                if hasattr(content, 'seek'):
                    content.seek(0)
            else:
                content_bytes = content
            
            # Let MinIO generate a unique object key using content hash + timestamp
            content_hash = hashlib.sha256(content_bytes).hexdigest()[:16]  # First 16 chars of hash
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]  # Short UUID
            
            # Extract file extension
            file_ext = ''
            if '.' in filename:
                file_ext = '.' + filename.split('.')[-1].lower()
            
            # Generate MinIO-native object key
            if prefix:
                object_key = f"{prefix}/{timestamp}_{content_hash}_{unique_id}{file_ext}"
            else:
                object_key = f"{timestamp}_{content_hash}_{unique_id}{file_ext}"
            
            # Prepare metadata
            final_metadata = {
                'original_filename': filename,
                'content_hash': content_hash,
                'upload_timestamp': timestamp,
                'content_length': str(len(content_bytes))
            }
            if metadata:
                final_metadata.update(metadata)
            
            # Upload to MinIO with auto-generated key
            self.client.put_object(
                self.bucket_name,
                object_key,
                io.BytesIO(content_bytes),
                length=len(content_bytes),
                metadata=final_metadata
            )
            
            return object_key
            
        except S3Error as e:
            raise Exception(f"MinIO upload failed: {str(e)}")
    
    def save_file(self, path: str, content, metadata: dict = None) -> str:
        """
        Legacy method for custom path uploads (backward compatibility).
        """
        try:
            # Convert content to bytes if needed
            if hasattr(content, 'read'):
                content_bytes = content.read()
                if hasattr(content, 'seek'):
                    content.seek(0)
            else:
                content_bytes = content
            
            # Upload to MinIO with provided path
            self.client.put_object(
                self.bucket_name,
                path,
                io.BytesIO(content_bytes),
                length=len(content_bytes),
                metadata=metadata or {}
            )
            return path
            
        except S3Error as e:
            raise Exception(f"MinIO upload failed: {str(e)}")
    
    def get_file_url(self, object_key: str, expires: int = 3600) -> str:
        """Generate pre-signed URL for object access"""
        try:
            from datetime import timedelta
            return self.client.presigned_get_object(
                self.bucket_name,
                object_key,
                expires=timedelta(seconds=expires)
            )
        except S3Error as e:
            raise Exception(f"MinIO URL generation failed: {str(e)}")
    
    def get_file_content(self, object_key: str) -> bytes:
        """Get file content by object key"""
        try:
            response = self.client.get_object(self.bucket_name, object_key)
            return response.read()
        except S3Error as e:
            raise Exception(f"MinIO download failed: {str(e)}")
    
    def file_exists(self, object_key: str) -> bool:
        """Check if file exists"""
        try:
            self.client.stat_object(self.bucket_name, object_key)
            return True
        except S3Error:
            return False
    
    def delete_file(self, object_key: str) -> bool:
        """Delete file from MinIO"""
        try:
            self.client.remove_object(self.bucket_name, object_key)
            return True
        except S3Error as e:
            raise Exception(f"MinIO delete failed: {str(e)}")
    
    def list_objects_by_prefix(self, prefix: str) -> list:
        """List all objects with given prefix"""
        try:
            objects = self.client.list_objects(self.bucket_name, prefix=prefix)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            raise Exception(f"MinIO list failed: {str(e)}")
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise Exception(f"MinIO bucket creation failed: {str(e)}")
```

### **Phase 3: Service Layer Updates (Week 3)**

#### **3.1 Updated FileStorageService**
```python
# backend/notebooks/utils/file_storage.py
from .storage_backends import StorageBackend
from .minio_backend import MinIOBackend
from .local_backend import LocalBackend
from django.conf import settings

class FileStorageService:
    def __init__(self):
        self.service_name = "file_storage"
        self.logger = logging.getLogger(f"{__name__}.file_storage")
        
        # Initialize storage backend based on configuration
        self.storage_backend = self._get_storage_backend()
        
    def _get_storage_backend(self) -> StorageBackend:
        backend_type = getattr(settings, 'STORAGE_BACKEND', 'local')
        
        if backend_type == 'minio':
            return MinIOBackend()
        elif backend_type == 'local':
            return LocalBackend()
        else:
            raise ValueError(f"Unknown storage backend: {backend_type}")
    
    def _save_organized_original_file(self, kb_item, original_file_path: str, paths: Dict[str, str]):
        """Save the original binary file using storage backend."""
        try:
            with open(original_file_path, "rb") as f:
                saved_path = self.storage_backend.save_file(
                    paths["original_file_path"], 
                    f,
                    metadata={
                        'kb_item_id': str(kb_item.id),
                        'content_type': 'original_file'
                    }
                )
                
            # Update Django model with storage path
            kb_item.original_file.name = saved_path
            kb_item.save()
            
        except Exception as e:
            self.log_operation("save_organized_original_file_error", str(e), "error")
```

### **Phase 4: Model and URL Updates (Week 4)**

#### **4.1 Custom Storage Class**
```python
# backend/notebooks/utils/custom_storage.py
from django.core.files.storage import Storage
from django.conf import settings
from .minio_backend import MinIOBackend

class MinIOStorage(Storage):
    def __init__(self):
        self.backend = MinIOBackend()
    
    def _save(self, name, content):
        return self.backend.save_file(name, content)
    
    def url(self, name):
        return self.backend.get_file_url(name)
    
    def exists(self, name):
        return self.backend.file_exists(name)
    
    def delete(self, name):
        return self.backend.delete_file(name)
```

#### **4.2 Updated Models**
```python
# backend/notebooks/models.py
from django.db import models
from .utils.custom_storage import MinIOStorage

def get_storage():
    from django.conf import settings
    if getattr(settings, 'STORAGE_BACKEND', 'local') == 'minio':
        return MinIOStorage()
    return None

class KnowledgeBaseItem(models.Model):
    # ... existing fields ...
    
    original_file = models.FileField(
        upload_to="knowledge_base/original/",
        blank=True,
        null=True,
        storage=get_storage()
    )
    
    file = models.FileField(
        upload_to="knowledge_base/processed/",
        blank=True,
        null=True,
        storage=get_storage()
    )
```

---

## **🛠️ Detailed Implementation Plan**

### **Phase 5: Data Migration (Week 5)**

#### **5.1 Migration Script**
```python
# backend/notebooks/management/commands/migrate_to_minio.py
from django.core.management.base import BaseCommand
from django.conf import settings
from notebooks.models import KnowledgeBaseItem
from notebooks.utils.minio_backend import MinIOBackend
import os
from pathlib import Path

class Command(BaseCommand):
    help = 'Migrate existing files from local storage to MinIO'
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated')
        parser.add_argument('--batch-size', type=int, default=100, help='Batch size for migration')
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        
        self.stdout.write('Starting MinIO migration...')
        
        # Initialize MinIO backend
        minio_backend = MinIOBackend()
        
        # Get all knowledge base items with files
        items = KnowledgeBaseItem.objects.filter(
            models.Q(original_file__isnull=False) | 
            models.Q(file__isnull=False)
        )
        
        total_items = items.count()
        self.stdout.write(f'Found {total_items} items to migrate')
        
        migrated_count = 0
        error_count = 0
        
        for item in items.iterator(chunk_size=batch_size):
            try:
                # Migrate original file
                if item.original_file:
                    self._migrate_file(item, 'original_file', minio_backend, dry_run)
                
                # Migrate processed file
                if item.file:
                    self._migrate_file(item, 'file', minio_backend, dry_run)
                
                migrated_count += 1
                
                if migrated_count % 10 == 0:
                    self.stdout.write(f'Migrated {migrated_count}/{total_items} items')
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Error migrating item {item.id}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Migration completed: {migrated_count} success, {error_count} errors'
            )
        )
    
    def _migrate_file(self, item, field_name, minio_backend, dry_run):
        """Migrate a single file field to MinIO"""
        file_field = getattr(item, field_name)
        
        if not file_field or not file_field.name:
            return
        
        # Get local file path
        local_path = file_field.path
        
        if not os.path.exists(local_path):
            self.stdout.write(
                self.style.WARNING(f'Local file not found: {local_path}')
            )
            return
        
        # Generate MinIO path
        minio_path = self._generate_minio_path(item, field_name, file_field.name)
        
        if dry_run:
            self.stdout.write(f'Would migrate: {local_path} -> {minio_path}')
            return
        
        # Upload to MinIO
        with open(local_path, 'rb') as f:
            minio_backend.save_file(
                minio_path,
                f,
                metadata={
                    'kb_item_id': str(item.id),
                    'field_name': field_name,
                    'original_path': file_field.name
                }
            )
        
        # Update database record
        file_field.name = minio_path
        item.save()
        
        self.stdout.write(f'Migrated: {local_path} -> {minio_path}')
    
    def _generate_minio_path(self, item, field_name, original_name):
        """Generate MinIO object path maintaining the organized structure"""
        # Extract user ID and maintain organized structure
        user_id = item.user_id
        
        # Build path similar to current structure
        base_path = f"users/u_{user_id}/knowledge-base"
        
        # Add temporal organization
        from datetime import datetime
        year_month = item.created_at.strftime("%Y-%m")
        
        # Build full path
        if field_name == 'original_file':
            return f"{base_path}/{year_month}/f_{item.id}/original/{Path(original_name).name}"
        else:
            return f"{base_path}/{year_month}/f_{item.id}/content/{Path(original_name).name}"
```

#### **5.2 Rollback Strategy**
```python
# backend/notebooks/management/commands/rollback_from_minio.py
from django.core.management.base import BaseCommand
from notebooks.models import KnowledgeBaseItem
from notebooks.utils.minio_backend import MinIOBackend
import os

class Command(BaseCommand):
    help = 'Rollback files from MinIO to local storage'
    
    def handle(self, *args, **options):
        self.stdout.write('Starting rollback from MinIO...')
        
        minio_backend = MinIOBackend()
        
        # Get all items with MinIO paths
        items = KnowledgeBaseItem.objects.filter(
            models.Q(original_file__startswith='users/') | 
            models.Q(file__startswith='users/')
        )
        
        for item in items:
            try:
                # Rollback original file
                if item.original_file and item.original_file.name.startswith('users/'):
                    self._rollback_file(item, 'original_file', minio_backend)
                
                # Rollback processed file
                if item.file and item.file.name.startswith('users/'):
                    self._rollback_file(item, 'file', minio_backend)
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error rolling back item {item.id}: {str(e)}')
                )
        
        self.stdout.write(self.style.SUCCESS('Rollback completed'))
```

### **Phase 6: Configuration Management (Week 6)**

#### **6.1 Environment-based Configuration**
```python
# backend/deepsight/settings.py

# Storage Backend Configuration
STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'local')

# MinIO Configuration
MINIO_SETTINGS = {
    'ENDPOINT': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
    'ACCESS_KEY': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
    'SECRET_KEY': os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
    'BUCKET_NAME': os.getenv('MINIO_BUCKET_NAME', 'deepsight-users'),
    'SECURE': os.getenv('MINIO_SECURE', 'false').lower() == 'true',
    'REGION': os.getenv('MINIO_REGION', 'us-east-1'),
}

# Django Storages Configuration for MinIO
if STORAGE_BACKEND == 'minio':
    # Configure django-storages for MinIO
    DEFAULT_FILE_STORAGE = 'notebooks.utils.custom_storage.MinIOStorage'
    
    # AWS S3 settings for MinIO (boto3 compatibility)
    AWS_ACCESS_KEY_ID = MINIO_SETTINGS['ACCESS_KEY']
    AWS_SECRET_ACCESS_KEY = MINIO_SETTINGS['SECRET_KEY']
    AWS_STORAGE_BUCKET_NAME = MINIO_SETTINGS['BUCKET_NAME']
    AWS_S3_ENDPOINT_URL = f"http{'s' if MINIO_SETTINGS['SECURE'] else ''}://{MINIO_SETTINGS['ENDPOINT']}"
    AWS_S3_REGION_NAME = MINIO_SETTINGS['REGION']
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
```

#### **6.2 Docker Environment Configuration**
```yaml
# .env file for Docker
STORAGE_BACKEND=minio
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=deepsight-users
MINIO_SECURE=false
MINIO_REGION=us-east-1

# Production settings
MINIO_ENDPOINT=your-minio-server.com:9000
MINIO_SECURE=true
```

### **Phase 7: API and Frontend Updates (Week 7)**

#### **7.1 File Serving API Updates**
```python
# backend/notebooks/views.py
from django.http import HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .utils.storage_backends import get_storage_backend

@login_required
@require_http_methods(["GET"])
def serve_file(request, file_id):
    """Serve files with proper authentication and MinIO support"""
    try:
        # Get knowledge base item
        kb_item = KnowledgeBaseItem.objects.get(id=file_id, user=request.user)
        
        # Get storage backend
        storage_backend = get_storage_backend()
        
        # Get file field based on request parameter
        file_type = request.GET.get('type', 'processed')
        
        if file_type == 'original' and kb_item.original_file:
            file_path = kb_item.original_file.name
        elif kb_item.file:
            file_path = kb_item.file.name
        else:
            raise Http404("File not found")
        
        # For MinIO, return redirect to signed URL
        if hasattr(storage_backend, 'get_file_url'):
            file_url = storage_backend.get_file_url(file_path, expires=3600)
            return HttpResponse(
                status=302,
                headers={'Location': file_url}
            )
        else:
            # For local storage, serve directly
            file_content = storage_backend.get_file_content(file_path)
            response = HttpResponse(
                file_content,
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
            
    except KnowledgeBaseItem.DoesNotExist:
        raise Http404("File not found")
```

#### **7.2 Upload API Updates**
```python
# backend/notebooks/api/views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..utils.storage_backends import get_storage_backend

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_file(request):
    """Handle file uploads with MinIO support"""
    try:
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {'error': 'No file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get storage backend
        storage_backend = get_storage_backend()
        
        # Generate upload path
        upload_path = f"users/u_{request.user.id}/temp/uploads/{uploaded_file.name}"
        
        # Save file using storage backend
        saved_path = storage_backend.save_file(
            upload_path,
            uploaded_file,
            metadata={
                'user_id': str(request.user.id),
                'original_filename': uploaded_file.name,
                'content_type': uploaded_file.content_type
            }
        )
        
        return Response({
            'success': True,
            'file_path': saved_path,
            'file_url': storage_backend.get_file_url(saved_path) if hasattr(storage_backend, 'get_file_url') else None
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

---

## **🧪 Testing and Validation Strategy**

### **Phase 8: Testing Framework (Week 8)**

#### **8.1 Unit Tests for Storage Backends**
```python
# backend/notebooks/tests/test_storage_backends.py
import io
import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.conf import settings
from notebooks.utils.minio_backend import MinIOBackend
from notebooks.utils.local_backend import LocalBackend

class TestMinIOBackend(TestCase):
    def setUp(self):
        self.backend = MinIOBackend()
    
    @patch('notebooks.utils.minio_backend.Minio')
    def test_save_file_success(self, mock_minio):
        """Test successful file save to MinIO"""
        mock_client = MagicMock()
        mock_minio.return_value = mock_client
        
        test_content = b"test content"
        test_path = "test/path/file.txt"
        
        result = self.backend.save_file(test_path, io.BytesIO(test_content))
        
        self.assertEqual(result, test_path)
        mock_client.put_object.assert_called_once()
    
    @patch('notebooks.utils.minio_backend.Minio')
    def test_get_file_url(self, mock_minio):
        """Test file URL generation"""
        mock_client = MagicMock()
        mock_minio.return_value = mock_client
        mock_client.presigned_get_object.return_value = "https://minio.example.com/bucket/file.txt"
        
        result = self.backend.get_file_url("test/file.txt")
        
        self.assertTrue(result.startswith("https://"))
        mock_client.presigned_get_object.assert_called_once()
    
    @patch('notebooks.utils.minio_backend.Minio')
    def test_file_exists(self, mock_minio):
        """Test file existence check"""
        mock_client = MagicMock()
        mock_minio.return_value = mock_client
        mock_client.stat_object.return_value = MagicMock()
        
        result = self.backend.file_exists("test/file.txt")
        
        self.assertTrue(result)
        mock_client.stat_object.assert_called_once()

class TestStorageBackendSelection(TestCase):
    def test_minio_backend_selection(self):
        """Test MinIO backend is selected when configured"""
        with self.settings(STORAGE_BACKEND='minio'):
            from notebooks.utils.storage_backends import get_storage_backend
            backend = get_storage_backend()
            self.assertIsInstance(backend, MinIOBackend)
    
    def test_local_backend_selection(self):
        """Test local backend is selected when configured"""
        with self.settings(STORAGE_BACKEND='local'):
            from notebooks.utils.storage_backends import get_storage_backend
            backend = get_storage_backend()
            self.assertIsInstance(backend, LocalBackend)
```

#### **8.2 Integration Tests**
```python
# backend/notebooks/tests/test_file_storage_integration.py
import os
import tempfile
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from notebooks.models import KnowledgeBaseItem, Notebook
from notebooks.utils.file_storage import FileStorageService

class TestFileStorageIntegration(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.notebook = Notebook.objects.create(
            user=self.user,
            title='Test Notebook'
        )
        self.storage_service = FileStorageService()
    
    def test_store_processed_file_minio(self):
        """Test storing processed file with MinIO backend"""
        with self.settings(STORAGE_BACKEND='minio'):
            # Create test content
            test_content = "# Test Document\n\nThis is a test document."
            test_metadata = {
                'original_filename': 'test.pdf',
                'file_extension': '.pdf',
                'file_size': len(test_content)
            }
            
            # Store file
            kb_item_id = self.storage_service.store_processed_file(
                content=test_content,
                metadata=test_metadata,
                processing_result={},
                user_id=self.user.id,
                notebook_id=self.notebook.id
            )
            
            # Verify item was created
            kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id)
            self.assertEqual(kb_item.user_id, self.user.id)
            self.assertEqual(kb_item.title, 'test')
            
            # Verify file was stored
            self.assertTrue(kb_item.file.name.startswith('users/'))
    
    def test_get_file_content_minio(self):
        """Test retrieving file content from MinIO"""
        with self.settings(STORAGE_BACKEND='minio'):
            # First store a file
            test_content = "# Test Document Content"
            test_metadata = {'original_filename': 'test.md'}
            
            kb_item_id = self.storage_service.store_processed_file(
                content=test_content,
                metadata=test_metadata,
                processing_result={},
                user_id=self.user.id,
                notebook_id=self.notebook.id
            )
            
            # Retrieve content
            retrieved_content = self.storage_service.get_file_content(
                kb_item_id, 
                self.user.id
            )
            
            self.assertEqual(retrieved_content, test_content)
    
    def test_delete_knowledge_base_item_minio(self):
        """Test deleting knowledge base item from MinIO"""
        with self.settings(STORAGE_BACKEND='minio'):
            # Store a file
            test_content = "Content to be deleted"
            test_metadata = {'original_filename': 'delete_test.txt'}
            
            kb_item_id = self.storage_service.store_processed_file(
                content=test_content,
                metadata=test_metadata,
                processing_result={},
                user_id=self.user.id,
                notebook_id=self.notebook.id
            )
            
            # Delete the item
            success = self.storage_service.delete_knowledge_base_item(
                kb_item_id,
                self.user.id
            )
            
            self.assertTrue(success)
            
            # Verify item was deleted
            self.assertFalse(
                KnowledgeBaseItem.objects.filter(id=kb_item_id).exists()
            )
```

#### **8.3 Performance Tests**
```python
# backend/notebooks/tests/test_performance.py
import time
import threading
from django.test import TestCase
from django.contrib.auth.models import User
from notebooks.utils.file_storage import FileStorageService

class TestStoragePerformance(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='perfuser',
            email='perf@example.com',
            password='perfpass123'
        )
        self.storage_service = FileStorageService()
    
    def test_concurrent_file_operations(self):
        """Test concurrent file operations performance"""
        def store_file(thread_id):
            content = f"Thread {thread_id} content"
            metadata = {'original_filename': f'thread_{thread_id}.txt'}
            
            return self.storage_service.store_processed_file(
                content=content,
                metadata=metadata,
                processing_result={},
                user_id=self.user.id,
                notebook_id=1
            )
        
        # Test concurrent operations
        threads = []
        results = []
        
        start_time = time.time()
        
        for i in range(10):
            thread = threading.Thread(
                target=lambda i=i: results.append(store_file(i))
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # Verify all operations completed
        self.assertEqual(len(results), 10)
        
        # Performance assertion (should complete within reasonable time)
        self.assertLess(end_time - start_time, 30)  # 30 seconds max
```

#### **8.4 Migration Tests**
```python
# backend/notebooks/tests/test_migration.py
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import User
from notebooks.models import KnowledgeBaseItem
from io import StringIO

class TestMigration(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='miguser',
            email='mig@example.com',
            password='migpass123'
        )
    
    def test_migration_dry_run(self):
        """Test migration dry run functionality"""
        # Create test item with local file
        kb_item = KnowledgeBaseItem.objects.create(
            user=self.user,
            title='Test Item',
            content='test content'
        )
        
        # Run dry run migration
        out = StringIO()
        call_command('migrate_to_minio', '--dry-run', stdout=out)
        
        # Check output
        output = out.getvalue()
        self.assertIn('Would migrate', output)
        
        # Verify no actual migration occurred
        kb_item.refresh_from_db()
        self.assertFalse(kb_item.file.name.startswith('users/'))
    
    def test_migration_execution(self):
        """Test actual migration execution"""
        # This would require a more complex setup with actual files
        # and MinIO test environment
        pass
```

---

## **🚀 Deployment and Monitoring**

### **Phase 9: Production Deployment (Week 9)**

#### **9.1 Production Docker Configuration**
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  django:
    build: .
    environment:
      - STORAGE_BACKEND=minio
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - MINIO_BUCKET_NAME=deepsight-production
      - MINIO_SECURE=true
    depends_on:
      - minio
      - postgres
    volumes:
      - static_volume:/app/staticfiles
    
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - static_volume:/var/www/static
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - django

volumes:
  minio_data:
  static_volume:
```

#### **9.2 Monitoring and Logging**
```python
# backend/notebooks/utils/monitoring.py
import logging
import time
from functools import wraps
from django.conf import settings

logger = logging.getLogger(__name__)

def monitor_storage_operations(func):
    """Decorator to monitor storage operations performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        operation_name = func.__name__
        
        try:
            result = func(*args, **kwargs)
            
            # Log success
            duration = time.time() - start_time
            logger.info(
                f"Storage operation success: {operation_name}, "
                f"duration: {duration:.2f}s, "
                f"backend: {getattr(settings, 'STORAGE_BACKEND', 'unknown')}"
            )
            
            return result
            
        except Exception as e:
            # Log failure
            duration = time.time() - start_time
            logger.error(
                f"Storage operation failed: {operation_name}, "
                f"duration: {duration:.2f}s, "
                f"error: {str(e)}, "
                f"backend: {getattr(settings, 'STORAGE_BACKEND', 'unknown')}"
            )
            raise
    
    return wrapper

# Add monitoring to storage backends
from .storage_backends import StorageBackend

class MonitoredStorageBackend(StorageBackend):
    def __init__(self, backend):
        self.backend = backend
    
    @monitor_storage_operations
    def save_file(self, path, content, metadata=None):
        return self.backend.save_file(path, content, metadata)
    
    @monitor_storage_operations
    def get_file_url(self, path, expires=3600):
        return self.backend.get_file_url(path, expires)
    
    @monitor_storage_operations
    def delete_file(self, path):
        return self.backend.delete_file(path)
    
    @monitor_storage_operations
    def file_exists(self, path):
        return self.backend.file_exists(path)
    
    @monitor_storage_operations
    def get_file_content(self, path):
        return self.backend.get_file_content(path)
```

#### **9.3 Health Check Endpoints**
```python
# backend/notebooks/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ... existing patterns ...
    path('health/storage/', views.storage_health_check, name='storage_health'),
]

# backend/notebooks/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .utils.storage_backends import get_storage_backend
import time

@require_http_methods(["GET"])
def storage_health_check(request):
    """Health check endpoint for storage backend"""
    try:
        start_time = time.time()
        storage_backend = get_storage_backend()
        
        # Test basic operations
        test_path = "health/test.txt"
        test_content = b"health check"
        
        # Test save
        storage_backend.save_file(test_path, test_content)
        
        # Test exists
        exists = storage_backend.file_exists(test_path)
        
        # Test get content
        content = storage_backend.get_file_content(test_path)
        
        # Test delete
        storage_backend.delete_file(test_path)
        
        duration = time.time() - start_time
        
        return JsonResponse({
            'status': 'healthy',
            'backend': getattr(settings, 'STORAGE_BACKEND', 'unknown'),
            'response_time': f"{duration:.2f}s",
            'operations_tested': ['save', 'exists', 'get_content', 'delete']
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'backend': getattr(settings, 'STORAGE_BACKEND', 'unknown')
        }, status=500)
```

---

## **📋 Implementation Checklist**

### **Week 1: Infrastructure Setup**
- [ ] Set up MinIO server with Docker
- [ ] Configure MinIO buckets and policies
- [ ] Install required dependencies
- [ ] Set up development environment

### **Week 2: Storage Abstraction**
- [ ] Create StorageBackend interface
- [ ] Implement MinIOBackend class
- [ ] Create LocalBackend for backward compatibility
- [ ] Add backend selection mechanism

### **Week 3: Service Layer Updates**
- [ ] Update FileStorageService to use storage backends
- [ ] Update StorageService for reports
- [ ] Modify path generation for object storage
- [ ] Update image handling for MinIO

### **Week 4: Model and URL Updates**
- [ ] Create custom Django storage class
- [ ] Update model file fields to use MinIO storage
- [ ] Modify URL generation for file serving
- [ ] Update upload handling

### **Week 5: Data Migration**
- [ ] Create migration command for existing files
- [ ] Test migration with subset of data
- [ ] Create rollback mechanism
- [ ] Execute full migration

### **Week 6: Configuration Management**
- [ ] Add environment-based configuration
- [ ] Update Docker configuration
- [ ] Add production settings
- [ ] Document configuration options

### **Week 7: API Updates**
- [ ] Update file serving endpoints
- [ ] Modify upload API for MinIO
- [ ] Update authentication for file access
- [ ] Test API endpoints

### **Week 8: Testing**
- [ ] Create unit tests for storage backends
- [ ] Add integration tests
- [ ] Create performance tests
- [ ] Test migration process

### **Week 9: Deployment**
- [ ] Set up production MinIO cluster
- [ ] Deploy updated application
- [ ] Configure monitoring and logging
- [ ] Set up health checks

---

## **🔧 Maintenance and Monitoring**

### **Ongoing Operations**
1. **Backup Strategy**: Implement automated backups of MinIO data
2. **Monitoring**: Set up alerts for storage operations and failures
3. **Performance Tuning**: Monitor and optimize storage performance
4. **Security**: Regular security audits and access control reviews
5. **Scaling**: Plan for horizontal scaling as data grows

### **Key Metrics to Monitor**
- File upload/download success rates
- Storage operation latency
- MinIO cluster health
- Storage usage and capacity
- API response times

---

## **💡 Benefits of MinIO Migration**

### **Scalability**
- Horizontal scaling capabilities
- Cloud-native architecture
- Better handling of large files

### **Reliability**
- Built-in replication and redundancy
- Better disaster recovery
- Reduced single points of failure

### **Performance**
- Distributed storage for better performance
- Concurrent access optimization
- CDN integration capabilities

### **Operations**
- Easier backup and restore
- Better monitoring and alerting
- Simplified deployment in containers

This comprehensive plan provides a structured approach to migrating from local file storage to MinIO while maintaining the current organized file structure and functionality. The phased approach ensures minimal disruption to existing users and provides rollback capabilities if needed.