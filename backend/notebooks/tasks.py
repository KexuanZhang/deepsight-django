"""
Simplified Celery tasks for async processing of notebook content.
"""

import logging
import tempfile
import os
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from asgiref.sync import async_to_sync
from uuid import uuid4

from .models import KnowledgeBaseItem, Notebook, BatchJob, BatchJobItem
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
def process_url_task(self, url, notebook_id, user_id, upload_url_id=None, batch_job_id=None, batch_item_id=None, kb_item_id=None):
    """Process a single URL asynchronously."""
    try:
        # Import services lazily to avoid circular imports
        from .services.notebook_service import NotebookService
        from .utils.helpers import clean_title
        
        notebook_service = NotebookService()
        
        # Validate inputs
        if not url or not notebook_id or not user_id:
            raise ValidationError("Missing required parameters")
        
        # Get required objects
        user = User.objects.get(id=user_id)
        notebook = get_object_or_404(Notebook, id=notebook_id, user=user)
        
        # Update batch item status if this is part of a batch
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'processing')
        
        # Step 1: Get or create KnowledgeBaseItem
        kb_item = None
        if kb_item_id:
            # Use existing KnowledgeBaseItem (created by the view)
            try:
                kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
            except KnowledgeBaseItem.DoesNotExist:
                logger.error(f"Pre-created KnowledgeBaseItem {kb_item_id} not found")
                # Fallback: create new one
                kb_item = None
        
        if not kb_item:
            # Create new KnowledgeBaseItem (fallback or batch processing)
            kb_item = KnowledgeBaseItem.objects.create(
                notebook=notebook,
                parsing_status="queueing",  # Start in queueing state
                title=clean_title(url),
                content_type="webpage",
                notes=f"Processing URL: {url}",
                tags=[],  # Explicitly set empty list
                file_metadata={},  # Explicitly set empty dict
                metadata={
                    "source_url": url,
                    "upload_url_id": upload_url_id or uuid4().hex,
                    "processing_metadata": {
                        "extraction_type": "url_extractor",
                        "processing_type": "url_content"
                    }
                }
            )

        # Step 4: Now process the URL using url extractor
        from .processors.url_extractor import URLExtractor
        from asgiref.sync import async_to_sync
        
        url_extractor = URLExtractor()
        
        # Process the URL using async function - but modify it to update existing item
        async def process_url_async():
            return await url_extractor.process_url_update_existing(
                url=url,
                kb_item_id=str(kb_item.id),
                upload_url_id=upload_url_id or uuid4().hex,
                user_id=user.pk,
                notebook_id=str(notebook.id)
            )

        try:
            # Update status to in_progress before starting processing
            kb_item.parsing_status = "parsing"
            kb_item.save(update_fields=["parsing_status"])
            
            # Run async processing using async_to_sync
            result = async_to_sync(process_url_async)()
            
            # Step 5: Update status to done (this will trigger SSE update)
            kb_item.parsing_status = "done"
            kb_item.save(update_fields=["parsing_status"])

            # Upload to RagFlow dataset if content is available
            if kb_item.content:  # Ensure content exists
                try:
                    from .services.ragflow_service import RagFlowService
                    ragflow_service = RagFlowService()
                    
                    # Upload knowledge item content to RagFlow
                    upload_result = ragflow_service.upload_knowledge_item_content(kb_item)
                    if upload_result.get('success'):
                        logger.info(f"Successfully uploaded KB item {kb_item.id} to RagFlow: {upload_result.get('ragflow_document_id')}")
                    else:
                        logger.warning(f"Failed to upload KB item {kb_item.id} to RagFlow: {upload_result.get('error')}")
                        
                except Exception as ragflow_error:
                    logger.error(f"RagFlow upload error for KB item {kb_item.id}: {ragflow_error}")
                    # Don't fail the task - content processing was successful
                
                # Keep legacy RAG collection for now (will be removed later)
                try:
                    add_user_files(user_id=user.pk, kb_items=[kb_item])
                except Exception as legacy_rag_error:
                    logger.error(f"Legacy RAG processing error for KB item {kb_item.id}: {legacy_rag_error}")
                    # Don't fail the task
            
            # Update batch item status on success
            if batch_item_id:
                _update_batch_item_status(batch_item_id, 'completed', result_data={"file_id": str(kb_item.id)})
            
            # Check if batch is complete
            if batch_job_id:
                _check_batch_completion(batch_job_id)
            
            logger.info(f"Successfully processed URL: {url}")
            return {"file_id": str(kb_item.id), "url": url, "status": "completed"}
        
        except Exception as processing_error:
            # Update status to error (this will trigger SSE update)
            kb_item.parsing_status = "done"
            kb_item.metadata = kb_item.metadata or {}
            kb_item.metadata["error_message"] = str(processing_error)
            kb_item.save(update_fields=["parsing_status", "metadata"])
            raise processing_error
        
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
        from .services.notebook_service import NotebookService
        from .utils.helpers import clean_title
        
        notebook_service = NotebookService()
        
        # Validate inputs
        if not url or not notebook_id or not user_id:
            raise ValidationError("Missing required parameters")
        
        # Get required objects
        user = User.objects.get(id=user_id)
        notebook = get_object_or_404(Notebook, id=notebook_id, user=user)
        
        # Update batch item status if this is part of a batch
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'processing')
        
        # Step 1: Create KnowledgeBaseItem directly in notebook with processing status
        kb_item = KnowledgeBaseItem.objects.create(
            notebook=notebook,
            parsing_status="queueing",  # Start in queueing state
            title=clean_title(url),
            content_type="media",
            tags=[],  # Explicitly set empty list
            file_metadata={},  # Explicitly set empty dict
            metadata={
                "source_url": url,
                "upload_url_id": upload_url_id or uuid4().hex,
                "processing_metadata": {
                    "extraction_type": "url_extractor",
                    "processing_type": "media"
                }
            }
        )


        # Step 4: Now process the URL with media using url extractor
        from .processors.url_extractor import URLExtractor
        from asgiref.sync import async_to_sync
        
        url_extractor = URLExtractor()
        
        # Process the URL using async function with media extraction
        async def process_url_with_media_async():
            return await url_extractor.process_url_with_media_update_existing(
                url=url,
                kb_item_id=str(kb_item.id),
                upload_url_id=upload_url_id or uuid4().hex,
                user_id=user.pk,
                notebook_id=notebook.id
            )

        try:
            # Update status to in_progress before starting processing
            kb_item.parsing_status = "parsing"
            kb_item.save(update_fields=["parsing_status"])
            
            # Run async processing using async_to_sync
            result = async_to_sync(process_url_with_media_async)()
            
            # Step 5: Update status to done (this will trigger SSE update)
            kb_item.parsing_status = "done"
            kb_item.save(update_fields=["parsing_status"])

            # Upload to RagFlow dataset if content is available
            if kb_item.content:  # Ensure content exists
                try:
                    from .services.ragflow_service import RagFlowService
                    ragflow_service = RagFlowService()
                    
                    # Upload knowledge item content to RagFlow
                    upload_result = ragflow_service.upload_knowledge_item_content(kb_item)
                    if upload_result.get('success'):
                        logger.info(f"Successfully uploaded KB item {kb_item.id} to RagFlow: {upload_result.get('ragflow_document_id')}")
                    else:
                        logger.warning(f"Failed to upload KB item {kb_item.id} to RagFlow: {upload_result.get('error')}")
                        
                except Exception as ragflow_error:
                    logger.error(f"RagFlow upload error for KB item {kb_item.id}: {ragflow_error}")
                    # Don't fail the task - content processing was successful
                
                # Keep legacy RAG collection for now (will be removed later)
                try:
                    add_user_files(user_id=user.pk, kb_items=[kb_item])
                except Exception as legacy_rag_error:
                    logger.error(f"Legacy RAG processing error for KB item {kb_item.id}: {legacy_rag_error}")
                    # Don't fail the task
            
            # Update batch item status on success
            if batch_item_id:
                _update_batch_item_status(batch_item_id, 'completed', result_data={"file_id": str(kb_item.id)})
            
            # Check if batch is complete
            if batch_job_id:
                _check_batch_completion(batch_job_id)
            
            logger.info(f"Successfully processed URL with media: {url}")
            return {"file_id": str(kb_item.id), "url": url, "status": "completed"}
        
        except Exception as processing_error:
            # Update status to error (this will trigger SSE update)
            kb_item.parsing_status = "done"
            kb_item.metadata = kb_item.metadata or {}
            kb_item.metadata["error_message"] = str(processing_error)
            kb_item.save(update_fields=["parsing_status", "metadata"])
            raise processing_error
        
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
def process_url_document_task(self, url, notebook_id, user_id, upload_url_id=None, batch_job_id=None, batch_item_id=None):
    """Process a single document URL asynchronously."""
    try:
        # Import services lazily to avoid circular imports
        from .services.notebook_service import NotebookService
        from .utils.helpers import clean_title
        
        notebook_service = NotebookService()
        
        # Validate inputs
        if not url or not notebook_id or not user_id:
            raise ValidationError("Missing required parameters")
        
        # Get required objects
        user = User.objects.get(id=user_id)
        notebook = get_object_or_404(Notebook, id=notebook_id, user=user)
        
        # Update batch item status if this is part of a batch
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'processing')
        
        # Step 1: Create KnowledgeBaseItem directly in notebook with processing status
        kb_item = KnowledgeBaseItem.objects.create(
            notebook=notebook,
            parsing_status="queueing",  # Start in queueing state
            title=clean_title(url),
            content_type="document",
            tags=[],  # Explicitly set empty list
            file_metadata={},  # Explicitly set empty dict
            metadata={
                "source_url": url,
                "upload_url_id": upload_url_id or uuid4().hex,
                "processing_metadata": {
                    "extraction_type": "url_extractor",
                    "processing_type": "document"
                }
            }
        )


        # Step 4: Now process the document URL using url extractor
        from .processors.url_extractor import URLExtractor
        from asgiref.sync import async_to_sync
        
        url_extractor = URLExtractor()
        
        # Process document URL asynchronously with existing KB item
        async def process_document_async():
            return await url_extractor.process_url_document_update_existing(
                url=url,
                kb_item_id=str(kb_item.id),
                upload_url_id=upload_url_id or uuid4().hex,
                user_id=user.pk,
                notebook_id=notebook.id
            )
        
        try:
            # Update status to in_progress before starting processing
            kb_item.parsing_status = "parsing"
            kb_item.save(update_fields=["parsing_status"])
            
            # Run async processing using async_to_sync
            result = async_to_sync(process_document_async)()
            
            # Step 5: Update status to done (this will trigger SSE update)
            kb_item.parsing_status = "done"
            kb_item.save(update_fields=["parsing_status"])
            
            # Update batch item status on success
            if batch_item_id:
                _update_batch_item_status(batch_item_id, 'completed', result_data={"file_id": str(kb_item.id)})
            
            # Check if batch is complete
            if batch_job_id:
                _check_batch_completion(batch_job_id)
            
            logger.info(f"Successfully processed document URL: {url}")
            return {"file_id": str(kb_item.id), "url": url, "status": "completed"}
        
        except Exception as processing_error:
            # Update status to error (this will trigger SSE update)
            kb_item.parsing_status = "done"
            kb_item.metadata = kb_item.metadata or {}
            kb_item.metadata["error_message"] = str(processing_error)
            kb_item.save(update_fields=["parsing_status", "metadata"])
            raise processing_error
        
    except Exception as e:
        logger.error(f"Error processing document URL {url}: {e}")
        
        # Update batch item status on failure
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'failed', error_message=str(e))
        
        # Check if batch is complete
        if batch_job_id:
            _check_batch_completion(batch_job_id)
        
        raise URLProcessingError(f"Failed to process document URL: {str(e)}")


