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

from ..models import Source, KnowledgeItem, KnowledgeBaseItem, BatchJob, BatchJobItem
from ..serializers import (
    URLParseSerializer, URLParseWithMediaSerializer, URLParseDocumentSerializer,
    BatchURLParseSerializer, BatchURLParseWithMediaSerializer
)
from ..utils.view_mixins import StandardAPIView, NotebookPermissionMixin
from ..processors.url_extractor import URLExtractor
from rag.rag import add_user_files  # Add this import at the top

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
        from ..models import Source
        source = Source.objects.create(
            notebook=notebook,
            source_type="url",
            title=url,
        )


        # Link to knowledge base
        kb_item_id = result['file_id']
        kb_item = get_object_or_404(KnowledgeBaseItem, id=kb_item_id, user=user)
        
        ki, _ = KnowledgeItem.objects.get_or_create(
            notebook=notebook,
            knowledge_base_item=kb_item,
            defaults={
                'source': source,
                'notes': f"Processed from URL: {url}"
            }
        )

        # Ingest KB item content for retrieval (embedding)
        if result.get("file_id"):
            kb_item = KnowledgeBaseItem.objects.filter(id=result["file_id"], user=user).first()
            if kb_item and kb_item.content:  # Ensure content exists
                try:
                    add_user_files(user_id=user.pk, kb_items=[kb_item])
                except Exception as e:
                    logger.error(f"Error ingesting KB item {kb_item.id}: {e}")

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
        from ..tasks import process_url_task
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
            process_url_task.delay(
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
        try:
            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)
            
            # Try batch serializer first
            from ..serializers import BatchURLParseWithMediaSerializer, URLParseWithMediaSerializer
            batch_serializer = BatchURLParseWithMediaSerializer(data=request.data)
            if batch_serializer.is_valid():
                validated_data = batch_serializer.validated_data
                
                # Check if this is a batch request (multiple URLs)
                if 'urls' in validated_data:
                    return self._handle_batch_url_parse_with_media(validated_data, notebook, request.user)
                else:
                    # Single URL - convert to single URL format for backward compatibility
                    url = validated_data.get('url')
                    upload_url_id = validated_data.get('upload_url_id', uuid4().hex)
                    return self._handle_single_url_parse_with_media(url, upload_url_id, notebook, request.user)
            
            # Fallback to original serializer for backward compatibility
            serializer = URLParseWithMediaSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error_response(
                    "Invalid request data", 
                    details=serializer.errors
                )
            
            # Handle single URL with original logic
            url = serializer.validated_data["url"]
            upload_url_id = serializer.validated_data.get("upload_url_id") or uuid4().hex
            return self._handle_single_url_parse_with_media(url, upload_url_id, notebook, request.user)

        except Exception as e:
            return self.error_response(
                "URL parsing failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )
    
    def _handle_single_url_parse_with_media(self, url, upload_url_id, notebook, user):
        """Handle single URL parsing with media extraction."""
        from asgiref.sync import async_to_sync
        
        # Process the URL using async function with media extraction
        async def process_url_with_media_async():
            return await url_extractor.process_url_with_media(
                url=url,
                upload_url_id=upload_url_id,
                user_id=user.pk,
                notebook_id=notebook.id
            )

        # Run async processing using async_to_sync
        result = async_to_sync(process_url_with_media_async)()

        # Create source record
        from ..models import Source
        source = Source.objects.create(
            notebook=notebook,
            source_type="url",
            title=url,
        )


        # Link to knowledge base
        kb_item_id = result['file_id']
        kb_item = get_object_or_404(KnowledgeBaseItem, id=kb_item_id, user=user)
        
        ki, _ = KnowledgeItem.objects.get_or_create(
            notebook=notebook,
            knowledge_base_item=kb_item,
            defaults={
                'source': source,
                'notes': f"Processed from URL with media: {url}"
            }
        )

        # Ingest KB item content for retrieval (embedding)
        if result.get("file_id"):
            kb_item = KnowledgeBaseItem.objects.filter(id=result["file_id"], user=user).first()
            if kb_item and kb_item.content:  # Ensure content exists
                try:
                    add_user_files(user_id=user.pk, kb_items=[kb_item])
                except Exception as e:
                    logger.error(f"Error ingesting KB item {kb_item.id}: {e}")

        return Response(
            {
                "success": True,
                "file_id": kb_item_id,
                "knowledge_item_id": ki.id,
                "url": result.get("url", url),
                "title": result.get("title", ""),
                "extraction_method": result.get("extraction_method", "yt-dlp"),
                "content_preview": result.get("content_preview", ""),
                "media_info": result.get("media_info", {}),
            },
            status=status.HTTP_201_CREATED,
        )
    
    def _handle_batch_url_parse_with_media(self, validated_data, notebook, user):
        """Handle batch URL parsing with media extraction."""
        from ..tasks import process_url_media_task
        from ..models import BatchJob, BatchJobItem
        
        urls = validated_data.get('urls', [])
        batch_job_id = validated_data.get('batch_job_id') or uuid4().hex
        
        # Create batch job
        batch_job = BatchJob.objects.create(
            id=batch_job_id,
            notebook=notebook,
            job_type='url_parse_with_media',
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
            process_url_media_task.delay(
                url=url,
                upload_url_id=upload_url_id,
                notebook_id=notebook.id,
                user_id=user.id,
                batch_job_id=batch_job_id,
                batch_item_id=batch_item.id
            )
        
        return self.success_response(
            "Batch URL processing with media started",
            data={
                "batch_job_id": batch_job_id,
                "total_urls": len(urls),
                "status": "processing"
            },
            status_code=status.HTTP_202_ACCEPTED
        )


class URLParseDocumentView(StandardAPIView, NotebookPermissionMixin):
    """Parse document URLs and validate file format (PDF/PPTX only)."""

    parser_classes = [JSONParser]

    def post(self, request, notebook_id):
        """Parse a document URL and validate its format."""
        try:
            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)
            
            # Validate input
            serializer = URLParseDocumentSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error_response(
                    "Invalid input data",
                    details=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            url = validated_data['url']
            upload_url_id = validated_data.get('upload_url_id')
            
            # Process document URL asynchronously
            result = async_to_sync(url_extractor.process_url_document_only)(
                url=url,
                upload_url_id=upload_url_id,
                user_id=request.user.pk,
                notebook_id=notebook.id
            )
            
            return Response({
                'success': True,
                'file_id': result['file_id'],
                'url': result['url'],
                'status': result['status'],
                'title': result['title'],
                'processing_type': result['processing_type'],
                'file_extension': result['file_extension'],
                'file_size': result['file_size'],
                'content_preview': result.get('content_preview', ''),
                'upload_url_id': upload_url_id
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            # File format validation errors - provide user-friendly messages
            error_msg = str(e)
            if "Invalid document format" in error_msg:
                if "text/html" in error_msg:
                    error_msg = "This URL points to a webpage, not a document file. Please use a direct link to a PDF or PowerPoint file instead."
                elif "Unknown" in error_msg:
                    error_msg = "This URL does not point to a valid PDF or PowerPoint file. Please check the URL and ensure it links directly to a document file."
                else:
                    error_msg = f"Invalid file format. The document URL processor only accepts PDF and PowerPoint files. {error_msg}"
            elif "Invalid URL" in error_msg:
                error_msg = "Please enter a valid URL that starts with http:// or https://"
            
            return self.error_response(
                error_msg,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Other processing errors (download failures, etc.)
            import traceback
            logger.error(f"Document URL processing failed for {validated_data.get('url', 'unknown URL')}: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Provide user-friendly error messages for common issues
            error_msg = str(e)
            if "Failed to download document" in error_msg:
                if "HTTP 404" in error_msg:
                    error_msg = "Document not found at this URL. Please check the URL and try again."
                elif "HTTP 403" in error_msg:
                    error_msg = "Access denied. The document may require authentication or may not be publicly accessible."
                else:
                    error_msg = "Unable to download the document from this URL. Please check if the URL is accessible and try again."
            elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                error_msg = "Network connection issue. Please check your internet connection and try again."
            elif "You cannot call this from an async context" in error_msg:
                error_msg = "Internal server error. Please try again in a moment."
            else:
                error_msg = f"Failed to process document URL: {error_msg}"
            
            return self.error_response(
                error_msg,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )