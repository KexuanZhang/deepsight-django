"""
Simplified Celery tasks for async processing of notebook content.
"""

import logging
import tempfile
import os
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from asgiref.sync import async_to_sync
from uuid import uuid4

from .models import Source, KnowledgeItem, KnowledgeBaseItem, Notebook, BatchJob, BatchJobItem
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


@shared_task(bind=True)
def generate_image_captions_task(self, kb_item_id):
    """Generate captions for images in a knowledge base item asynchronously."""
    try:
        from .models import KnowledgeBaseItem, KnowledgeBaseImage
        from datetime import datetime
        from uuid import UUID
        
        logger.info(f"Starting caption generation task for KB item: {kb_item_id}")
        
        # Convert string back to UUID if needed
        if isinstance(kb_item_id, str):
            try:
                kb_item_id = UUID(kb_item_id)
            except ValueError as e:
                logger.error(f"Invalid UUID format: {kb_item_id}")
                return {"status": "error", "message": f"Invalid UUID format: {kb_item_id}"}
        
        # Get the knowledge base item
        kb_item = KnowledgeBaseItem.objects.filter(id=kb_item_id).first()
        if not kb_item:
            logger.warning(f"Knowledge base item {kb_item_id} not found")
            return {"status": "error", "message": "Knowledge base item not found"}
        
        # Mark caption generation as in progress
        if not kb_item.file_metadata:
            kb_item.file_metadata = {}
        
        kb_item.file_metadata['caption_generation_status'] = 'in_progress'
        kb_item.save()
        
        # Get images that need captions
        images_needing_captions = KnowledgeBaseImage.objects.filter(
            knowledge_base_item=kb_item,
            image_caption__in=['', None]
        )
        
        if not images_needing_captions.exists():
            kb_item.file_metadata['caption_generation_status'] = 'completed'
            kb_item.save()
            return {"status": "success", "message": "No images need captions"}
        
        # Generate captions directly without importing upload_processor to avoid circular imports
        try:
            updated_count = 0
            ai_generated_count = 0
            
            # Get markdown content for caption extraction
            markdown_content = None
            if kb_item.content:
                markdown_content = kb_item.content
            elif kb_item.file_object_key:
                try:
                    markdown_content = kb_item.get_file_content()
                except Exception as e:
                    logger.warning(f"Could not get markdown content for KB item {kb_item_id}: {e}")
            
            # Extract figure data from markdown if available
            figure_data = []
            if markdown_content:
                try:
                    # Import here to avoid issues
                    from reports.image_utils import extract_figure_data_from_markdown
                    
                    # Create a temporary markdown file for extraction
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_file:
                        temp_file.write(markdown_content)
                        temp_file_path = temp_file.name
                    
                    try:
                        figure_data = extract_figure_data_from_markdown(temp_file_path) or []
                    finally:
                        if os.path.exists(temp_file_path):
                            os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Could not extract figure data for KB item {kb_item_id}: {e}")
            
            # Process each image
            for image in images_needing_captions:
                try:
                    caption = None
                    caption_source = None
                    
                    # Try to find caption from markdown first
                    if figure_data:
                        caption = _find_caption_for_image(image, figure_data, images_needing_captions)
                        if caption:
                            caption_source = "markdown"
                    
                    # Use AI generation as fallback if no caption found from markdown
                    if not caption:
                        try:
                            from notebooks.utils.image_processing.caption_generator import generate_caption_for_image
                            
                            # Download image to temp file for AI captioning
                            temp_image_path = _download_image_to_temp(image)
                            if temp_image_path:
                                try:
                                    caption = generate_caption_for_image(temp_image_path)
                                    if caption and not caption.startswith("Caption generation failed"):
                                        caption_source = "AI"
                                        ai_generated_count += 1
                                finally:
                                    if os.path.exists(temp_image_path):
                                        os.unlink(temp_image_path)
                        except Exception as e:
                            logger.warning(f"AI caption generation failed for image {image.id}: {e}")
                    
                    # Update the image with the caption
                    if caption:
                        image.image_caption = caption
                        image.save(update_fields=['image_caption', 'updated_at'])
                        updated_count += 1
                        logger.info(f"Updated image {image.id} with {caption_source} caption: {caption[:50]}...")
                    else:
                        logger.warning(f"No caption found for image {image.id}")
                
                except Exception as e:
                    logger.error(f"Error processing image {image.id}: {e}")
            
            # Mark as completed
            kb_item.file_metadata['caption_generation_status'] = 'completed'
            kb_item.file_metadata['caption_generation_completed_at'] = datetime.now().isoformat()
            kb_item.save()
            
            logger.info(f"Successfully generated captions for {updated_count} images in KB item {kb_item_id} ({ai_generated_count} AI-generated)")
            
            return {
                "status": "success",
                "kb_item_id": kb_item_id,
                "images_processed": updated_count,
                "ai_generated": ai_generated_count
            }
            
        except Exception as e:
            # Mark as failed
            kb_item.file_metadata['caption_generation_status'] = 'failed'
            kb_item.file_metadata['caption_generation_error'] = str(e)
            kb_item.save()
            
            logger.error(f"Caption generation failed for KB item {kb_item_id}: {e}")
            raise e
        
    except Exception as e:
        logger.error(f"Error in generate_image_captions_task for KB item {kb_item_id}: {e}")
        return {"status": "error", "message": str(e)}


