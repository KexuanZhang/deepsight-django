"""
API v1 ViewSets for notebooks app.

Provides comprehensive API endpoints following DRF best practices
with proper permissions, filtering, and pagination.
"""

import logging
import json
from typing import Any
from uuid import uuid4

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, filters, authentication
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from ...models import KnowledgeBaseItem, BatchJob, Notebook
from ...serializers import (
    FileUploadSerializer,
    BatchFileUploadSerializer,
    KnowledgeBaseItemSerializer,
    KnowledgeBaseImageSerializer,
    BatchJobSerializer,
    URLParseSerializer,
    URLParseWithMediaSerializer,
    URLParseDocumentSerializer,
    VideoImageExtractionSerializer,
    NotebookSerializer,
    NotebookListSerializer,
    NotebookCreateSerializer,
    NotebookUpdateSerializer
)
from ...services import FileService, ChatService, KnowledgeBaseService, NotebookService
from core.permissions import IsOwnerPermission
from core.pagination import StandardPageNumberPagination, LargePageNumberPagination, ChatMessagePagination, NotebookPagination

logger = logging.getLogger(__name__)


class NotebookViewSet(viewsets.ModelViewSet):
    """
    ViewSet for notebook operations with proper DRF patterns.
    
    Provides full CRUD operations:
    - list: GET /api/v1/notebooks/
    - create: POST /api/v1/notebooks/
    - retrieve: GET /api/v1/notebooks/{id}/
    - update: PUT /api/v1/notebooks/{id}/
    - partial_update: PATCH /api/v1/notebooks/{id}/
    - destroy: DELETE /api/v1/notebooks/{id}/
    
    Custom actions:
    - stats: GET /api/v1/notebooks/{id}/stats/
    - duplicate: POST /api/v1/notebooks/{id}/duplicate/
    """
    
    permission_classes = [permissions.IsAuthenticated, IsOwnerPermission]
    authentication_classes = [authentication.SessionAuthentication]
    pagination_class = NotebookPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['created_at']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-updated_at']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.notebook_service = NotebookService()
    
    def get_queryset(self):
        """
        Get queryset with optimized queries and user filtering.
        
        Uses select_related and prefetch_related for optimal database performance.
        """
        # Handle schema generation when user is not authenticated
        if getattr(self, 'swagger_fake_view', False) or not self.request.user.is_authenticated:
            return Notebook.objects.none()
            
        return Notebook.objects.filter(
            user=self.request.user
        ).select_related(
            'user'
        ).prefetch_related(
            'knowledge_base_items',
            'chat_messages',
            'batch_jobs'
        ).order_by('-updated_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action."""
        if self.action == 'list':
            return NotebookListSerializer
        elif self.action == 'create':
            return NotebookCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return NotebookUpdateSerializer
        return NotebookSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new notebook using the service layer."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            notebook = self.notebook_service.create_notebook(
                user=request.user,
                name=serializer.validated_data['name'],
                description=serializer.validated_data.get('description', '')
            )
            
            response_serializer = NotebookSerializer(notebook)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.exception(f"Failed to create notebook: {e}")
            return Response(
                {"error": "Failed to create notebook", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """Update notebook using the service layer."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            updated_notebook = self.notebook_service.update_notebook(
                notebook_id=str(instance.id),
                user=request.user,
                **serializer.validated_data
            )
            
            response_serializer = NotebookSerializer(updated_notebook)
            return Response(response_serializer.data)
            
        except Exception as e:
            logger.exception(f"Failed to update notebook {instance.id}: {e}")
            return Response(
                {"error": "Failed to update notebook", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """Delete notebook using the service layer."""
        instance = self.get_object()
        
        try:
            self.notebook_service.delete_notebook(
                notebook_id=str(instance.id),
                user=request.user
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.exception(f"Failed to delete notebook {instance.id}: {e}")
            return Response(
                {"error": "Failed to delete notebook", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Get notebook statistics.
        
        GET /api/v1/notebooks/{id}/stats/
        """
        notebook = self.get_object()
        
        try:
            stats = self.notebook_service.get_notebook_stats(
                notebook_id=str(notebook.id),
                user=request.user
            )
            return Response(stats)
            
        except Exception as e:
            logger.exception(f"Failed to get notebook stats: {e}")
            return Response(
                {"error": "Failed to retrieve notebook statistics", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplicate a notebook.
        
        POST /api/v1/notebooks/{id}/duplicate/
        """
        source_notebook = self.get_object()
        
        try:
            duplicated_notebook = self.notebook_service.duplicate_notebook(
                source_notebook_id=str(source_notebook.id),
                user=request.user,
                new_name=request.data.get('name', f"{source_notebook.name} (Copy)")
            )
            
            response_serializer = NotebookSerializer(duplicated_notebook)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.exception(f"Failed to duplicate notebook {source_notebook.id}: {e}")
            return Response(
                {"error": "Failed to duplicate notebook", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class FileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for file operations within notebooks.
    
    Provides endpoints:
    - GET /api/v1/notebooks/{notebook_id}/files/ - List files
    - POST /api/v1/notebooks/{notebook_id}/files/ - Upload file
    - GET /api/v1/notebooks/{notebook_id}/files/{id}/ - Get file details
    - DELETE /api/v1/notebooks/{notebook_id}/files/{id}/ - Delete file
    """
    
    serializer_class = KnowledgeBaseItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerPermission]
    pagination_class = LargePageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['processing_status', 'content_type']
    search_fields = ['title', 'notes']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-created_at']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_service = FileService()
    
    def get_queryset(self):
        """Get files for the specified notebook."""
        notebook_id = self.kwargs.get('notebook_pk')
        if notebook_id:
            try:
                # Get notebook and validate access
                from ...models import Notebook
                notebook = Notebook.objects.get(id=notebook_id, user=self.request.user)
                return KnowledgeBaseItem.objects.filter(notebook=notebook).select_related('notebook')
            except Notebook.DoesNotExist:
                logger.warning(f"Notebook {notebook_id} not found for user {self.request.user.id}")
                return KnowledgeBaseItem.objects.none()
            except Exception as e:
                logger.exception(f"Error getting queryset for notebook {notebook_id}: {e}")
                return KnowledgeBaseItem.objects.none()
        return KnowledgeBaseItem.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Upload a file to the notebook."""
        notebook_id = kwargs.get('notebook_pk')
        if not notebook_id:
            return Response(
                {"error": "notebook_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get notebook and validate access
        from ...models import Notebook
        try:
            notebook = Notebook.objects.get(id=notebook_id, user=request.user)
        except Notebook.DoesNotExist:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            try:
                file_obj, upload_id = self.file_service.validate_file_upload(serializer)
                result = self.file_service.handle_single_file_upload(
                    file_obj=file_obj,
                    upload_id=upload_id,
                    notebook=notebook,
                    user=request.user
                )
                
                return Response(result, status=result.get('status_code', status.HTTP_201_CREATED))
                
            except Exception as e:
                logger.exception(f"File upload failed: {e}")
                return Response(
                    {"error": "File upload failed", "details": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def batch_upload(self, request, notebook_pk=None):
        """
        Upload multiple files to the notebook.
        
        POST /api/v1/notebooks/{notebook_id}/files/batch_upload/
        """
        from ...models import Notebook
        
        try:
            notebook = Notebook.objects.get(id=notebook_pk, user=request.user)
        except Notebook.DoesNotExist:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        from ...serializers import BatchFileUploadSerializer
        serializer = BatchFileUploadSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                files = self.file_service.validate_batch_file_upload(serializer)
                if files:
                    result = self.file_service.handle_batch_file_upload(
                        files=files,
                        notebook=notebook,
                        user=request.user
                    )
                    return Response(result, status=result.get('status_code', status.HTTP_202_ACCEPTED))
                else:
                    return Response(
                        {"error": "No files provided"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
            except Exception as e:
                logger.exception(f"Batch file upload failed: {e}")
                return Response(
                    {"error": "Batch file upload failed", "details": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def content(self, request, notebook_pk=None, pk=None):
        """
        Get file content (processed content).
        
        GET /api/v1/notebooks/{notebook_id}/files/{id}/content/
        """
        file_item = self.get_object()
        
        try:
            # Use service to get processed content
            knowledge_service = KnowledgeBaseService()
            content_result = knowledge_service.get_file_content(
                file_id=str(file_item.id),
                user=request.user
            )
            
            if 'error' in content_result:
                return Response(content_result, status=content_result.get('status_code', status.HTTP_500_INTERNAL_SERVER_ERROR))
            
            return Response(content_result)
            
        except Exception as e:
            logger.exception(f"Failed to get file content: {e}")
            return Response(
                {"error": "Failed to retrieve file content", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def images(self, request, notebook_pk=None, pk=None):
        """
        Get all images for a file.
        
        GET /api/v1/notebooks/{notebook_id}/files/{id}/images/
        """
        file_item = self.get_object()
        
        try:
            knowledge_service = KnowledgeBaseService()
            notebook = get_object_or_404(Notebook, id=notebook_pk, user=request.user)
            
            images_result = knowledge_service.get_knowledge_base_images(
                file_id=str(file_item.id),
                notebook=notebook
            )
            
            if 'error' in images_result:
                return Response(images_result, status=images_result.get('status_code', status.HTTP_500_INTERNAL_SERVER_ERROR))
            
            return Response(images_result)
            
        except Exception as e:
            logger.exception(f"Failed to get file images: {e}")
            return Response(
                {"error": "Failed to retrieve file images", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def raw(self, request, notebook_pk=None, pk=None):
        """
        Get raw file content (original uploaded file).
        
        GET /api/v1/notebooks/{notebook_id}/files/{id}/raw/
        """
        file_item = self.get_object()
        
        try:
            # Use service to get raw file
            knowledge_service = KnowledgeBaseService()
            from django.http import FileResponse, Http404
            import os
            
            if not file_item.raw_file:
                return Response(
                    {"error": "Raw file not available"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get the file path
            file_path = file_item.raw_file.path if hasattr(file_item.raw_file, 'path') else None
            
            if file_path and os.path.exists(file_path):
                response = FileResponse(
                    open(file_path, 'rb'),
                    content_type='application/octet-stream'
                )
                response['Content-Disposition'] = f'attachment; filename="{file_item.title}"'
                return response
            else:
                return Response(
                    {"error": "Raw file not found on storage"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.exception(f"Failed to get raw file: {e}")
            return Response(
                {"error": "Failed to retrieve raw file", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def batch_upload(self, request, notebook_pk=None):
        """
        Upload multiple files to the notebook.
        
        POST /api/v1/notebooks/{notebook_id}/files/batch_upload/
        """
        from ...models import Notebook
        
        try:
            notebook = Notebook.objects.get(id=notebook_pk, user=request.user)
        except Notebook.DoesNotExist:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        from ...serializers import BatchFileUploadSerializer
        serializer = BatchFileUploadSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                files = self.file_service.validate_batch_file_upload(serializer)
                if files:
                    result = self.file_service.handle_batch_file_upload(
                        files=files,
                        notebook=notebook,
                        user=request.user
                    )
                    return Response(result, status=result.get('status_code', status.HTTP_202_ACCEPTED))
                else:
                    return Response(
                        {"error": "No files provided"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
            except Exception as e:
                logger.exception(f"Batch file upload failed: {e}")
                return Response(
                    {"error": "Batch file upload failed", "details": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def parse_url_with_media(self, request, notebook_pk=None):
        """
        Parse URL content with media extraction.
        
        POST /api/v1/notebooks/{notebook_id}/files/parse_url_with_media/
        """
        notebook = get_object_or_404(Notebook, id=notebook_pk, user=request.user)
        
        from ...serializers import URLParseWithMediaSerializer
        serializer = URLParseWithMediaSerializer(data=request.data)
        if serializer.is_valid():
            try:
                from ...services import URLService
                url_service = URLService()
                
                url, upload_url_id = url_service.validate_url_request(serializer)
                result = url_service.handle_url_with_media(
                    url=url,
                    upload_url_id=upload_url_id,
                    notebook=notebook,
                    user=request.user
                )
                
                return Response(result, status=result.get('status_code', status.HTTP_201_CREATED))
                
            except Exception as e:
                logger.exception(f"URL parsing with media failed: {e}")
                return Response(
                    {"error": "URL parsing with media failed", "details": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def parse_document_url(self, request, notebook_pk=None):
        """
        Parse document URL content.
        
        POST /api/v1/notebooks/{notebook_id}/files/parse_document_url/
        """
        notebook = get_object_or_404(Notebook, id=notebook_pk, user=request.user)
        
        from ...serializers import URLParseDocumentSerializer
        serializer = URLParseDocumentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                from ...services import URLService
                url_service = URLService()
                
                url, upload_url_id = url_service.validate_url_request(serializer)
                result = url_service.handle_document_url(
                    url=url,
                    upload_url_id=upload_url_id,
                    notebook=notebook,
                    user=request.user
                )
                
                return Response(result, status=result.get('status_code', status.HTTP_201_CREATED))
                
            except Exception as e:
                logger.exception(f"Document URL parsing failed: {e}")
                return Response(
                    {"error": "Document URL parsing failed", "details": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def extract_video_images(self, request, notebook_pk=None):
        """
        Extract images from video files.
        
        POST /api/v1/notebooks/{notebook_id}/files/extract_video_images/
        """
        notebook = get_object_or_404(Notebook, id=notebook_pk, user=request.user)
        
        from ...serializers import VideoImageExtractionSerializer
        serializer = VideoImageExtractionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Implementation would go here
                return Response(
                    {"message": "Video image extraction started"},
                    status=status.HTTP_202_ACCEPTED
                )
                
            except Exception as e:
                logger.exception(f"Video image extraction failed: {e}")
                return Response(
                    {"error": "Video image extraction failed", "details": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def parse_url(self, request, notebook_pk=None):
        """
        Parse URL content without media extraction.
        
        POST /api/v1/notebooks/{notebook_id}/files/parse_url/
        """
        notebook = get_object_or_404(Notebook, id=notebook_pk, user=request.user)
        
        serializer = URLParseSerializer(data=request.data)
        if serializer.is_valid():
            try:
                from ...services import URLService
                url_service = URLService()
                
                url, upload_url_id = url_service.validate_url_request(serializer)
                result = url_service.handle_single_url_parse(
                    url=url,
                    upload_url_id=upload_url_id,
                    notebook=notebook,
                    user=request.user
                )
                
                return Response(result, status=result.get('status_code', status.HTTP_201_CREATED))
                
            except Exception as e:
                logger.exception(f"URL parsing failed: {e}")
                return Response(
                    {"error": "URL parsing failed", "details": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def status(self, request, notebook_pk=None, pk=None):
        """
        Get file processing status.
        
        GET /api/v1/notebooks/{notebook_id}/files/{id}/status/
        """
        file_item = self.get_object()
        
        try:
            return Response({
                "id": str(file_item.id),
                "status": file_item.processing_status,
                "title": file_item.title,
                "content_type": file_item.content_type,
                "created_at": file_item.created_at,
                "updated_at": file_item.updated_at,
                "has_content": bool(file_item.content),
                "metadata": file_item.metadata or {}
            })
            
        except Exception as e:
            logger.exception(f"Failed to get file status: {e}")
            return Response(
                {"error": "Failed to retrieve file status", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='status/stream')
    def status_stream(self, request, notebook_pk=None, pk=None):
        """
        Get streaming file processing status updates.
        
        GET /api/v1/notebooks/{notebook_id}/files/{id}/status/stream/
        """
        from django.http import StreamingHttpResponse
        import json
        import time
        
        def generate_status_stream():
            try:
                file_item = self.get_object()
                
                # Keep streaming status until processing is complete
                for _ in range(60):  # Max 60 iterations (5 minutes)
                    file_item.refresh_from_db()
                    
                    status_data = {
                        "id": str(file_item.id),
                        "status": file_item.processing_status,
                        "title": file_item.title,
                        "content_type": file_item.content_type,
                        "created_at": file_item.created_at.isoformat(),
                        "updated_at": file_item.updated_at.isoformat(),
                        "has_content": bool(file_item.content),
                        "metadata": file_item.metadata or {}
                    }
                    
                    yield f"data: {json.dumps(status_data)}\n\n"
                    
                    # Stop streaming if processing is complete or failed
                    if file_item.processing_status in ['completed', 'failed', 'error']:
                        break
                        
                    time.sleep(5)  # Wait 5 seconds between updates
                    
            except Exception as e:
                error_data = {"error": "Failed to stream status", "details": str(e)}
                yield f"data: {json.dumps(error_data)}\n\n"
        
        try:
            response = StreamingHttpResponse(
                generate_status_stream(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['Connection'] = 'keep-alive'
            return response
            
        except Exception as e:
            logger.exception(f"Failed to create status stream: {e}")
            return Response(
                {"error": "Failed to create status stream", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatViewSet(viewsets.ViewSet):
    """
    ViewSet for chat operations within notebooks.
    
    Provides endpoints:
    - GET /api/v1/notebooks/{notebook_id}/chat/ - Get chat history
    - POST /api/v1/notebooks/{notebook_id}/chat/ - Send message
    - DELETE /api/v1/notebooks/{notebook_id}/chat/ - Clear history
    """
    
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ChatMessagePagination
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_service = ChatService()
    
    def list(self, request, notebook_pk=None):
        """Get chat history for the notebook."""
        from ...models import Notebook
        
        try:
            notebook = Notebook.objects.get(id=notebook_pk, user=request.user)
        except Notebook.DoesNotExist:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            history = self.chat_service.get_formatted_chat_history(notebook)
            return Response({"messages": history})
            
        except Exception as e:
            logger.exception(f"Failed to get chat history: {e}")
            return Response(
                {"error": "Failed to retrieve chat history", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request, notebook_pk=None):
        """Send a chat message."""
        from ...models import Notebook
        
        try:
            notebook = Notebook.objects.get(id=notebook_pk, user=request.user)
        except Notebook.DoesNotExist:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        question = request.data.get('question')
        file_ids = request.data.get('file_ids', [])
        
        # Validate request
        validation_error = self.chat_service.validate_chat_request(question, file_ids)
        if validation_error:
            return Response(validation_error, status=validation_error.get('status_code', status.HTTP_400_BAD_REQUEST))
        
        # Check knowledge base
        kb_error = self.chat_service.check_user_knowledge_base(request.user.id)
        if kb_error:
            return Response(kb_error, status=kb_error.get('status_code', status.HTTP_400_BAD_REQUEST))
        
        try:
            # Record user message
            self.chat_service.record_user_message(notebook, question)
            
            # Get chat history for context
            history = self.chat_service.get_chat_history(notebook)
            
            # Create streaming response
            from django.http import StreamingHttpResponse
            import json
            
            def generate_response():
                stream = self.chat_service.create_chat_stream(
                    user_id=request.user.id,
                    question=question,
                    history=history,
                    file_ids=file_ids,
                    notebook=notebook
                )
                
                for chunk in stream:
                    yield chunk
            
            response = StreamingHttpResponse(
                generate_response(),
                content_type='text/plain'
            )
            response['Cache-Control'] = 'no-cache'
            return response
            
        except Exception as e:
            logger.exception(f"Chat request failed: {e}")
            return Response(
                {"error": "Chat request failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, notebook_pk=None):
        """Clear chat history for the notebook."""
        from ...models import Notebook
        
        try:
            notebook = Notebook.objects.get(id=notebook_pk, user=request.user)
        except Notebook.DoesNotExist:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            success = self.chat_service.clear_chat_history(notebook)
            if success:
                return Response(
                    {"message": "Chat history cleared successfully"},
                    status=status.HTTP_204_NO_CONTENT
                )
            else:
                return Response(
                    {"error": "Failed to clear chat history"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.exception(f"Failed to clear chat history: {e}")
            return Response(
                {"error": "Failed to clear chat history", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def suggested_questions(self, request, notebook_pk=None):
        """
        Generate suggested questions based on chat history.
        
        GET /api/v1/notebooks/{notebook_id}/chat/suggested_questions/
        """
        notebook = get_object_or_404(Notebook, id=notebook_pk, user=request.user)
        
        try:
            result = self.chat_service.generate_suggested_questions(notebook)
            
            if 'error' in result:
                return Response(result, status=result.get('status_code', status.HTTP_500_INTERNAL_SERVER_ERROR))
            
            return Response(result)
            
        except Exception as e:
            logger.exception(f"Failed to generate suggested questions: {e}")
            return Response(
                {"error": "Failed to generate suggested questions", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class KnowledgeBaseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for knowledge base operations within notebooks.
    
    Provides read-only endpoints for browsing processed knowledge items.
    """
    
    serializer_class = KnowledgeBaseItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerPermission]
    pagination_class = LargePageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['processing_status', 'content_type']
    search_fields = ['title', 'notes']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-created_at']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.knowledge_service = KnowledgeBaseService()
    
    def get_queryset(self):
        """Get knowledge items for the specified notebook."""
        notebook_id = self.kwargs.get('notebook_pk')
        if notebook_id:
            from ...models import Notebook
            notebook = Notebook.objects.get(id=notebook_id, user=self.request.user)
            return KnowledgeBaseItem.objects.filter(
                notebook=notebook,
                processing_status='completed'
            ).select_related('notebook')
        return KnowledgeBaseItem.objects.none()


class BatchJobViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for batch job monitoring within notebooks.
    
    Provides read-only endpoints for monitoring batch processing jobs.
    """
    
    serializer_class = BatchJobSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerPermission]
    pagination_class = StandardPageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['job_type', 'status']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get batch jobs for the specified notebook."""
        notebook_id = self.kwargs.get('notebook_pk')
        if notebook_id:
            from ...models import Notebook
            notebook = Notebook.objects.get(id=notebook_id, user=self.request.user)
            return BatchJob.objects.filter(notebook=notebook).select_related('notebook')
        return BatchJob.objects.none()


class ChatHistoryView(APIView):
    """
    Compatibility endpoint for frontend that expects /chat-history/
    Redirects to the standard ChatViewSet.list() functionality
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, notebook_pk=None):
        """Get chat history for the notebook."""
        from ...models import Notebook
        
        try:
            notebook = Notebook.objects.get(id=notebook_pk, user=request.user)
        except Notebook.DoesNotExist:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            chat_service = ChatService()
            history = chat_service.get_formatted_chat_history(notebook)
            return Response({"messages": history})
            
        except Exception as e:
            logger.exception(f"Failed to get chat history: {e}")
            return Response(
                {"error": "Failed to retrieve chat history", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


