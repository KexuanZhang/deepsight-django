"""
URL Views - Handle URL processing operations only
"""
import logging
from uuid import uuid4

from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import BatchJob, BatchJobItem
from ..serializers import (
    URLParseSerializer, URLParseWithMediaSerializer, URLParseDocumentSerializer,
    BatchURLParseSerializer, BatchURLParseWithMediaSerializer
)
from ..utils.view_mixins import StandardAPIView, NotebookPermissionMixin

logger = logging.getLogger(__name__)


class URLParseView(StandardAPIView, NotebookPermissionMixin):
    """Handle URL parsing without media extraction - supports both single and batch processing."""
    
    parser_classes = [JSONParser]

    def post(self, request, notebook_id):
        """Parse URL content using crawl4ai only - supports single URL or multiple URLs."""
        try:
            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)
            
            # Try batch serializer first
            from ..serializers import BatchURLParseSerializer, URLParseSerializer
            batch_serializer = BatchURLParseSerializer(
                data=request.data, 
                context={'request': request, 'notebook_id': notebook_id}
            )
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
            serializer = URLParseSerializer(
                data=request.data, 
                context={'request': request, 'notebook_id': notebook_id}
            )
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
        """Handle single URL parsing using celery worker."""
        from ..tasks import process_url_task
        from ..models import KnowledgeBaseItem
        from ..utils.helpers import clean_title
        from uuid import uuid4
        
        # Step 1: Create KnowledgeBaseItem immediately so frontend can track it
        kb_item = KnowledgeBaseItem.objects.create(
            notebook=notebook,
            processing_status="processing",
            title=clean_title(url),
            content_type="webpage",
            notes=f"Processing URL: {url}",
            metadata={
                "source_url": url,
                "upload_url_id": upload_url_id or uuid4().hex,
                "processing_metadata": {
                    "extraction_type": "url_extractor",
                    "processing_type": "url_content"
                }
            }
        )
        
        # Step 2: Start async processing using celery task
        task_result = process_url_task.delay(
            url=url,
            notebook_id=str(notebook.id),  # Convert UUID to string for Celery serialization
            user_id=user.id,
            upload_url_id=upload_url_id,
            kb_item_id=str(kb_item.id)  # Pass the created KB item ID to the task
        )
        
        return Response(
            {
                "success": True,
                "task_id": task_result.id,
                "file_id": str(kb_item.id),  # Return the KB item ID for frontend tracking
                "url": url,
                "upload_url_id": upload_url_id,
                "status": "processing",
                "message": "URL processing started. Check task status for completion."
            },
            status=status.HTTP_202_ACCEPTED,
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
                notebook_id=str(notebook.id),  # Convert UUID to string for Celery serialization
                user_id=user.id,
                batch_job_id=batch_job_id,
                batch_item_id=str(batch_item.id)  # Convert UUID to string for Celery serialization
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
    
    def get(self, _request, notebook_id):
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
            batch_serializer = BatchURLParseWithMediaSerializer(
                data=request.data, 
                context={'request': request, 'notebook_id': notebook_id}
            )
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
            serializer = URLParseWithMediaSerializer(
                data=request.data, 
                context={'request': request, 'notebook_id': notebook_id}
            )
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
        """Handle single URL parsing with media extraction using celery worker."""
        from ..tasks import process_url_media_task
        
        # Start async processing using celery task
        task_result = process_url_media_task.delay(
            url=url,
            notebook_id=str(notebook.id),  # Convert UUID to string for Celery serialization
            user_id=user.id,
            upload_url_id=upload_url_id
        )
        
        return Response(
            {
                "success": True,
                "task_id": task_result.id,
                "url": url,
                "upload_url_id": upload_url_id,
                "status": "processing",
                "message": "URL media processing started. Check task status for completion."
            },
            status=status.HTTP_202_ACCEPTED,
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
                notebook_id=str(notebook.id),  # Convert UUID to string for Celery serialization
                user_id=user.id,
                batch_job_id=batch_job_id,
                batch_item_id=str(batch_item.id)  # Convert UUID to string for Celery serialization
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
            serializer = URLParseDocumentSerializer(
                data=request.data, 
                context={'request': request, 'notebook_id': notebook_id}
            )
            if not serializer.is_valid():
                return self.error_response(
                    "Invalid input data",
                    details=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            url = validated_data['url']
            upload_url_id = validated_data.get('upload_url_id')
            
            # Start async processing using celery task
            from ..tasks import process_url_document_task
            task_result = process_url_document_task.delay(
                url=url,
                notebook_id=str(notebook.id),  # Convert UUID to string for Celery serialization
                user_id=request.user.pk,
                upload_url_id=upload_url_id
            )
            
            return Response({
                'success': True,
                'task_id': task_result.id,
                'url': url,
                'upload_url_id': upload_url_id,
                'status': 'processing',
                'message': 'Document URL processing started. Check task status for completion.'
            }, status=status.HTTP_202_ACCEPTED)
            
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