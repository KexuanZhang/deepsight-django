import os
import json
import time
import mimetypes
from uuid import uuid4

from .utils.rag_engine import RAGChatbot

from django.db import transaction
from django.http import StreamingHttpResponse, Http404, FileResponse
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework import status, permissions, authentication, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser

from .models import (
    Source, 
    URLProcessingResult, 
    KnowledgeItem, 
    KnowledgeBaseItem, 
    Notebook,
    NotebookChatMessage,
    )
from .serializers import NotebookSerializer, FileUploadSerializer
from .utils.upload_processor import UploadProcessor
from .utils.file_storage import FileStorageService
from .utils.view_mixins import (
    StandardAPIView,
    NotebookPermissionMixin,
    KnowledgeBasePermissionMixin,
    FileAccessValidatorMixin,
    PaginationMixin,
    FileListResponseMixin,
)


upload_processor = UploadProcessor()
file_storage = FileStorageService()

class FileUploadView(StandardAPIView, NotebookPermissionMixin):
    """Handle file uploads to notebooks."""
    
    parser_classes = [MultiPartParser]

    @transaction.atomic
    def post(self, request, notebook_id):
        """Handle file upload to notebook."""
        try:
            # Validate request data
            serializer = FileUploadSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error_response(
                    "Invalid request data", 
                    details=serializer.errors
                )
            
            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)
            
            # Extract file and upload ID
            inbound_file = serializer.validated_data["file"]
            upload_id = serializer.validated_data.get("upload_file_id") or uuid4().hex

            # Process the upload
            result = upload_processor.process_upload(
                inbound_file, 
                upload_id,
                user_pk=request.user.pk,
                notebook_id=notebook.id
            )

            # Create source record
            source = Source.objects.create(
                notebook=notebook,
                source_type="file",
                title=inbound_file.name,
                needs_processing=False,
                processing_status="done",
            )

            # Link to knowledge base
            kb_item_id = result['file_id']
            kb_item = get_object_or_404(KnowledgeBaseItem, id=kb_item_id, user=request.user)
            
            ki, created = KnowledgeItem.objects.get_or_create(
                notebook=notebook,
                knowledge_base_item=kb_item,
                defaults={
                    'source': source,
                    'notes': f"Processed from {inbound_file.name}"
                }
            )
            
            # Update source if needed
            if not created and not ki.source:
                ki.source = source
                ki.save(update_fields=['source'])

            return Response({
                "success": True,
                "file_id": kb_item_id,
                "knowledge_item_id": ki.id,
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return self.error_response(
                "File upload failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)}
            )
    
class FileListView(StandardAPIView, NotebookPermissionMixin, FileListResponseMixin):
    """List all knowledge items linked to a notebook."""

    def get(self, request, notebook_id):
        """Get all files linked to the notebook."""
        try:
            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)

            # Get all KnowledgeItems for this notebook with optimized query
            knowledge_items = KnowledgeItem.objects.filter(
                notebook=notebook
            ).select_related(
                'knowledge_base_item', 'source', 'source__url_result'
            ).order_by("-added_at")

            # Build response data using mixin
            files = [self.build_file_response_data(ki) for ki in knowledge_items]

            return self.success_response(files)
            
        except Exception as e:
            return self.error_response(
                "Failed to retrieve files",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)}
            )
        

