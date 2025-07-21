"""
Simplified Celery tasks for async processing of notebook content.
"""

import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from asgiref.sync import async_to_sync
from uuid import uuid4

from .models import Source, URLProcessingResult, KnowledgeItem, KnowledgeBaseItem, Notebook, BatchJob, BatchJobItem
from .exceptions import (
    FileProcessingError,
    URLProcessingError,
    NotebookNotFoundError,
    ValidationError
)
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)

# Services will be initialized lazily inside functions to avoid circular imports


@shared_task(bind=True)
def process_url_task(self, url, notebook_id, user_id, upload_url_id=None, batch_job_id=None, batch_item_id=None):
    """Process a single URL asynchronously."""
    try:
        # Import services lazily to avoid circular imports
        from .services.url_service import URLService
        from .services.notebook_service import NotebookService
        
        url_service = URLService()
        notebook_service = NotebookService()
        
        # Validate inputs
        if not url or not notebook_id or not user_id:
            raise ValidationError("Missing required parameters")
        
        # Get required objects
        user = User.objects.get(id=user_id)
        notebook = notebook_service.get_notebook_or_404(notebook_id, user)
        
        # Update batch item status if this is part of a batch
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'processing')
        
        # Process the URL using service
        result = url_service.process_url(
            url=url,
            upload_url_id=upload_url_id or uuid4().hex,
            user=user,
            notebook=notebook
        )
        
        # Update batch item status on success
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'completed', result_data=result)
        
        # Check if batch is complete
        if batch_job_id:
            _check_batch_completion(batch_job_id)
        
        logger.info(f"Successfully processed URL: {url}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        
        # Update batch item status on failure
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'failed', error_message=str(e))
        
        # Check if batch is complete
        if batch_job_id:
            _check_batch_completion(batch_job_id)
        
        raise URLProcessingError(f"Failed to process URL: {str(e)}")


@shared_task(bind=True)
def process_url_media_task(self, url, notebook_id, user_id, upload_url_id=None, batch_job_id=None, batch_item_id=None):
    """Process a single URL with media extraction asynchronously."""
    try:
        # Import services lazily to avoid circular imports
        from .services.url_service import URLService
        from .services.notebook_service import NotebookService
        
        url_service = URLService()
        notebook_service = NotebookService()
        
        # Validate inputs
        if not url or not notebook_id or not user_id:
            raise ValidationError("Missing required parameters")
        
        # Get required objects
        user = User.objects.get(id=user_id)
        notebook = notebook_service.get_notebook_or_404(notebook_id, user)
        
        # Update batch item status if this is part of a batch
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'processing')
        
        # Process the URL with media using service
        result = url_service.process_url_with_media(
            url=url,
            upload_url_id=upload_url_id or uuid4().hex,
            user=user,
            notebook=notebook
        )
        
        # Update batch item status on success
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'completed', result_data=result)
        
        # Check if batch is complete
        if batch_job_id:
            _check_batch_completion(batch_job_id)
        
        logger.info(f"Successfully processed URL with media: {url}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing URL with media {url}: {e}")
        
        # Update batch item status on failure
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'failed', error_message=str(e))
        
        # Check if batch is complete
        if batch_job_id:
            _check_batch_completion(batch_job_id)
        
        raise URLProcessingError(f"Failed to process URL with media: {str(e)}")


@shared_task(bind=True)
def process_file_upload_task(self, file_data, filename, notebook_id, user_id, upload_file_id=None, batch_job_id=None, batch_item_id=None):
    """Process a single file upload asynchronously."""
    try:
        # Import services lazily to avoid circular imports
        from .services.file_service import FileService
        from .services.notebook_service import NotebookService
        
        file_service = FileService()
        notebook_service = NotebookService()
        
        # Validate inputs
        if not file_data or not filename or not notebook_id or not user_id:
            raise ValidationError("Missing required parameters")
        
        # Get required objects
        user = User.objects.get(id=user_id)
        notebook = notebook_service.get_notebook_or_404(notebook_id, user)
        
        # Update batch item status if this is part of a batch
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'processing')
        
        # Create a temporary file-like object from the file data
        from django.core.files.base import ContentFile
        temp_file = ContentFile(file_data, name=filename)
        
        # Process the upload using service
        result = file_service.upload_file(
            file=temp_file,
            upload_file_id=upload_file_id or uuid4().hex,
            user=user,
            notebook=notebook
        )
        
        # Update batch item status on success
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'completed', result_data=result)
        
        # Check if batch is complete
        if batch_job_id:
            _check_batch_completion(batch_job_id)
        
        logger.info(f"Successfully processed file upload: {filename}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing file upload {filename}: {e}")
        
        # Update batch item status on failure
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'failed', error_message=str(e))
        
        # Check if batch is complete
        if batch_job_id:
            _check_batch_completion(batch_job_id)
        
        raise FileProcessingError(f"Failed to process file upload: {str(e)}")


def _update_batch_item_status(batch_item_id, status, result_data=None, error_message=None):
    """Update the status of a batch job item."""
    try:
        batch_item = BatchJobItem.objects.get(id=batch_item_id)
        batch_item.status = status
        
        if result_data:
            batch_item.result_data = result_data
        
        if error_message:
            batch_item.error_message = error_message
        
        batch_item.save()
        
    except ObjectDoesNotExist:
        logger.warning(f"Batch item {batch_item_id} not found")


def _check_batch_completion(batch_job_id):
    """Check if a batch job is complete and update its status."""
    try:
        batch_job = BatchJob.objects.get(id=batch_job_id)
        items = batch_job.items.all()
        
        # Check if any items are still pending or processing
        if items.filter(status__in=['pending', 'processing']).exists():
            return  # Still has items in progress
        
        # All items are either completed or failed
        completed_count = items.filter(status='completed').count()
        failed_count = items.filter(status='failed').count()
        
        # Update batch job status
        if failed_count == 0:
            batch_job.status = 'completed'
        elif completed_count == 0:
            batch_job.status = 'failed'
        else:
            batch_job.status = 'partially_completed'
        
        batch_job.completed_items = completed_count
        batch_job.failed_items = failed_count
        batch_job.save()
        
        logger.info(f"Batch job {batch_job_id} completed: {completed_count} successful, {failed_count} failed")
        
    except ObjectDoesNotExist:
        logger.warning(f"Batch job {batch_job_id} not found")


@shared_task
def cleanup_old_batch_jobs():
    """Cleanup old completed batch jobs (older than 7 days)."""
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.now() - timedelta(days=7)
    
    # Delete old completed batch jobs
    old_jobs = BatchJob.objects.filter(
        status__in=['completed', 'failed', 'partially_completed'],
        updated_at__lt=cutoff_date
    )
    
    count = old_jobs.count()
    old_jobs.delete()
    
    logger.info(f"Cleaned up {count} old batch jobs")
    return count


@shared_task
def health_check_task():
    """Simple health check task for monitoring Celery workers."""
    logger.info("Celery health check completed")
    return {"status": "healthy", "timestamp": datetime.now().isoformat()} 