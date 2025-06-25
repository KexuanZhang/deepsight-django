# Batch Processing Guide

This guide explains how to use the new batch processing functionality to handle multiple URLs and file uploads efficiently without database locking issues.

## Problem Solved

The original implementation had database locking issues when processing multiple URLs or files simultaneously because:

1. **SQLite Database Limitations**: SQLite locks the entire database during write operations
2. **Long-running Transactions**: Processing operations were wrapped in `@transaction.atomic`, keeping database locks for extended periods
3. **Synchronous Processing**: All processing happened within HTTP requests, blocking other operations

## Solution Overview

The new batch processing system:

1. **Supports both single and batch operations** in the same endpoints
2. **Uses Celery for async processing** to avoid database locks
3. **Maintains backward compatibility** with existing code
4. **Provides batch status tracking** for monitoring progress

## How It Works

### Backend Changes

1. **Celery Tasks**: Created async tasks for URL and file processing
2. **Batch Job Models**: Added `BatchJob` and `BatchJobItem` models to track progress
3. **Enhanced Views**: Modified existing endpoints to detect and handle batch requests
4. **Status Endpoint**: Added batch job status tracking

### Frontend Changes

1. **Enhanced API Methods**: Updated `parseUrl`, `parseUrlWithMedia`, and `parseFile` to support arrays
2. **Batch Status Tracking**: Added `getBatchJobStatus` method
3. **Backward Compatibility**: Existing single-item calls continue to work

## Usage Examples

### Single Item Processing (Existing Behavior)

```javascript
// Single URL parsing
const result = await apiService.parseUrl("https://example.com", notebookId);

// Single file upload
const result = await apiService.parseFile(file, uploadId, notebookId);

// Single media URL
const result = await apiService.parseUrlWithMedia("https://youtube.com/watch?v=xyz", notebookId);
```

### Batch Processing (New Feature)

```javascript
// Batch URL parsing
const urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"];
const result = await apiService.parseUrl(urls, notebookId);

if (result.is_batch) {
    const batchJobId = result.batch_job_id;
    
    // Monitor progress
    const status = await apiService.getBatchJobStatus(notebookId, batchJobId);
    console.log(`Progress: ${status.batch_job.progress_percentage}%`);
}

// Batch file uploads
const files = [file1, file2, file3];
const result = await apiService.parseFile(files, null, notebookId);

// Batch media URL parsing
const mediaUrls = ["https://youtube.com/watch?v=1", "https://youtube.com/watch?v=2"];
const result = await apiService.parseUrlWithMedia(mediaUrls, notebookId);
```

## API Response Formats

### Single Item Response (HTTP 201)

```json
{
  "success": true,
  "file_id": "f_12345",
  "knowledge_item_id": 67,
  "is_batch": false,
  "total_items": 1
}
```

### Batch Response (HTTP 202)

```json
{
  "success": true,
  "batch_job_id": 42,
  "total_items": 3,
  "message": "Batch processing started for 3 URLs",
  "is_batch": true
}
```

### Batch Status Response

```json
{
  "batch_job": {
    "id": 42,
    "job_type": "url_parse",
    "status": "processing",
    "total_items": 3,
    "completed_items": 1,
    "failed_items": 0,
    "processing_items": 1,
    "pending_items": 1,
    "progress_percentage": 33.3,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z"
  },
  "items": [
    {
      "id": 1,
      "status": "completed",
      "item_data": {"url": "https://example.com/1"},
      "upload_id": "abc123",
      "result": {"file_id": "f_12345", "knowledge_item_id": 67}
    },
    {
      "id": 2,
      "status": "processing",
      "item_data": {"url": "https://example.com/2"},
      "upload_id": "def456"
    },
    {
      "id": 3,
      "status": "pending",
      "item_data": {"url": "https://example.com/3"},
      "upload_id": "ghi789"
    }
  ]
}
```

## Backend Setup

### 1. Run Migrations

```bash
cd backend
conda activate deepsight
python manage.py migrate
```

### 2. Start Celery Worker

```bash
# In a separate terminal
cd backend
conda activate deepsight
celery -A backend worker -l info -Q notebook_processing
```

### 3. Start Redis (if not running)

```bash
redis-server
```

## Frontend Integration

### Detecting Batch vs Single Responses

```javascript
async function handleParseResult(result, notebookId) {
    if (result.is_batch) {
        // Handle batch processing
        const batchJobId = result.batch_job_id;
        console.log(`Started batch job ${batchJobId} with ${result.total_items} items`);
        
        // Poll for status updates
        const pollStatus = async () => {
            const status = await apiService.getBatchJobStatus(notebookId, batchJobId);
            const job = status.batch_job;
            
            console.log(`Progress: ${job.progress_percentage}%`);
            
            if (job.status === 'completed') {
                console.log('Batch completed successfully!');
                // Refresh file list or handle completion
            } else if (job.status === 'failed') {
                console.error('Batch failed');
            } else if (job.status === 'partially_completed') {
                console.warn(`Batch partially completed: ${job.completed_items}/${job.total_items}`);
            } else {
                // Still processing, check again
                setTimeout(pollStatus, 2000);
            }
        };
        
        pollStatus();
    } else {
        // Handle single item processing (existing logic)
        console.log(`Single item processed: ${result.file_id}`);
    }
}
```

### Updating UI Components

Your existing UI components will continue to work without changes. To add batch support:

```javascript
// In your file upload handler
async function handleMultipleFiles(files, notebookId) {
    if (files.length === 1) {
        // Single file - existing behavior
        return await apiService.parseFile(files[0], null, notebookId);
    } else {
        // Multiple files - new batch behavior
        return await apiService.parseFile(files, null, notebookId);
    }
}

// In your URL parsing handler
async function handleMultipleUrls(urls, notebookId) {
    if (urls.length === 1) {
        // Single URL - existing behavior
        return await apiService.parseUrl(urls[0], notebookId);
    } else {
        // Multiple URLs - new batch behavior
        return await apiService.parseUrl(urls, notebookId);
    }
}
```

## Benefits

1. **No Database Locks**: Async processing eliminates SQLite locking issues
2. **Better Performance**: Multiple items processed concurrently via Celery
3. **Progress Tracking**: Real-time status updates for batch operations
4. **Backward Compatibility**: Existing code continues to work unchanged
5. **Scalable**: Can handle large batches efficiently
6. **No New Endpoints**: Uses existing URLs with enhanced functionality

## Troubleshooting

### Common Issues

1. **Celery Worker Not Running**
   ```bash
   # Start Celery worker
   celery -A backend worker -l info -Q notebook_processing
   ```

2. **Redis Connection Issues**
   ```bash
   # Check Redis status
   redis-cli ping
   # Should return "PONG"
   ```

3. **Task Import Errors**
   - Ensure `notebooks/tasks.py` is properly imported
   - Check Celery configuration in `backend/celery.py`

### Monitoring

1. **Check Batch Job Status**
   ```bash
   # Django shell
   python manage.py shell
   >>> from notebooks.models import BatchJob
   >>> BatchJob.objects.all()
   ```

2. **Monitor Celery Tasks**
   ```bash
   # Celery monitor
   celery -A backend events
   ```

## Migration Path

1. **Phase 1**: Deploy the new code (backward compatible)
2. **Phase 2**: Update frontend to use batch processing for multiple items
3. **Phase 3**: Optimize UI for better batch operation UX

The system is designed to be deployed without breaking existing functionality, allowing for gradual adoption of batch processing features. 