class RAGChatFromKBView(StandardAPIView, NotebookPermissionMixin):
    def post(self, request):
        file_ids = request.data.get("file_ids", [])
        question = request.data.get("question")
        notebook_id = request.data.get("notebook_id")

        if not file_ids or not question or not notebook_id:
            return Response({"error": "file_ids, question, and notebook_id are required"}, status=400)

        try:
            notebook = Notebook.objects.get(id=notebook_id, user=request.user)
        except Notebook.DoesNotExist:
            return Response({"error": "Notebook not found or access denied"}, status=404)

        # Filter valid KB items
        kb_items = KnowledgeBaseItem.objects.filter(
            id__in=file_ids,
            user=request.user,
            file__isnull=False
        ).exclude(file="")

        if not kb_items.exists():
            return Response({"error": "No valid text files found"}, status=404)

        # Load file content
        docs = []
        for item in kb_items:
            if item.file and item.file.name:
                with item.file.open("rb") as f:
                    content = f.read().decode("utf-8")
                    docs.append({"content": content, "name": item.title})

        # Load previous chat history
        history = list(
            NotebookChatMessage.objects.filter(notebook=notebook)
            .order_by("timestamp")
            .values_list("sender", "message")
        )

        # Add new user message to DB
        NotebookChatMessage.objects.create(
            notebook=notebook,
            sender="user",
            message=question
        )

        # Run RAG with history
        bot = RAGChatbot(docs, chat_history=history)
        answer = bot.ask(question)

        # Save assistant reply
        NotebookChatMessage.objects.create(
            notebook=notebook,
            sender="assistant",
            message=answer
        )

        return Response({
            "answer": answer,
            "notebook_id": notebook_id,
            "history": history + [("user", question), ("assistant", answer)]
        })


class ChatHistoryView(StandardAPIView, NotebookPermissionMixin):

    def get(self, request, notebook_id):
        try:
            notebook = Notebook.objects.get(id=notebook_id, user=request.user)
        except Notebook.DoesNotExist:
            return Response({"error": "Notebook not found"}, status=404)

        messages = NotebookChatMessage.objects.filter(notebook=notebook).order_by("timestamp")
        history = [
            {
                "id": msg.id,
                "sender": msg.sender,
                "message": msg.message,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in messages
        ]

        return Response({"history": history})



class KnowledgeBaseView(StandardAPIView, NotebookPermissionMixin, PaginationMixin):
    """Manage user's knowledge base items."""
    
    parser_classes = [JSONParser, MultiPartParser]
    
    def get(self, request, notebook_id):
        """Get user's entire knowledge base with linkage status."""
        try:
            # Verify notebook ownership
            notebook = self.get_user_notebook(notebook_id, request.user)
            
            # Get query parameters
            content_type = request.GET.get('content_type')
            limit, offset = self.get_pagination_params(request)
            
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
            
            return self.success_response({
                "items": knowledge_base,
                "notebook_id": notebook_id,
                "pagination": {"limit": limit, "offset": offset}
            })
            
        except Exception as e:
            return self.error_response(
                "Failed to retrieve knowledge base",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)}
            )
    
    def post(self, request, notebook_id):
        """Link a knowledge base item to this notebook."""
        try:
            # Verify notebook ownership
            notebook = self.get_user_notebook(notebook_id, request.user)
            
            # Validate request data
            kb_item_id = request.data.get('knowledge_base_item_id')
            notes = request.data.get('notes', '')
            
            if not kb_item_id:
                return self.error_response("knowledge_base_item_id is required")
            
            # Link the item
            success = file_storage.link_knowledge_item_to_notebook(
                kb_item_id=kb_item_id,
                notebook_id=notebook_id,
                user_id=request.user.pk,
                notes=notes
            )
            
            if success:
                return self.success_response({"linked": True})
            else:
                return self.error_response("Failed to link knowledge item")
                
        except Exception as e:
            return self.error_response(
                "Link operation failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)}
            )
    
    def delete(self, request, notebook_id):
        """Delete a knowledge base item entirely from user's knowledge base."""
        try:
            # Verify notebook ownership (for permission check)
            self.get_user_notebook(notebook_id, request.user)
            
            # Validate request data
            kb_item_id = request.data.get('knowledge_base_item_id')
            if not kb_item_id:
                return self.error_response("knowledge_base_item_id is required")
            
            # Delete the knowledge base item entirely
            success = file_storage.delete_knowledge_base_item(
                kb_item_id, request.user.pk
            )
            
            if success:
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return self.error_response(
                    "Knowledge base item not found or access denied",
                    status_code=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            return self.error_response(
                "Delete operation failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)}
            )


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


class ClearChatHistoryView(APIView, NotebookPermissionMixin):

    def delete(self, request, notebook_id):
        notebook = self.get_user_notebook(notebook_id, request.user)
        NotebookChatMessage.objects.filter(notebook=notebook).delete()
        return Response({"success": True, "message": "Chat history cleared."})

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


class FileContentView(StandardAPIView, KnowledgeBasePermissionMixin):
    """Serve parsed content from knowledge base items."""

    def get(self, request, file_id):
        """Get processed content for a knowledge base item."""
        try:
            # Get the knowledge base item (verifies ownership)
            kb_item = self.get_user_kb_item(file_id, request.user)
            
            # Get content from storage service
            content = file_storage.get_file_content(file_id, user_id=request.user.pk)
            
            if content is None:
                return self.error_response(
                    "Content not found or not accessible",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            return self.success_response({
                "content": content,
                "title": kb_item.title,
                "content_type": kb_item.content_type,
                "metadata": kb_item.metadata or {}
            })
            
        except Exception as e:
            return self.error_response(
                "Failed to retrieve content",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)}
            )