def _find_caption_for_image(image, figure_data, all_images):
    """Find matching caption for an image from figure data."""
    try:
        # Try to match by image name from object key first
        if image.minio_object_key:
            image_basename = os.path.basename(image.minio_object_key).lower()
            for figure in figure_data:
                figure_image_path = figure.get('image_path', '')
                if figure_image_path:
                    figure_basename = figure_image_path.split('/')[-1].lower()
                    if figure_basename == image_basename:
                        return figure.get('caption', '')
        
        # Fallback: match by index in the figure data list
        if figure_data:
            try:
                image_index = list(all_images).index(image)
                if image_index < len(figure_data):
                    return figure_data[image_index].get('caption', '')
            except (ValueError, IndexError):
                pass
        
        return None
        
    except Exception as e:
        logger.error(f"Error finding caption for image {image.id}: {e}")
        return None


def _download_image_to_temp(image):
    """Download image from MinIO to a temporary file for caption generation."""
    try:
        # Get image content from MinIO
        image_content = image.get_image_content()
        
        if not image_content:
            return None
        
        # Determine file extension from content type or object key
        file_extension = '.png'  # default
        if image.content_type:
            if 'jpeg' in image.content_type or 'jpg' in image.content_type:
                file_extension = '.jpg'
            elif 'png' in image.content_type:
                file_extension = '.png'
            elif 'gif' in image.content_type:
                file_extension = '.gif'
            elif 'webp' in image.content_type:
                file_extension = '.webp'
        elif image.minio_object_key:
            object_key_lower = image.minio_object_key.lower()
            if object_key_lower.endswith('.jpg') or object_key_lower.endswith('.jpeg'):
                file_extension = '.jpg'
            elif object_key_lower.endswith('.png'):
                file_extension = '.png'
            elif object_key_lower.endswith('.gif'):
                file_extension = '.gif'
            elif object_key_lower.endswith('.webp'):
                file_extension = '.webp'
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            suffix=file_extension, 
            delete=False
        ) as temp_file:
            temp_file.write(image_content)
            temp_file_path = temp_file.name
        
        return temp_file_path
        
    except Exception as e:
        logger.error(f"Error downloading image {image.id} to temp file: {e}")
        return None


@shared_task
def test_caption_generation_task(kb_item_id):
    """Test task to verify caption generation works."""
    logger.info(f"Test caption generation task called with kb_item_id: {kb_item_id}")
    return {"status": "test_success", "kb_item_id": kb_item_id}


@shared_task
def health_check_task():
    """Simple health check task for monitoring Celery workers."""
    from datetime import datetime
    logger.info("Celery health check completed")
    return {"status": "healthy", "timestamp": datetime.now().isoformat()} 