@shared_task(bind=True)
def process_file_upload_task(self, file_data, filename, notebook_id, user_id, upload_file_id=None, batch_job_id=None, batch_item_id=None, kb_item_id=None):
    """Process a single file upload asynchronously with actual file processing."""
    try:
        # Import services and processors lazily to avoid circular imports
        from .processors.upload_processor import UploadProcessor
        from .services.notebook_service import NotebookService
        from django.core.files.base import ContentFile
        from django.shortcuts import get_object_or_404
        from django.db import transaction
        from asgiref.sync import async_to_sync
        
        # Initialize processors and services
        upload_processor = UploadProcessor()
        notebook_service = NotebookService()
        
        # Validate inputs
        if not file_data or not filename or not notebook_id or not user_id:
            raise ValidationError("Missing required parameters")
        
        # Get required objects
        user = User.objects.get(id=user_id)
        notebook = get_object_or_404(Notebook, id=notebook_id, user=user)
        
        # Update batch item status if this is part of a batch
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'processing')
        
        # Create a temporary file-like object from the file data
        temp_file = ContentFile(file_data, name=filename)
        
        # Log file size for debugging and check limits
        file_size_mb = len(file_data) / 1024 / 1024
        logger.info(f"Processing file {filename}: {file_size_mb:.2f} MB")
        
        # Check file size limit (prevent worker crashes on huge files)
        MAX_FILE_SIZE_MB = 500  # 500MB limit
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise ValidationError(f"File too large: {file_size_mb:.2f}MB (max: {MAX_FILE_SIZE_MB}MB)")
        
        # Get the pre-created KnowledgeBaseItem if provided
        kb_item = None
        if kb_item_id:
            try:
                # Security: Verify the knowledge base item belongs to the verified notebook
                kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
                # Update status to show parsing has started
                kb_item.parsing_status = "parsing"
                kb_item.save(update_fields=["parsing_status"])
            except KnowledgeBaseItem.DoesNotExist:
                logger.error(f"KnowledgeBaseItem {kb_item_id} not found in notebook {notebook_id}")
        
        # Process the file using upload processor
        result = async_to_sync(upload_processor.process_upload)(
            temp_file, upload_file_id or uuid4().hex, user_pk=user.pk, notebook_id=notebook.id, kb_item_id=kb_item_id
        )
        
        # If we had a pre-created kb_item, the processor updated it directly
        if kb_item_id:
            # Get the updated KnowledgeBaseItem
            kb_item = get_object_or_404(KnowledgeBaseItem, id=kb_item_id, notebook=notebook)
            
            # Update status to done - parsing is complete
            kb_item.parsing_status = "done"
            kb_item.save(update_fields=["parsing_status"])
            
            # Upload to RagFlow dataset if content is available
            try:
                from .services.ragflow_service import RagFlowService
                ragflow_service = RagFlowService()
                
                # Upload knowledge item content to RagFlow
                upload_result = ragflow_service.upload_knowledge_item_content(kb_item)
                if upload_result.get('success'):
                    logger.info(f"Successfully uploaded KB item {kb_item.id} to RagFlow: {upload_result.get('ragflow_document_id')}")
                else:
                    logger.warning(f"Failed to upload KB item {kb_item.id} to RagFlow: {upload_result.get('error')}")
                    
            except Exception as ragflow_error:
                logger.error(f"RagFlow upload error for KB item {kb_item.id}: {ragflow_error}")
                # Don't fail the task - content processing was successful
            
            # Keep legacy RAG collection for now (will be removed later)
            try:
                add_user_files(
                    user_id=user.pk,
                    kb_items=[kb_item],
                )
            except Exception as legacy_rag_error:
                logger.error(f"Legacy RAG processing error for KB item {kb_item.id}: {legacy_rag_error}")
                # Don't fail the task
            
            # Ensure the result uses our kb_item ID
            result["file_id"] = kb_item.id
        else:
            # No pre-created item, processor created new one
            processed_kb_item = get_object_or_404(KnowledgeBaseItem, id=result["file_id"], notebook=notebook)
            
            # Add to user's RAG collection
            add_user_files(
                user_id=user.pk,
                kb_items=[processed_kb_item],
            )
        
        # Update batch item status on success
        if batch_item_id:
            _update_batch_item_status(batch_item_id, 'completed', result_data=result)
        
        # Check if batch is complete
        if batch_job_id:
            _check_batch_completion(batch_job_id)
        
        logger.info(f"Successfully processed file upload: {filename} (kb_item: {result['file_id']})")
        
        # Clean up memory
        del file_data
        del temp_file
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing file upload {filename}: {e}")
        
        # Update the KnowledgeBaseItem status to error if we have one
        if kb_item_id:
            try:
                # Get notebook for security verification (needed since we're in exception handler)
                user = User.objects.get(id=user_id)
                notebook = Notebook.objects.get(id=notebook_id, user=user)
                # Security: Verify the knowledge base item belongs to the verified notebook
                kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
                kb_item.parsing_status = "done"  # Mark as done even if failed
                kb_item.save(update_fields=["parsing_status"])
                logger.info(f"Updated kb_item {kb_item_id} status to failed")
            except (KnowledgeBaseItem.DoesNotExist, Notebook.DoesNotExist):
                logger.error(f"Could not find kb_item {kb_item_id} to update error status")
        
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
            
            # Get markdown content for caption extraction using model manager
            try:
                markdown_content = KnowledgeBaseItem.objects.get_content(
                    str(kb_item.id), 
                    user_id=kb_item.notebook.user.pk
                )
            except Exception as e:
                logger.warning(f"Could not get markdown content for KB item {kb_item_id}: {e}")
                markdown_content = None
            
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

            # Proactively notify notebooks via SSE that associated file has updated
            try:
                from .signals import NotebookFileChangeNotifier
                # Since KnowledgeBaseItem is now directly linked to notebook
                if kb_item.notebook:
                    NotebookFileChangeNotifier.notify_file_change(
                        notebook_id=kb_item.notebook.id,
                        change_type='file_status_updated',
                        file_data={
                            'file_id': str(kb_item.id),
                            'title': kb_item.title,
                            # Use completed to indicate post-processing (captions) finished
                            'status': 'completed',
                            'parsing_status': kb_item.parsing_status,
                            # Include updated metadata so frontend knows captions are done
                            'metadata': kb_item.metadata,
                            'file_metadata': kb_item.file_metadata,
                        }
                    )
            except Exception as notify_err:
                logger.warning(f"Failed to send SSE caption completion notification for KB item {kb_item_id}: {notify_err}")
            
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