@method_decorator(csrf_exempt, name='dispatch')
class FileRawView(StandardAPIView, FileAccessValidatorMixin):
    """Serve raw file content (PDFs, videos, audio, etc.)."""

    def get(self, request, notebook_id, file_id):
        """Serve raw file through notebook context."""
        try:
            # Validate access through notebook
            notebook, kb_item, knowledge_item = self.validate_notebook_file_access(
                notebook_id, file_id, request.user
            )
            
            # Try to serve original file first
            if kb_item.original_file:
                return self._serve_file(kb_item.original_file, kb_item.title)
            
            # Fallback to processed file
            if kb_item.file:
                return self._serve_file(kb_item.file, kb_item.title)
            
            raise Http404("Raw file not found")
            
        except PermissionDenied as e:
            return self.error_response(
                str(e), 
                status_code=status.HTTP_403_FORBIDDEN
            )
        except Http404 as e:
            return self.error_response(
                str(e),
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return self.error_response(
                "File access failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)}
            )
    
    def _serve_file(self, file_field, title):
        """Helper to serve a file with proper headers."""
        content_type, _ = mimetypes.guess_type(file_field.name)
        if not content_type:
            content_type = 'application/octet-stream'
        
        response = FileResponse(
            file_field.open('rb'),
            content_type=content_type,
            as_attachment=False
        )
        response['Content-Disposition'] = f'inline; filename="{title}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        return response


@method_decorator(csrf_exempt, name='dispatch')
class FileRawSimpleView(StandardAPIView, KnowledgeBasePermissionMixin):
    """Serve raw file content without requiring notebook context."""

    def get(self, request, file_id):
        """Serve raw file directly by knowledge base item ID."""
        try:
            # Get the knowledge base item (verifies ownership)
            kb_item = self.get_user_kb_item(file_id, request.user)
            
            # Try to serve original file first
            if kb_item.original_file:
                return self._serve_file(kb_item.original_file, kb_item.title)
            
            # Fallback to processed file
            if kb_item.file:
                return self._serve_file(kb_item.file, kb_item.title)
            
            raise Http404("Raw file not found")
            
        except Http404 as e:
            return self.error_response(
                str(e),
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return self.error_response(
                "File access failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)}
            )
    
    def _serve_file(self, file_field, title):
        """Helper to serve a file with proper headers."""
        content_type, _ = mimetypes.guess_type(file_field.name)
        if not content_type:
            content_type = 'application/octet-stream'
        
        response = FileResponse(
            file_field.open('rb'),
            content_type=content_type,
            as_attachment=False
        )
        response['Content-Disposition'] = f'inline; filename="{title}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        return response
