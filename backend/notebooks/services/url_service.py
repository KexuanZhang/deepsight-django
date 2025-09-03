"""
URL Service - Handle URL processing business logic following Django patterns.
"""
import logging
from uuid import uuid4
from typing import Dict, List, Optional
from asgiref.sync import async_to_sync
from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import status

from ..models import KnowledgeBaseItem, BatchJob, BatchJobItem
from ..processors.url_extractor import URLExtractor
from core.services import NotebookBaseService

logger = logging.getLogger(__name__)


class URLService(NotebookBaseService):
    """Handle URL processing business logic following Django patterns."""
    
    def __init__(self):
        super().__init__()
        # Keep original url extractor for full pipeline
        self.url_extractor = URLExtractor()
    
    @transaction.atomic
    def handle_single_url_parse(self, url, upload_url_id, notebook, user):
        """Handle single URL parsing (original behavior)"""
        try:
            # Process the URL using async function
            async def process_url_async():
                return await self.url_extractor.process_url(
                    url=url,
                    upload_url_id=upload_url_id,
                    user_id=user.pk,
                    notebook_id=notebook.id
                )

            # Run async processing using async_to_sync
            result = async_to_sync(process_url_async)()

            # Create KnowledgeBaseItem with processing_status="processing" directly in notebook


            # Ingest the KB item content for this URL
            if result.get("file_id"):
                # Security: Verify the knowledge base item belongs to the verified notebook
                kb_item = KnowledgeBaseItem.objects.filter(id=result["file_id"], notebook=notebook).first()
                if kb_item:
                    add_user_files(user_id=user.pk, kb_items=[kb_item])

            return {
                "success": True,
                "upload_url_id": upload_url_id,
                "file_id": result.get("file_id"),
                "status_code": status.HTTP_201_CREATED
            }

        except Exception as e:
            logger.exception(f"Single URL parsing failed for {url}: {e}")
            raise

    @transaction.atomic
    def handle_batch_url_parse(self, validated_data, notebook, user):
        """Handle batch URL parsing"""
        try:
            urls = validated_data['urls']
            upload_url_id = validated_data.get('upload_url_id', uuid4().hex)

            # Create batch job
            batch_job = BatchJob.objects.create(
                notebook=notebook,
                job_type='url_parse',
                total_items=len(urls),
                status='processing'
            )

            results = []
            for url in urls:
                individual_upload_id = f"{upload_url_id}_{uuid4().hex[:8]}"
                
                batch_item = BatchJobItem.objects.create(
                    batch_job=batch_job,
                    item_data={'url': url},
                    upload_id=individual_upload_id,
                    status='pending'
                )

                try:
                    # Process each URL individually
                    result = self.handle_single_url_parse(url, individual_upload_id, notebook, user)
                    
                    batch_item.status = 'completed'
                    batch_item.result_data = result
                    batch_item.save()
                    
                    results.append({
                        'url': url,
                        'upload_url_id': individual_upload_id,
                        'success': True
                    })
                    
                except Exception as e:
                    batch_item.status = 'failed'
                    batch_item.error_message = str(e)
                    batch_item.save()
                    
                    results.append({
                        'url': url,
                        'upload_url_id': individual_upload_id,
                        'success': False,
                        'error': str(e)
                    })

            # Update batch job status
            completed_items = sum(1 for r in results if r['success'])
            failed_items = len(results) - completed_items
            
            batch_job.completed_items = completed_items
            batch_job.failed_items = failed_items
            batch_job.status = 'completed' if failed_items == 0 else 'partial'
            batch_job.save()

            return {
                'success': True,
                'batch_job_id': batch_job.id,
                'total_items': len(urls),
                'completed_items': completed_items,
                'failed_items': failed_items,
                'results': results,
                'status_code': status.HTTP_201_CREATED
            }

        except Exception as e:
            logger.exception(f"Batch URL parsing failed: {e}")
            raise

    @transaction.atomic
    def handle_url_with_media(self, url, upload_url_id, notebook, user):
        """Handle URL parsing with media extraction"""
        try:
            # Similar to single URL parse but with media extraction
            async def process_url_with_media_async():
                return await self.url_extractor.process_url_with_media(
                    url=url,
                    upload_url_id=upload_url_id,
                    user_id=user.pk,
                    notebook_id=notebook.id
                )

            result = async_to_sync(process_url_with_media_async)()

            # Create KnowledgeBaseItem with processing_status="processing" directly in notebook


            return {
                "success": True,
                "upload_url_id": upload_url_id,
                "file_id": result.get("file_id"),
                "status_code": status.HTTP_201_CREATED
            }

        except Exception as e:
            logger.exception(f"URL with media parsing failed for {url}: {e}")
            raise

    @transaction.atomic
    def handle_document_url(self, url, upload_url_id, notebook, user):
        """Handle document URL parsing"""
        try:
            async def process_document_url_async():
                return await self.url_extractor.process_url_document_only(
                    url=url,
                    upload_url_id=upload_url_id,
                    user_id=user.pk,
                    notebook_id=notebook.id
                )

            result = async_to_sync(process_document_url_async)()

            # Create KnowledgeBaseItem with processing_status="processing" directly in notebook


            return {
                "success": True,
                "upload_url_id": upload_url_id,
                "file_id": result.get("file_id"),
                "status_code": status.HTTP_201_CREATED
            }

        except Exception as e:
            logger.exception(f"Document URL parsing failed for {url}: {e}")
            raise

    def validate_url_request(self, serializer):
        """Validate URL request data"""
        serializer.is_valid(raise_exception=True)
        url = serializer.validated_data["url"]
        upload_url_id = serializer.validated_data.get("upload_url_id") or uuid4().hex
        return url, upload_url_id

    def validate_batch_url_request(self, serializer):
        """Validate batch URL request data"""
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        
        if 'urls' in validated_data:
            return validated_data
        else:
            # Convert single URL to single format for backward compatibility
            url = validated_data.get('url')
            upload_url_id = validated_data.get('upload_url_id', uuid4().hex)
            return {'url': url, 'upload_url_id': upload_url_id}