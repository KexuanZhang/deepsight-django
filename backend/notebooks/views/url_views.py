"""
URL Views - Handle URL processing operations only
"""
import logging
from uuid import uuid4

from asgiref.sync import async_to_sync
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Source, URLProcessingResult, KnowledgeItem, KnowledgeBaseItem, BatchJob, BatchJobItem
from ..serializers import (
    URLParseSerializer, URLParseWithMediaSerializer, URLParseDocumentSerializer,
    BatchURLParseSerializer, BatchURLParseWithMediaSerializer
)
from ..utils.view_mixins import StandardAPIView, NotebookPermissionMixin
from ..processors.url_extractor import URLExtractor

logger = logging.getLogger(__name__)

# Initialize URL extractor
url_extractor = URLExtractor()


class URLParseViewNew(StandardAPIView, NotebookPermissionMixin):
    """Handle URL parsing without media extraction - supports both single and batch processing."""
    
    parser_classes = [JSONParser]

    def post(self, request, notebook_id):
        """Parse URL content using crawl4ai only - supports single URL or multiple URLs."""
        try:
            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)
            
            # Try batch serializer first
            from ..serializers import BatchURLParseSerializer, URLParseSerializer
            batch_serializer = BatchURLParseSerializer(data=request.data)
            if batch_serializer.is_valid():
                validated_data = batch_serializer.validated_data
                
                # Check if this is a batch request (multiple URLs)
                if 'urls' in validated_data:
                    return self._handle_batch_url_parse(validated_data, notebook, request.user)
                else:
                    # Single URL - convert to single URL format for backward compatibility
                    url = validated_data.get('url')
                    upload_url_id = validated_data.get('upload_url_id', uuid4().hex)
                    return self._handle_single_url_parse(url, upload_url_id, notebook, request.user)
            
            # Fallback to original serializer for backward compatibility
            serializer = URLParseSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error_response(
                    "Invalid request data", 
                    details=serializer.errors
                )
            
            # Handle single URL with original logic
            url = serializer.validated_data["url"]
            upload_url_id = serializer.validated_data.get("upload_url_id") or uuid4().hex
            return self._handle_single_url_parse(url, upload_url_id, notebook, request.user)

        except Exception as e:
            return self.error_response(
                "URL parsing failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )
    
    def _handle_single_url_parse(self, url, upload_url_id, notebook, user):
        """Handle single URL parsing (original behavior)."""
        from asgiref.sync import async_to_sync
        
        # Process the URL using async function
        async def process_url_async():
            return await url_extractor.process_url(
                url=url,
                upload_url_id=upload_url_id,
                user_id=user.pk,
                notebook_id=notebook.id
            )

        # Run async processing using async_to_sync
        result = async_to_sync(process_url_async)()

        # Create source record
        from ..models import Source, URLProcessingResult
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
        kb_item = get_object_or_404(KnowledgeBaseItem, id=kb_item_id, user=user)
        
        ki, created = KnowledgeItem.objects.get_or_create(
            notebook=notebook,
            knowledge_base_item=kb_item,
            defaults={
                'source': source,
                'notes': f"Processed from URL: {url}"
            }
        )

        return Response(
            {
                "success": True,
                "file_id": kb_item_id,
                "knowledge_item_id": ki.id,
                "url": result.get("url", url),
                "title": result.get("title", ""),
                "extraction_method": result.get("extraction_method", "crawl4ai"),
                "content_preview": result.get("content_preview", ""),
            },
            status=status.HTTP_201_CREATED,
        )
    
    def _handle_batch_url_parse(self, validated_data, notebook, user):
        """Handle batch URL parsing."""
        from ..tasks import process_url_parse_task
        from ..models import BatchJob, BatchJobItem
        
        urls = validated_data.get('urls', [])
        batch_job_id = validated_data.get('batch_job_id') or uuid4().hex
        
        # Create batch job
        batch_job = BatchJob.objects.create(
            id=batch_job_id,
            notebook=notebook,
            job_type='url_parse',
            total_items=len(urls),
            status='processing'
        )
        
        # Create batch items and start processing
        for i, url_data in enumerate(urls):
            url = url_data.get('url')
            upload_url_id = url_data.get('upload_url_id', f"{batch_job_id}_{i}")
            
            batch_item = BatchJobItem.objects.create(
                batch_job=batch_job,
                item_data={'url': url, 'upload_url_id': upload_url_id},
                status='pending'
            )
            
            # Start async processing
            process_url_parse_task.delay(
                url=url,
                upload_url_id=upload_url_id,
                notebook_id=notebook.id,
                user_id=user.id,
                batch_job_id=batch_job_id,
                batch_item_id=batch_item.id
            )
        
        return self.success_response(
            "Batch URL processing started",
            data={
                "batch_job_id": batch_job_id,
                "total_urls": len(urls),
                "status": "processing"
            },
            status_code=status.HTTP_202_ACCEPTED
        )


# Test with basic APIView inheritance (no authentication)
class SimpleTestView(APIView):
    authentication_classes = []
    permission_classes = []
    """Ultra simple test view to check basic functionality"""
    
    def get(self, request, notebook_id):
        return Response({
            "message": "Simple GET works", 
            "notebook_id": notebook_id,
            "view_class": self.__class__.__name__,
            "module": self.__class__.__module__,
            "methods": [method for method in dir(self) if not method.startswith('_') and callable(getattr(self, method))]
        })
    
    def post(self, request, notebook_id):
        return Response({
            "message": "Simple POST works", 
            "notebook_id": notebook_id,
            "view_class": self.__class__.__name__,
            "module": self.__class__.__module__,
            "request_method": request.method,
            "allowed_methods": getattr(self, 'http_method_names', 'not_set')
        })


# Keep the old name for backward compatibility
URLParseView = URLParseViewNew


class URLParseWithMediaView(StandardAPIView, NotebookPermissionMixin):
    """Handle URL parsing with media extraction - supports both single and batch processing."""
    
    parser_classes = [JSONParser]

    def post(self, request, notebook_id):
        """Parse URL media content using yt-dlp and faster-whisper - supports single URL or multiple URLs."""
        return Response({"message": "URLParseWithMediaView POST working", "notebook_id": notebook_id})


class URLParseDocumentView(StandardAPIView, NotebookPermissionMixin):
    """Handle document URL parsing - for PDFs and other document types."""
    
    parser_classes = [JSONParser]

    def post(self, request, notebook_id):
        """Parse document URL content."""
        return Response({"message": "URLParseDocumentView POST working", "notebook_id": notebook_id})