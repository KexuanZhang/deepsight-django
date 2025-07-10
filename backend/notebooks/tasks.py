"""
Celery tasks for async processing of notebook content.
"""

import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from asgiref.sync import async_to_sync
from uuid import uuid4
import os

from .models import Source, URLProcessingResult, KnowledgeItem, KnowledgeBaseItem, Notebook, BatchJob, BatchJobItem
from .utils.url_extractor import URLExtractor
from .utils.media_extractor import MediaFeatureExtractor
from .utils.upload_processor import UploadProcessor
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)

# Initialize processors
url_extractor = URLExtractor()
media_extractor = MediaFeatureExtractor()
upload_processor = UploadProcessor()


@shared_task(bind=True)
def process_url_task(self, url, notebook_id, user_id, upload_url_id=None, batch_job_id=None, batch_item_id=None):
    """Process a single URL asynchronously."""
    try:
        # Get required objects
        notebook = Notebook.objects.get(id=notebook_id, user_id=user_id)
        user = User.objects.get(id=user_id)
        
        # Update batch item status if this is part of a batch
        if batch_item_id:
            batch_item = BatchJobItem.objects.get(id=batch_item_id)
            batch_item.status = 'processing'
            batch_item.save()
        
        # Process the URL using async function
        async def process_url_async():
            return await url_extractor.process_url(
                url=url,
                upload_url_id=upload_url_id or uuid4().hex,
                user_id=user_id,
                notebook_id=notebook_id
            )

        # Run async processing
        result = async_to_sync(process_url_async)()

        # Create source record
        source = Source.objects.create(
            notebook=notebook,
            source_type="url",
            title=url,
            needs_processing=False,
            processing_status="done",
        )

        # Create URL processing result
        URLProcessingResult.objects.create(
            source=source,
            content_md=result.get("content_preview", ""),
        )

        # Link to knowledge base
        kb_item_id = result['file_id']
        kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, user=user)
        
        ki, created = KnowledgeItem.objects.get_or_create(
            notebook=notebook,
            knowledge_base_item=kb_item,
            defaults={
                'source': source,
                'notes': f"Processed from URL: {url}"
            }
        )

        # Update batch item if this is part of a batch
        if batch_item_id:
            batch_item.status = 'completed'
            batch_item.result_data = {
                'file_id': kb_item_id,
                'knowledge_item_id': ki.id,
                'source_id': source.id
            }
            batch_item.save()
            
            # Check if batch is complete
            _check_batch_completion(batch_job_id)

        return {
            'success': True,
            'file_id': kb_item_id,
            'knowledge_item_id': ki.id,
            'source_id': source.id
        }

    except Exception as e:
        logger.error(f"Error processing URL {url}: {str(e)}")
        
        # Update batch item status on error
        if batch_item_id:
            try:
                batch_item = BatchJobItem.objects.get(id=batch_item_id)
                batch_item.status = 'failed'
                batch_item.error_message = str(e)
                batch_item.save()
                _check_batch_completion(batch_job_id)
            except:
                pass
        
        raise


@shared_task(bind=True)
def process_url_media_task(self, url, notebook_id, user_id, upload_url_id=None, batch_job_id=None, batch_item_id=None):
    """Process a single URL with media extraction asynchronously."""
    try:
        # Get required objects
        notebook = Notebook.objects.get(id=notebook_id, user_id=user_id)
        user = User.objects.get(id=user_id)
        
        # Update batch item status if this is part of a batch
        if batch_item_id:
            batch_item = BatchJobItem.objects.get(id=batch_item_id)
            batch_item.status = 'processing'
            batch_item.save()
        
        # Process the URL using async function
        async def process_url_media_async():
            return await url_extractor.process_url_media_only(
                url=url,
                upload_url_id=upload_url_id or uuid4().hex,
                user_id=user_id,
                notebook_id=notebook_id
            )

        # Run async processing
        result = async_to_sync(process_url_media_async)()

        # Create source record
        source = Source.objects.create(
            notebook=notebook,
            source_type="url",
            title=url,
            needs_processing=False,
            processing_status="done",
        )

        # Create URL processing result
        URLProcessingResult.objects.create(
            source=source,
            content_md=result.get("content_preview", ""),
        )

        # Link to knowledge base
        kb_item_id = result['file_id']
        kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, user=user)
        
        ki, created = KnowledgeItem.objects.get_or_create(
            notebook=notebook,
            knowledge_base_item=kb_item,
            defaults={
                'source': source,
                'notes': f"Processed from URL with media: {url}"
            }
        )

        # Update batch item if this is part of a batch
        if batch_item_id:
            batch_item.status = 'completed'
            batch_item.result_data = {
                'file_id': kb_item_id,
                'knowledge_item_id': ki.id,
                'source_id': source.id
            }
            batch_item.save()
            
            # Check if batch is complete
            _check_batch_completion(batch_job_id)

        return {
            'success': True,
            'file_id': kb_item_id,
            'knowledge_item_id': ki.id,
            'source_id': source.id
        }

    except Exception as e:
        logger.error(f"Error processing URL with media {url}: {str(e)}")
        
        # Update batch item status on error
        if batch_item_id:
            try:
                batch_item = BatchJobItem.objects.get(id=batch_item_id)
                batch_item.status = 'failed'
                batch_item.error_message = str(e)
                batch_item.save()
                _check_batch_completion(batch_job_id)
            except:
                pass
        
        raise


