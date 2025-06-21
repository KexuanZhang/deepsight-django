import os
import json
import asyncio
import time
from django.db import transaction
from django.core.files.base import ContentFile
from django.http import StreamingHttpResponse, HttpResponse, Http404, FileResponse
from rest_framework import status, permissions, authentication, generics 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from uuid import uuid4    
import mimetypes

from .models import Source, URLProcessingResult, KnowledgeItem, KnowledgeBaseItem, Notebook
from .serializers import (
    NotebookSerializer,
    FileUploadSerializer,
    # TextUploadSerializer,
    # URLUploadSerializer,
)
from .utils.upload_processor import UploadProcessor
from .utils.services.file_storage import FileStorageService

upload_processor = UploadProcessor()
file_storage     = FileStorageService()

class FileUploadView(APIView):
    permission_classes     = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]
    parser_classes         = [MultiPartParser]

    @transaction.atomic
    def post(self, request, notebook_id):
        """Handle /api/sources/upload/"""
        print(request.data)
        ser = FileUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        notebook = get_object_or_404(Notebook, pk=notebook_id, user=request.user)
        inbound_file = ser.validated_data["file"]
        upload_id    = ser.validated_data.get("upload_file_id") or uuid4().hex

        result = upload_processor.process_upload(
            inbound_file, 
            upload_id,
            user_pk=request.user.pk,
            notebook_id=notebook.id
        )

        source = Source.objects.create(
            notebook=notebook,
            source_type="file",
            title=inbound_file.name,
            needs_processing=False,
            processing_status="done",
        )

        # The upload processor now returns a knowledge base item ID
        kb_item_id = result['file_id']
        
        # Get or create the knowledge base item link
        try:
            kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, user=request.user)
            ki, created = KnowledgeItem.objects.get_or_create(
                notebook=notebook,
                knowledge_base_item=kb_item,
                defaults={
                    'source': source,
                    'notes': f"Processed from {inbound_file.name}"
                }
            )
            
            # If the KnowledgeItem already existed but didn't have a source, update it
            if not created and not ki.source:
                ki.source = source
                ki.save(update_fields=['source'])
        except KnowledgeBaseItem.DoesNotExist:
            return Response({
                "success": False,
                "error": "Failed to create knowledge base item"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "success": True,
            "file_id": kb_item_id,
            "knowledge_item_id": ki.id,
        }, status=status.HTTP_201_CREATED)
    
