"""
File Service - Handle file processing business logic
"""
import logging
from uuid import uuid4
from asgiref.sync import async_to_sync
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status

from ..models import KnowledgeBaseItem, BatchJob, BatchJobItem
from ..processors.upload_processor import UploadProcessor
from ..processors import FileProcessor
from rag.rag import add_user_files

logger = logging.getLogger(__name__)


class FileService:
    """Handle file processing business logic"""
    
    def __init__(self):
        # Use new focused file processor
        self.file_processor = FileProcessor()
        # Keep original upload processor for full pipeline
        self.upload_processor = UploadProcessor()
    
    def handle_single_file_upload(self, file_obj, upload_id, notebook, user):
        """Process single file upload"""
        kb_item = None
        try:
            # Step 1: Create KnowledgeBaseItem immediately in separate transaction
            with transaction.atomic():
                # Create KnowledgeBaseItem with processing_status="processing" directly in notebook
                kb_item = KnowledgeBaseItem.objects.create(
                    notebook=notebook,
                    title=file_obj.name,
                    content_type="document",
                    processing_status="processing",
                    notes=f"Processing {file_obj.name}"
                )

            # Step 2: Queue file processing to Celery (async)
            try:
                # Read file data for Celery task
                file_data = file_obj.read()
                file_obj.seek(0)  # Reset file pointer
                
                # Queue the processing task
                from ..tasks import process_file_upload_task
                process_file_upload_task.delay(
                    file_data=file_data,
                    filename=file_obj.name,
                    notebook_id=notebook.id,
                    user_id=user.pk,
                    upload_file_id=upload_id,
                    kb_item_id=str(kb_item.id)  # Pass our pre-created kb_item ID
                )
                
                logger.info(f"Queued file processing task for {file_obj.name} (kb_item: {kb_item.id})")
                
            except Exception as queue_error:
                # Update processing status to error if queueing fails
                kb_item.processing_status = "error"
                kb_item.save(update_fields=["processing_status"])
                logger.error(f"Failed to queue processing for {file_obj.name}: {queue_error}")
                # Don't re-raise - return success so frontend shows the item with error status
                
            return {
                "success": True,
                "file_id": kb_item.id,
                "knowledge_item_id": kb_item.id,
                "upload_id": upload_id,
                "status_code": status.HTTP_201_CREATED,
                "message": "File uploaded and processing started",
                "refresh_source_list": True,  # Trigger frontend refresh when processing complete
            }

        except Exception as e:
            logger.exception(f"Single file upload failed for {file_obj.name}: {e}")
            raise

    @transaction.atomic
    def handle_batch_file_upload(self, files, notebook, user):
        """Process batch file upload"""
        try:
            # Create batch job
            batch_job = BatchJob.objects.create(
                notebook=notebook,
                job_type='file_upload',
                total_items=len(files),
                status='processing'
            )

            # Process each file and create source/knowledge base items immediately
            for file_obj in files:
                upload_id = uuid4().hex
                data = file_obj.read()
                file_obj.seek(0)

                # Create KnowledgeBaseItem with processing_status="processing" directly in notebook
                kb_item = KnowledgeBaseItem.objects.create(
                    notebook=notebook,
                    title=file_obj.name,
                    content_type="document",
                    processing_status="processing"
                )

                batch_item = BatchJobItem.objects.create(
                    batch_job=batch_job,
                    item_data={'filename': file_obj.name, 'size': len(data), 'kb_item_id': str(kb_item.id)},
                    upload_id=upload_id,
                    status='pending'
                )

                # Enqueue Celery task for background processing
                from ..tasks import process_file_upload_task
                process_file_upload_task.delay(
                    file_data=data,
                    filename=file_obj.name,
                    notebook_id=notebook.id,
                    user_id=user.pk,
                    upload_file_id=upload_id,
                    batch_job_id=batch_job.id,
                    batch_item_id=batch_item.id,
                    kb_item_id=str(kb_item.id)  # Pass the kb_item_id to the task
                )

            return {
                'success': True,
                'batch_job_id': batch_job.id,
                'total_items': len(files),
                'message': f'Batch upload started for {len(files)} files',
                'status_code': status.HTTP_202_ACCEPTED
            }

        except Exception as e:
            logger.exception(f"Batch file upload failed: {e}")
            raise

    def process_file_by_type(self, file_path, file_metadata):
        """Process file using focused file processor"""
        return async_to_sync(self.file_processor.process_file_by_type)(file_path, file_metadata)

    def validate_file_upload(self, serializer):
        """Validate file upload data"""
        serializer.is_valid(raise_exception=True)
        file_obj = serializer.validated_data['file']
        upload_id = serializer.validated_data.get('upload_file_id') or uuid4().hex
        return file_obj, upload_id

    def validate_batch_file_upload(self, serializer):
        """Validate batch file upload data"""
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        if 'files' in validated_data:
            return validated_data['files']
        return None 