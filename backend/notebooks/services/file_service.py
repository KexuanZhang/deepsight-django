"""
File Service - Handle file processing business logic
"""
import logging
from uuid import uuid4
from asgiref.sync import async_to_sync
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status

from ..models import Source, KnowledgeItem, KnowledgeBaseItem, BatchJob, BatchJobItem
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
    
    @transaction.atomic
    def handle_single_file_upload(self, file_obj, upload_id, notebook, user):
        """Process single file upload"""
        try:
            # 1) Process & save to KnowledgeBaseItem using original processor
            # (This handles the full upload pipeline including storage)
            result = async_to_sync(self.upload_processor.process_upload)(
                file_obj, upload_id, user_pk=user.pk, notebook_id=notebook.id
            )
            kb_item = get_object_or_404(KnowledgeBaseItem, id=result["file_id"], user=user)

            # 2) Create or update the link in KnowledgeItem
            source = Source.objects.create(
                notebook=notebook,
                source_type="file",
                title=file_obj.name,
                needs_processing=False,
                processing_status="done",
            )
            
            ki, created = KnowledgeItem.objects.get_or_create(
                notebook=notebook,
                knowledge_base_item=kb_item,
                defaults={"source": source, "notes": f"Processed {file_obj.name}"}
            )
            
            if not created and not ki.source:
                ki.source = source
                ki.save(update_fields=["source"])
            
            # 3) Add to user's RAG collection
            add_user_files(
                user_id=user.pk,
                kb_items=[kb_item],
            )

            return {
                "success": True,
                "file_id": kb_item.id,
                "knowledge_item_id": ki.id,
                "status_code": status.HTTP_201_CREATED,
                "refresh_source_list": True  # Signal frontend to refresh source list
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

            # Process each file
            for file_obj in files:
                upload_id = uuid4().hex
                data = file_obj.read()
                file_obj.seek(0)

                batch_item = BatchJobItem.objects.create(
                    batch_job=batch_job,
                    item_data={'filename': file_obj.name, 'size': len(data)},
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
                    batch_item_id=batch_item.id
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