class FileListView(APIView):
    """
    GET /api/notebooks/{notebook_id}/files/
    Return the list of all knowledge items linked to this notebook.
    """
    permission_classes     = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def get(self, request, notebook_id):
        # Only include files for notebooks the user owns
        notebook = get_object_or_404(Notebook, id=notebook_id, user=request.user)

        # Get all KnowledgeItems for this notebook
        knowledge_items = KnowledgeItem.objects.filter(
            notebook=notebook
        ).select_related('knowledge_base_item', 'source').order_by("-added_at")

        files = []
        for ki in knowledge_items:
            kb_item = ki.knowledge_base_item
            source = ki.source
            
            file_data = {
                "file_id": str(kb_item.id),
                "knowledge_item_id": ki.id,
                "title": kb_item.title,
                "content_type": kb_item.content_type,
                "tags": kb_item.tags,
                "created_at": kb_item.created_at.isoformat(),
                "updated_at": kb_item.updated_at.isoformat(),
                "added_to_notebook_at": ki.added_at.isoformat(),
                "notes": ki.notes,
                "metadata": kb_item.metadata or {},
                "has_file": bool(kb_item.file),
                "has_content": bool(kb_item.content),
                "parsing_status": "completed",  # Knowledge base items are always processed
                
                # Legacy fields for compatibility - prioritize original file information from metadata
                "original_filename": self._get_original_filename_from_metadata(kb_item.metadata, kb_item.title),
                "file_extension": self._get_extension_from_metadata(kb_item.metadata),
                "file_size": self._get_file_size_from_metadata(kb_item.metadata),
                "uploaded_at": kb_item.created_at.isoformat(),
            }
            
            # Add source-specific information if available
            if source:
                file_data.update({
                    "source_id": source.id,
                    "source_type": source.source_type,
                    "source_title": source.title,
                    "source_status": source.processing_status,
                })
                
                # Legacy source file information - now handled by knowledge base
                if source.source_type == "file":
                    # File information now comes from knowledge base metadata
                    pass
                
                elif source.source_type == "url" and hasattr(source, 'url_result'):
                    url_result = source.url_result
                    file_data.update({
                        "source_url": source.title,
                        "content_length": len(url_result.content_md) if url_result.content_md else 0,
                        "processing_method": "web_scraping",
                        "extraction_type": "url_extractor",
                        "original_filename": f"{source.title}_processed.md",
                        "file_extension": ".md",
                    })
                    
                    if url_result.downloaded_file:
                        file_data["downloaded_file_path"] = url_result.downloaded_file.name
                        file_data["downloaded_file_url"] = url_result.downloaded_file.url
                
                elif source.source_type == "text":
                    # Text content now handled by knowledge base
                    file_data.update({
                        "original_filename": f"{source.title}.txt",
                        "file_extension": ".txt",
                    })
            
            # Add knowledge base file information
            if kb_item.file:
                file_data.update({
                    "knowledge_file_path": kb_item.file.name,
                    "knowledge_file_url": kb_item.file.url,
                })

            files.append(file_data)

        return Response({"success": True, "data": files})
    
    def _get_extension_from_metadata(self, metadata):
        """Extract file extension from metadata."""
        if not metadata:
            return ""
        
        # Try various sources for file extension
        extension = metadata.get('file_extension', '')
        if not extension and 'original_filename' in metadata and '.' in metadata['original_filename']:
            extension = '.' + metadata['original_filename'].split('.')[-1]
        elif not extension and 'filename' in metadata and '.' in metadata['filename']:
            extension = '.' + metadata['filename'].split('.')[-1]
        
        return extension
    
    def _get_original_filename_from_metadata(self, metadata, fallback_title):
        """Extract original filename from metadata, with fallback to title."""
        if not metadata:
            return fallback_title
        
        # Priority order for original filename
        original_filename = metadata.get('original_filename') or \
                           metadata.get('filename') or \
                           fallback_title
        
        # If we have a filename but no extension, and we can get extension from metadata, combine them
        if original_filename and not '.' in original_filename:
            extension = metadata.get('file_extension', '')
            if extension:
                if not extension.startswith('.'):
                    extension = '.' + extension
                original_filename = original_filename + extension
        
        return original_filename
    
    def _get_file_size_from_metadata(self, metadata):
        """Extract file size from metadata."""
        if not metadata:
            return None
        
        # Try various sources for file size
        return metadata.get('file_size') or \
               metadata.get('content_length') or \
               None