@shared_task(bind=True)
def process_file_upload_task(self, file_data, filename, notebook_id, user_id, upload_file_id=None, batch_job_id=None, batch_item_id=None):
    """Process a single file upload asynchronously."""
    try:
        # Get required objects
        notebook = Notebook.objects.get(id=notebook_id, user_id=user_id)
        user = User.objects.get(id=user_id)
        
        # Update batch item status if this is part of a batch
        if batch_item_id:
            batch_item = BatchJobItem.objects.get(id=batch_item_id)
            batch_item.status = 'processing'
            batch_item.save()
        
        # Create a temporary file-like object from the file data
        from django.core.files.base import ContentFile
        temp_file = ContentFile(file_data, name=filename)
        
        # Process the upload using async function
        async def process_upload_async():
            return await upload_processor.process_upload(
                temp_file,
                upload_file_id or uuid4().hex,
                user_pk=user_id,
                notebook_id=notebook_id,
            )

        # Run async processing
        result = async_to_sync(process_upload_async)()

        # Create source record
        source = Source.objects.create(
            notebook=notebook,
            source_type="file",
            title=filename,
            needs_processing=False,
            processing_status="done",
        )

        # Link to knowledge base
        kb_item_id = result["file_id"]
        kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, user=user)

        ki, created = KnowledgeItem.objects.get_or_create(
            notebook=notebook,
            knowledge_base_item=kb_item,
            defaults={
                "source": source,
                "notes": f"Processed from {filename}",
            },
        )

        # Update source if needed
        if not created and not ki.source:
            ki.source = source
            ki.save(update_fields=["source"])

        # Update batch item if this is part of a batch
        if batch_item_id:
            batch_item.status = 'completed'
            batch_item.result_data = {
                'file_id': kb_item_id,
                'knowledge_item_id': ki.id,
                'source_id': source.id
            }
            batch_item.save()
            
            # Check if batch is complete
            _check_batch_completion(batch_job_id)

        return {
            'success': True,
            'file_id': kb_item_id,
            'knowledge_item_id': ki.id,
            'source_id': source.id
        }

    except ValidationError as e:
        logger.warning(f"File validation failed for {filename}: {str(e)}")
        
        # Update batch item status on validation error
        if batch_item_id:
            try:
                batch_item = BatchJobItem.objects.get(id=batch_item_id)
                batch_item.status = 'failed'
                batch_item.error_message = f"File validation failed: {str(e)}"
                batch_item.save()
                _check_batch_completion(batch_job_id)
            except:
                pass
        
        raise
    except Exception as e:
        logger.error(f"Error processing file upload {filename}: {str(e)}")
        
        # Update batch item status on error
        if batch_item_id:
            try:
                batch_item = BatchJobItem.objects.get(id=batch_item_id)
                batch_item.status = 'failed'
                batch_item.error_message = str(e)
                batch_item.save()
                _check_batch_completion(batch_job_id)
            except:
                pass
        
        raise


def _check_batch_completion(batch_job_id):
    """Check if a batch job is complete and update its status."""
    if not batch_job_id:
        return
        
    try:
        batch_job = BatchJob.objects.get(id=batch_job_id)
        items = batch_job.items.all()
        
        if items.filter(status='pending').exists():
            return  # Still has pending items
            
        if items.filter(status='processing').exists():
            return  # Still has processing items
            
        # All items are either completed or failed
        completed_count = items.filter(status='completed').count()
        failed_count = items.filter(status='failed').count()
        
        if failed_count == 0:
            batch_job.status = 'completed'
        elif completed_count == 0:
            batch_job.status = 'failed'
        else:
            batch_job.status = 'partially_completed'
            
        batch_job.completed_items = completed_count
        batch_job.failed_items = failed_count
        batch_job.save()
        
    except ObjectDoesNotExist:
        pass 

# === NEW: asynchronous transcription task ===
@shared_task(bind=True, queue="notebook_processing")
def generate_transcript_task(self, file_id: str):
    """Generate transcript for a previously stored media file.

    Args:
        file_id: KnowledgeBaseItem primary key (string).
    Workflow:
        1. Locate the KnowledgeBaseItem and its original binary file path.
        2. Run Whisper transcription via UploadProcessor.
        3. Save the markdown transcript into the same KB directory
           using FileStorageService._save_organized_content_file().
        4. Update metadata (has_transcript, transcript_filename).
        5. Publish a Redis pub/sub event so clients can refresh.
    """
    from .utils.upload_processor import UploadProcessor
    from .utils.file_storage import FileStorageService
    from .models import KnowledgeBaseItem
    import redis
    from django.conf import settings

    try:
        kb_item = KnowledgeBaseItem.objects.get(id=file_id)
        user_id = kb_item.user_id

        file_storage = FileStorageService()
        upload_processor = UploadProcessor()

        # Get original binary file path (video/audio)
        original_path = file_storage.get_original_file_path(file_id, user_id)
        if not original_path or not os.path.exists(original_path):
            raise FileNotFoundError(f"Original file for {file_id} not found: {original_path}")

        # Run transcription (sync call inside Celery – already offloaded)
        transcript_content, transcript_filename = async_to_sync(
            upload_processor.transcribe_audio_video
        )(original_path, os.path.basename(original_path))

        # Persist transcript markdown next to existing KB item
        paths = file_storage._generate_knowledge_base_paths(user_id, transcript_filename, kb_item.id)
        file_storage._save_organized_content_file(kb_item, transcript_content, paths, content_filename=transcript_filename)

        # Update metadata
        metadata = kb_item.metadata or {}
        metadata.update({
            "has_transcript": True,
            "transcript_filename": transcript_filename,
        })
        kb_item.metadata = metadata
        kb_item.save(update_fields=["metadata"])

        # Notify listeners via Redis pub/sub
        redis_conn = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        redis_conn.publish("transcript_ready", str(file_id))

        return {"success": True, "file_id": file_id}

    except Exception as e:
        logger.error(f"generate_transcript_task error for {file_id}: {e}")
        raise 