class KnowledgeBaseView(APIView):
    """
    GET /api/notebooks/{notebook_id}/knowledge-base/
    Get all knowledge base items for the user (not just this notebook).
    POST /api/notebooks/{notebook_id}/knowledge-base/link/
    Link an existing knowledge base item to this notebook.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]
    parser_classes = [JSONParser, MultiPartParser]
    
    def get(self, request, notebook_id):
        """Get user's entire knowledge base."""
        # Verify notebook ownership
        notebook = get_object_or_404(Notebook, id=notebook_id, user=request.user)
        
        content_type = request.GET.get('content_type')
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        # Get knowledge base items
        knowledge_base = file_storage.get_user_knowledge_base(
            user_id=request.user.pk,
            content_type=content_type,
            limit=limit,
            offset=offset
        )
        
        # Check which items are already linked to this notebook
        linked_kb_item_ids = set(
            KnowledgeItem.objects.filter(notebook=notebook)
            .values_list('knowledge_base_item_id', flat=True)
        )
        
        # Add linked status to each item
        for item in knowledge_base:
            item['linked_to_notebook'] = int(item['id']) in linked_kb_item_ids
        
        return Response({
            "success": True, 
            "data": knowledge_base,
            "notebook_id": notebook_id
        })
    
    def post(self, request, notebook_id):
        """Link a knowledge base item to this notebook."""
        notebook = get_object_or_404(Notebook, id=notebook_id, user=request.user)
        
        kb_item_id = request.data.get('knowledge_base_item_id')
        notes = request.data.get('notes', '')
        
        if not kb_item_id:
            return Response({
                "success": False,
                "error": "knowledge_base_item_id is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Link the item
        success = file_storage.link_knowledge_item_to_notebook(
            kb_item_id=kb_item_id,
            notebook_id=notebook_id,
            user_id=request.user.pk,
            notes=notes
        )
        
        if success:
            return Response({"success": True})
        else:
            return Response({
                "success": False,
                "error": "Failed to link knowledge item"
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, notebook_id):
        """Delete a knowledge base item entirely from user's knowledge base."""
        # Verify notebook ownership (for permission check)
        notebook = get_object_or_404(Notebook, id=notebook_id, user=request.user)
        
        kb_item_id = request.data.get('knowledge_base_item_id')
        
        if not kb_item_id:
            return Response({
                "success": False,
                "error": "knowledge_base_item_id is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Delete the knowledge base item entirely
        success = file_storage.delete_knowledge_base_item(
            kb_item_id, request.user.pk
        )
        
        if success:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({
                "detail": "Knowledge base item not found or access denied"
            }, status=status.HTTP_404_NOT_FOUND)


class FileStatusView(APIView):
    """
    GET /api/notebooks/{notebook_id}/files/{upload_file_id}/status/
    Return a one‐time snapshot of parsing status, or 404 if unknown.
    """
    permission_classes     = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def get(self, request, notebook_id, upload_file_id):
        # verify notebook ownership
        if not Notebook.objects.filter(id=notebook_id, user=request.user).exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        status_obj = upload_processor.get_upload_status(upload_file_id, request.user.pk)
        if not status_obj:
            return Response({"detail": "Status not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True, **status_obj})


class FileStatusStreamView(APIView):
    """
    GET /api/notebooks/{notebook_id}/files/{upload_file_id}/status/stream
    Server-Sent Events streaming endpoint for real-time upload status updates.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def get(self, request, notebook_id, upload_file_id):
        # Verify notebook ownership
        if not Notebook.objects.filter(id=notebook_id, user=request.user).exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        def event_stream():
            """Generator function for SSE events"""
            max_duration = 300  # 5 minutes maximum
            start_time = time.time()
            poll_interval = 2  # Check every 2 seconds
            
            while time.time() - start_time < max_duration:
                try:
                    # Get current status synchronously
                    status_obj = upload_processor.get_upload_status(upload_file_id, request.user.pk)
                    
                    if status_obj:
                        # Send status update as SSE event
                        event_data = {
                            'status': status_obj.get('status', 'unknown'),
                            'job_details': {
                                'progress_percentage': status_obj.get('progress_percentage', 0),
                                'result': status_obj.get('metadata', {}),
                                'error': status_obj.get('error')
                            }
                        }
                        
                        yield f"data: {json.dumps(event_data)}\n\n"
                        
                        # If upload is complete, send final event and close
                        if status_obj.get('status') in ['completed', 'error', 'cancelled', 'unsupported']:
                            break
                    else:
                        # No status found, might be completed or doesn't exist
                        yield f"data: {json.dumps({'status': 'not_found', 'job_details': {}})}\n\n"
                        break
                        
                except Exception as e:
                    # Send error event
                    error_data = {
                        'status': 'error',
                        'job_details': {'error': str(e)}
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                    break
                
                # Wait before next poll
                time.sleep(poll_interval)
            
            # Send final close event
            yield f"data: {json.dumps({'status': 'stream_closed', 'job_details': {}})}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['Connection'] = 'keep-alive'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Headers'] = 'Cache-Control'
        
        return response


class FileDeleteView(APIView):
    """
    DELETE /api/notebooks/{notebook_id}/files/{file_or_upload_id}/
    Delete a knowledge item link from notebook or delete from knowledge base entirely.
    """
    permission_classes     = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    @transaction.atomic
    def delete(self, request, notebook_id, file_or_upload_id):
        # verify notebook ownership
        notebook = get_object_or_404(Notebook, id=notebook_id, user=request.user)
        
        force_delete = request.GET.get('force', 'false').lower() == 'true'
        
        deleted = False
        
        # Strategy 1: Try to find by knowledge_item_id (direct database ID)
        if not deleted:
            try:
                knowledge_item_id = int(file_or_upload_id)
                ki = KnowledgeItem.objects.filter(
                    id=knowledge_item_id, 
                    notebook=notebook
                ).first()
                
                if ki:
                    if force_delete:
                        # Delete the knowledge base item entirely
                        success = file_storage.delete_knowledge_base_item(
                            str(ki.knowledge_base_item.id), request.user.pk
                        )
                        if success:
                            deleted = True
                    else:
                        # Just delete the link
                        ki.delete()
                        deleted = True
            except (ValueError, TypeError):
                pass  # Not a valid integer ID
        
        # Strategy 2: Try to find by knowledge_base_item_id (if it's a valid integer)
        if not deleted:
            try:
                kb_item_id = int(file_or_upload_id)
                # Try to find a KnowledgeItem in this notebook that links to this KB item
                ki = KnowledgeItem.objects.filter(
                    notebook=notebook,
                    knowledge_base_item_id=kb_item_id
                ).first()
                
                if ki:
                    if force_delete:
                        # Delete the knowledge base item entirely
                        success = file_storage.delete_knowledge_base_item(
                            str(kb_item_id), request.user.pk
                        )
                        if success:
                            deleted = True
                    else:
                        # Just unlink from this notebook
                        success = file_storage.unlink_knowledge_item_from_notebook(
                            str(kb_item_id), notebook_id, request.user.pk
                        )
                        if success:
                            deleted = True
            except (ValueError, TypeError):
                pass  # Not a valid integer ID
        
        # Strategy 3: Handle upload IDs by searching in metadata
        if not deleted and str(file_or_upload_id).startswith('upload_'):
            try:
                # Find knowledge items in this notebook that have the upload ID in metadata
                knowledge_items = KnowledgeItem.objects.filter(
                    notebook=notebook
                ).select_related('knowledge_base_item', 'source')
                
                for ki in knowledge_items:
                    kb_item = ki.knowledge_base_item
                    source = ki.source
                    
                    # Check if this knowledge item is related to the upload ID
                    upload_id_match = False
                    
                    # Check metadata for upload ID references
                    if kb_item.metadata and isinstance(kb_item.metadata, dict):
                        metadata_str = str(kb_item.metadata)
                        if file_or_upload_id in metadata_str:
                            upload_id_match = True
                    
                    # Check source metadata if available
                    if source and hasattr(source, 'upload') and source.upload:
                        # Check if source file contains the upload ID pattern
                        if file_or_upload_id in str(source.upload.file.name):
                            upload_id_match = True
                    
                    if upload_id_match:
                        if force_delete:
                            # Delete the knowledge base item entirely
                            success = file_storage.delete_knowledge_base_item(
                                str(kb_item.id), request.user.pk
                            )
                            if success:
                                deleted = True
                                break
                        else:
                            # Just delete the link
                            ki.delete()
                            deleted = True
                            break
                        
            except Exception as e:
                print(f"Error handling upload ID {file_or_upload_id}: {e}")
        
        # Strategy 4: Legacy fallback - try as string knowledge base item ID
        if not deleted:
            try:
                # Some systems might pass KB item IDs as strings
                ki = KnowledgeItem.objects.filter(
                    notebook=notebook,
                    knowledge_base_item_id=file_or_upload_id
                ).first()
                
                if ki:
                    if force_delete:
                        # Delete the knowledge base item entirely
                        success = file_storage.delete_knowledge_base_item(
                            str(ki.knowledge_base_item.id), request.user.pk
                        )
                        if success:
                            deleted = True
                    else:
                        # Just delete the link
                        ki.delete()
                        deleted = True
                        
            except Exception as e:
                print(f"Error in legacy fallback for {file_or_upload_id}: {e}")

        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"detail": "File not found."}, status=status.HTTP_404_NOT_FOUND)


class NotebookListCreateAPIView(generics.ListCreateAPIView):
    """
    GET  /api/notebooks/      → list all notebooks for request.user
    POST /api/notebooks/      → create a new notebook for request.user
    """
    
    serializer_class = NotebookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only the current user's notebooks
        print(self.request.user)
        return Notebook.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # Auto-assign the creating user
        print(self.request.user)
        serializer.save(user=self.request.user)


class NotebookRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/notebooks/{pk}/   → retrieve a notebook
    PUT    /api/notebooks/{pk}/   → update name & description
    PATCH  /api/notebooks/{pk}/   → partial update
    DELETE /api/notebooks/{pk}/   → delete the notebook
    """
    serializer_class    = NotebookSerializer
    permission_classes  = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def get_queryset(self):
        # Users can only operate on their own notebooks
        return Notebook.objects.filter(user=self.request.user)


class FileContentView(APIView):
    """
    GET /api/v1/files/{file_id}/content/
    Serve parsed content from knowledge base item
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def get(self, request, file_id):
        try:
            # TODO: Add rate limiting to prevent abuse
            # from django_ratelimit.decorators import ratelimit
            # @ratelimit(key='user', rate='100/h', method='GET')
            
            # Get the knowledge base item
            kb_item = get_object_or_404(KnowledgeBaseItem, id=file_id, user=request.user)
            
            # TODO: Log access attempts for security monitoring
            # logger.info(f"User {request.user.id} accessed file content {file_id}")
            
            # Get content from storage service
            content = file_storage.get_file_content(file_id, user_id=request.user.pk)
            
            if content is None:
                # TODO: Log failed access attempts
                # logger.warning(f"User {request.user.id} attempted to access unavailable content {file_id}")
                return Response({
                    "success": False,
                    "error": "Content not found or not accessible"
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                "success": True,
                "data": {
                    "content": content,
                    "title": kb_item.title,
                    "content_type": kb_item.content_type,
                    "metadata": kb_item.metadata or {}
                }
            })
            
        except Exception as e:
            # TODO: Log security exceptions
            # logger.error(f"Security exception in FileContentView: user={request.user.id}, file_id={file_id}, error={str(e)}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileRawView(APIView):
    """
    GET /api/v1/notebooks/{notebook_id}/files/{file_id}/raw/
    Serve raw file content (PDFs, videos, audio, etc.)
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def get(self, request, notebook_id, file_id):
        try:
            # TODO: Add rate limiting for file downloads
            # @ratelimit(key='user', rate='50/h', method='GET')
            
            # Verify notebook ownership
            notebook = get_object_or_404(Notebook, id=notebook_id, user=request.user)
            
            # Get the knowledge base item
            kb_item = get_object_or_404(KnowledgeBaseItem, id=file_id, user=request.user)
            
            # Check if user has access to this file through the notebook
            knowledge_item = KnowledgeItem.objects.filter(
                notebook=notebook,
                knowledge_base_item=kb_item
            ).first()
            
            if not knowledge_item:
                # TODO: Log unauthorized access attempts
                # logger.warning(f"User {request.user.id} attempted unauthorized access: notebook={notebook_id}, file={file_id}")
                raise PermissionDenied("File not linked to this notebook")
            
            # TODO: Log successful file access
            # logger.info(f"User {request.user.id} downloaded file {file_id} from notebook {notebook_id}")
            
            # FIRST: Try to serve original file from knowledge base (new original_file field)
            if kb_item.original_file:
                # Determine content type
                content_type, _ = mimetypes.guess_type(kb_item.original_file.name)
                if not content_type:
                    content_type = 'application/octet-stream'
                
                # Return file response
                response = FileResponse(
                    kb_item.original_file.open('rb'),
                    content_type=content_type,
                    as_attachment=False
                )
                response['Content-Disposition'] = f'inline; filename="{kb_item.title}"'
                # TODO: Add security headers
                # response['X-Content-Type-Options'] = 'nosniff'
                # response['X-Frame-Options'] = 'DENY'
                return response
            
            # SECOND: Try to serve original source file (legacy support)
            if knowledge_item.source:
                source = knowledge_item.source
                
                if source.source_type == "file" and hasattr(source, 'upload'):
                    upload = source.upload
                    if upload.file:
                        content_type, _ = mimetypes.guess_type(upload.file.name)
                        if not content_type:
                            content_type = 'application/octet-stream'
                        
                        response = FileResponse(
                            upload.file.open('rb'),
                            content_type=content_type,
                            as_attachment=False
                        )
                        response['Content-Disposition'] = f'inline; filename="{upload.original_name or kb_item.title}"'
                        return response
            
            # FALLBACK: Try to serve the processed file from knowledge base item
            # (This would be processed content like .md files, not ideal for raw access)
            if kb_item.file:
                # TODO: Add file size limits for security
                # if kb_item.file.size > settings.MAX_FILE_DOWNLOAD_SIZE:
                #     raise ValidationError("File too large to download")
                
                # Determine content type
                content_type, _ = mimetypes.guess_type(kb_item.file.name)
                if not content_type:
                    content_type = 'application/octet-stream'
                
                # Return file response
                response = FileResponse(
                    kb_item.file.open('rb'),
                    content_type=content_type,
                    as_attachment=False
                )
                response['Content-Disposition'] = f'inline; filename="{kb_item.title}"'
                # TODO: Add security headers
                # response['X-Content-Type-Options'] = 'nosniff'
                # response['X-Frame-Options'] = 'DENY'
                return response
            
            raise Http404("Raw file not found")
            
        except PermissionDenied:
            return Response({
                "error": "Permission denied"
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            # TODO: Log all security-related exceptions
            # logger.error(f"FileRawView exception: user={request.user.id}, notebook={notebook_id}, file={file_id}, error={str(e)}")
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileRawSimpleView(APIView):
    """
    GET /api/v1/files/{file_id}/raw/
    Serve raw file content (PDFs, videos, audio, etc.) without requiring notebook context
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def get(self, request, file_id):
        try:
            # TODO: Add rate limiting for file downloads
            # @ratelimit(key='user', rate='50/h', method='GET')
            
            # Get the knowledge base item - only files owned by the user
            kb_item = get_object_or_404(KnowledgeBaseItem, id=file_id, user=request.user)
            
            # TODO: Log successful file access
            # logger.info(f"User {request.user.id} downloaded raw file {file_id}")
            
            # FIRST: Try to serve original file from knowledge base (new original_file field)
            if kb_item.original_file:
                # Determine content type
                content_type, _ = mimetypes.guess_type(kb_item.original_file.name)
                if not content_type:
                    content_type = 'application/octet-stream'
                
                # Return file response
                response = FileResponse(
                    kb_item.original_file.open('rb'),
                    content_type=content_type,
                    as_attachment=False
                )
                response['Content-Disposition'] = f'inline; filename="{kb_item.title}"'
                # TODO: Add security headers
                # response['X-Content-Type-Options'] = 'nosniff'
                # response['X-Frame-Options'] = 'DENY'
                return response
            
            # SECOND: Try to find original source file (legacy support)
            # Look for any knowledge item that links to this kb_item for the user
            knowledge_items = KnowledgeItem.objects.filter(
                knowledge_base_item=kb_item,
                notebook__user=request.user
            )
            
            for knowledge_item in knowledge_items:
                if knowledge_item.source:
                    source = knowledge_item.source
                    
                    if source.source_type == "file" and hasattr(source, 'upload'):
                        upload = source.upload
                        if upload.file:
                            content_type, _ = mimetypes.guess_type(upload.file.name)
                            if not content_type:
                                content_type = 'application/octet-stream'
                            
                            response = FileResponse(
                                upload.file.open('rb'),
                                content_type=content_type,
                                as_attachment=False
                            )
                            response['Content-Disposition'] = f'inline; filename="{upload.original_name or kb_item.title}"'
                            return response
            
            # FALLBACK: If no original files found, try knowledge base processed file
            # (This would be processed content like .md files, not ideal for raw access)
            if kb_item.file:
                # TODO: Add file size limits for security
                # if kb_item.file.size > settings.MAX_FILE_DOWNLOAD_SIZE:
                #     raise ValidationError("File too large to download")
                
                # Determine content type
                content_type, _ = mimetypes.guess_type(kb_item.file.name)
                if not content_type:
                    content_type = 'application/octet-stream'
                
                # Return file response
                response = FileResponse(
                    kb_item.file.open('rb'),
                    content_type=content_type,
                    as_attachment=False
                )
                response['Content-Disposition'] = f'inline; filename="{kb_item.title}"'
                # TODO: Add security headers
                # response['X-Content-Type-Options'] = 'nosniff'
                # response['X-Frame-Options'] = 'DENY'
                return response
            
            raise Http404("Raw file not found")
            
        except Exception as e:
            # TODO: Log all security-related exceptions
            # logger.error(f"FileRawSimpleView exception: user={request.user.id}, file={file_id}, error={str(e)}")
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
