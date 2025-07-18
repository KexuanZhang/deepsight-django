"""
File Views - Handle file upload and management operations only
"""
import logging
import traceback
from uuid import uuid4

from asgiref.sync import async_to_sync
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions, authentication
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response

from ..models import Source, KnowledgeItem, KnowledgeBaseItem, BatchJob, BatchJobItem
from ..serializers import FileUploadSerializer, BatchFileUploadSerializer
from ..utils.view_mixins import (
    StandardAPIView, NotebookPermissionMixin, KnowledgeBasePermissionMixin,
    FileAccessValidatorMixin, PaginationMixin, FileListResponseMixin
)
from ..processors.upload_processor import UploadProcessor
from ..tasks import process_file_upload_task
from rag.rag import add_user_files
from ..services import FileService

logger = logging.getLogger(__name__)

# Initialize processors
upload_processor = UploadProcessor()


class FileUploadView(NotebookPermissionMixin, APIView):
    """Handle file uploads to notebooks - supports both single and batch uploads."""
    parser_classes = [MultiPartParser]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_service = FileService()

    def post(self, request, notebook_id):
        try:
            notebook = self.get_user_notebook(notebook_id, request.user)

            # Try batch upload first
            batch_serializer = BatchFileUploadSerializer(data=request.data)
            if batch_serializer.is_valid():
                files = self.file_service.validate_batch_file_upload(batch_serializer)
                if files:
                    result = self.file_service.handle_batch_file_upload(files, notebook, request.user)
                    return Response(result, status=result['status_code'])

            # Handle single file upload
            serializer = FileUploadSerializer(data=request.data)
            file_obj, upload_id = self.file_service.validate_file_upload(serializer)
            
            result = self.file_service.handle_single_file_upload(file_obj, upload_id, notebook, request.user)
            return Response(result, status=result['status_code'])

        except ValidationError as e:
            return self.error_response(
                "File validation failed",
                status_code=status.HTTP_400_BAD_REQUEST,
                details={"error": str(e)},
            )
        except Exception as e:
            logger.exception(
                "Unhandled exception in FileUploadView POST for notebook %s: %s",
                notebook_id, e
            )
            logger.error("Traceback:\n%s", traceback.format_exc())

            return Response(
                {
                    "error": "File upload failed",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # Legacy methods for backward compatibility - will be refactored in future steps
    def _handle_single_file_upload(self, inbound_file, upload_id, notebook, user):
        """Legacy method - use service instead"""
        return self.file_service.handle_single_file_upload(inbound_file, upload_id, notebook, user)

    def _handle_batch_file_upload(self, files, notebook, user):
        """Legacy method - use service instead"""
        return self.file_service.handle_batch_file_upload(files, notebook, user)


class FileListView(StandardAPIView, NotebookPermissionMixin, FileListResponseMixin):
    """List all knowledge items linked to a notebook."""

    def get(self, request, notebook_id):
        """Get all files linked to the notebook."""
        try:
            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)

            # Get all KnowledgeItems for this notebook with optimized query
            knowledge_items = (
                KnowledgeItem.objects.filter(notebook=notebook)
                .select_related("knowledge_base_item", "source", "source__url_result")
                .order_by("-added_at")
            )

            # Build response data using mixin
            files = [self.build_file_response_data(ki) for ki in knowledge_items]

            return self.success_response(files)

        except Exception as e:
            return self.error_response(
                "Failed to retrieve files",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )


class FileStatusView(APIView):
    """
    GET /api/notebooks/{notebook_id}/files/{upload_file_id}/status/
    Return a one‐time snapshot of parsing status, or 404 if unknown.
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def get(self, request, notebook_id, upload_file_id):
        # verify notebook ownership
        from ..models import Notebook
        from rest_framework import permissions, authentication
        
        if not Notebook.objects.filter(id=notebook_id, user=request.user).exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        status_obj = upload_processor.get_upload_status(upload_file_id, request.user.pk)
        if not status_obj:
            return Response(
                {"detail": "Status not found."}, status=status.HTTP_404_NOT_FOUND
            )
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
        from ..models import Notebook
        from rest_framework import permissions, authentication
        import time
        import json
        from django.http import StreamingHttpResponse
        
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
                    status_obj = upload_processor.get_upload_status(
                        upload_file_id, request.user.pk
                    )

                    if status_obj:
                        # Send status update as SSE event
                        event_data = {
                            "status": status_obj.get("status", "unknown"),
                            "job_details": {
                                "progress_percentage": status_obj.get(
                                    "progress_percentage", 0
                                ),
                                "result": status_obj.get("metadata", {}),
                                "error": status_obj.get("error"),
                            },
                        }

                        yield f"data: {json.dumps(event_data)}\n\n"

                        # If upload is complete, send final event and close
                        if status_obj.get("status") in [
                            "completed",
                            "error",
                            "cancelled",
                            "unsupported",
                        ]:
                            break
                    else:
                        # No status found, might be completed or doesn't exist
                        yield f"data: {json.dumps({'status': 'not_found', 'job_details': {}})}\n\n"
                        break

                except Exception as e:
                    # Send error event
                    error_data = {"status": "error", "job_details": {"error": str(e)}}
                    yield f"data: {json.dumps(error_data)}\n\n"
                    break

                # Wait before next poll
                time.sleep(poll_interval)

            # Send final close event
            yield f"data: {json.dumps({'status': 'stream_closed', 'job_details': {}})}\n\n"

        response = StreamingHttpResponse(
            event_stream(), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["Connection"] = "keep-alive"
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control"

        return response


class FileDeleteView(APIView):
    """
    DELETE /api/notebooks/{notebook_id}/files/{file_or_upload_id}/
    Delete a knowledge item link from notebook or delete from knowledge base entirely.
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def delete(self, request, notebook_id, file_or_upload_id):
        from ..models import Notebook
        from ..utils.storage_adapter import get_storage_adapter
        from rest_framework import permissions, authentication
        
        # verify notebook ownership
        notebook = get_object_or_404(Notebook, id=notebook_id, user=request.user)
        storage_adapter = get_storage_adapter()

        force_delete = request.GET.get("force", "false").lower() == "true"
        deleted = False

        # Strategy 1: Try to find by knowledge_item_id (direct database ID)
        if not deleted:
            try:
                # Try as UUID string directly (no int conversion needed)
                ki = KnowledgeItem.objects.filter(
                    id=file_or_upload_id, notebook=notebook
                ).first()

                if ki:
                    if force_delete:
                        # Delete the knowledge base item entirely
                        success = storage_adapter.delete_knowledge_base_item(
                            str(ki.knowledge_base_item.id), request.user.pk
                        )
                        if success:
                            deleted = True
                    else:
                        # Just delete the link
                        ki.delete()
                        deleted = True
            except Exception:
                pass  # Not a valid UUID or other error

        # Strategy 2: Try to find by knowledge_base_item_id (UUID string)
        if not deleted:
            try:
                # Try as UUID string directly (no int conversion needed)
                ki = KnowledgeItem.objects.filter(
                    notebook=notebook, knowledge_base_item_id=file_or_upload_id
                ).first()

                if ki:
                    if force_delete:
                        # Delete the knowledge base item entirely
                        success = storage_adapter.delete_knowledge_base_item(
                            str(file_or_upload_id), request.user.pk
                        )
                        if success:
                            deleted = True
                    else:
                        # Just unlink from this notebook
                        success = storage_adapter.unlink_knowledge_item_from_notebook(
                            str(file_or_upload_id), notebook_id, request.user.pk
                        )
                        if success:
                            deleted = True
            except (ValueError, TypeError):
                pass  # Not a valid integer ID

        # Strategy 3: Handle upload IDs by searching in metadata
        if not deleted and str(file_or_upload_id).startswith("upload_"):
            try:
                # Find knowledge items in this notebook that have the upload ID in metadata
                knowledge_items = KnowledgeItem.objects.filter(
                    notebook=notebook
                ).select_related("knowledge_base_item", "source")

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

                    if upload_id_match:
                        if force_delete:
                            # Delete the knowledge base item entirely
                            success = storage_adapter.delete_knowledge_base_item(
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
                logger.error(f"Error handling upload ID {file_or_upload_id}: {e}")

        # Strategy 4: Legacy fallback - try as string knowledge base item ID
        if not deleted:
            try:
                # Some systems might pass KB item IDs as strings
                ki = KnowledgeItem.objects.filter(
                    notebook=notebook, knowledge_base_item_id=file_or_upload_id
                ).first()

                if ki:
                    if force_delete:
                        # Delete the knowledge base item entirely
                        success = storage_adapter.delete_knowledge_base_item(
                            str(ki.knowledge_base_item.id), request.user.pk
                        )
                        if success:
                            deleted = True
                    else:
                        # Just delete the link
                        ki.delete()
                        deleted = True

            except Exception as e:
                logger.error(f"Error in legacy fallback for {file_or_upload_id}: {e}")

        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                {"detail": "File not found."}, status=status.HTTP_404_NOT_FOUND
            )


class FileContentView(StandardAPIView, KnowledgeBasePermissionMixin):
    """Serve parsed content from knowledge base items."""

    def get(self, request, file_id):
        """Get processed content for a knowledge base item."""
        try:
            from ..utils.storage_adapter import get_storage_adapter
            storage_adapter = get_storage_adapter()
            
            # Get the knowledge base item (verifies ownership)
            kb_item = self.get_user_kb_item(file_id, request.user)

            # Check if user wants MinIO URLs for images
            use_minio_urls = request.GET.get('minio_urls', 'false').lower() == 'true'
            
            if use_minio_urls:
                # Get content with direct MinIO URLs
                content = storage_adapter.storage_service.get_content_with_minio_urls(
                    file_id, user_id=request.user.pk
                )
            else:
                # Get content with API endpoint URLs (legacy behavior)
                content = storage_adapter.get_file_content(file_id, user_id=request.user.pk)

            if content is None:
                return self.error_response(
                    "Content not found or not accessible",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return self.success_response(
                {
                    "content": content,
                    "title": kb_item.title,
                    "content_type": kb_item.content_type,
                    "metadata": kb_item.metadata or {},
                    "uses_minio_urls": use_minio_urls,
                }
            )

        except Exception as e:
            return self.error_response(
                "Failed to retrieve content",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )


class FileContentMinIOView(StandardAPIView, KnowledgeBasePermissionMixin):
    """Serve parsed content from knowledge base items with direct MinIO URLs for images."""

    def get(self, request, file_id):
        """Get processed content with direct MinIO pre-signed URLs for images."""
        try:
            from ..utils.storage_adapter import get_storage_adapter
            from django.views.decorators.csrf import csrf_exempt
            from django.utils.decorators import method_decorator
            
            storage_adapter = get_storage_adapter()
            
            # Get the knowledge base item (verifies ownership)
            kb_item = self.get_user_kb_item(file_id, request.user)

            # Get content with direct MinIO URLs
            expires = int(request.GET.get('expires', '86400'))  # Default 24 hours
            content = storage_adapter.storage_service.get_content_with_minio_urls(
                file_id, user_id=request.user.pk, expires=expires
            )

            if content is None:
                return self.error_response(
                    "Content not found or not accessible",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return self.success_response(
                {
                    "content": content,
                    "title": kb_item.title,
                    "content_type": kb_item.content_type,
                    "metadata": kb_item.metadata or {},
                    "uses_minio_urls": True,
                    "url_expires_in": expires,
                }
            )

        except Exception as e:
            return self.error_response(
                "Failed to retrieve content with MinIO URLs",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )


class FileRawView(StandardAPIView, FileAccessValidatorMixin):
    """Serve raw file content (PDFs, videos, audio, etc.)."""

    def get(self, request, notebook_id, file_id):
        """Serve raw file through notebook context by streaming file content."""
        try:
            from django.http import Http404, StreamingHttpResponse
            from django.core.exceptions import PermissionDenied
            import requests
            import mimetypes
            
            # Validate access through notebook
            notebook, kb_item, knowledge_item = self.validate_notebook_file_access(
                notebook_id, file_id, request.user
            )

            # Try to get original file URL first
            file_url = None
            if kb_item.original_file_object_key:
                file_url = kb_item.get_original_file_url()
            
            # Fallback to processed file
            if not file_url and kb_item.file_object_key:
                file_url = kb_item.get_file_url()
            
            if not file_url:
                raise Http404("Raw file not found")

            # Get file metadata
            original_filename = kb_item.metadata.get('original_filename', 'file') if kb_item.metadata else 'file'
            content_type, _ = mimetypes.guess_type(original_filename)
            
            # For video files, stream the content directly
            if content_type and content_type.startswith('video/'):
                def file_iterator():
                    response = requests.get(file_url, stream=True)
                    response.raise_for_status()
                    for chunk in response.iter_content(chunk_size=8192):
                        yield chunk
                
                streaming_response = StreamingHttpResponse(
                    file_iterator(),
                    content_type=content_type
                )
                streaming_response['Content-Disposition'] = f'inline; filename="{original_filename}"'
                streaming_response['Accept-Ranges'] = 'bytes'
                return streaming_response
            else:
                # For non-video files, return pre-signed URL (existing behavior)
                return Response({"file_url": file_url}, status=status.HTTP_200_OK)

        except PermissionDenied as e:
            return self.error_response(str(e), status_code=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return self.error_response(str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return self.error_response(
                "File access failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )


class FileRawSimpleView(StandardAPIView, KnowledgeBasePermissionMixin):
    """Serve raw file content without requiring notebook context."""

    def get(self, request, file_id):
        """Serve raw file directly by knowledge base item ID."""
        try:
            # Get the knowledge base item (verifies ownership)
            kb_item = self.get_user_kb_item(file_id, request.user)

            # Try to serve original file first
            if kb_item.original_file_object_key:
                file_url = kb_item.get_original_file_url()
                if file_url:
                    return Response({"file_url": file_url}, status=status.HTTP_200_OK)

            # Fallback to processed file
            if kb_item.file_object_key:
                file_url = kb_item.get_file_url()
                if file_url:
                    return Response({"file_url": file_url}, status=status.HTTP_200_OK)

            return self.error_response(
                "File not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
                         return self.error_response(
                "Failed to get file URL",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )


class VideoImageExtractionView(StandardAPIView, NotebookPermissionMixin):
    """Handle video image extraction with deduplication and captioning for notebook files."""

    parser_classes = [JSONParser]
    
    def post(self, request, notebook_id):
        """Extract and process images from a video file with deduplication and captioning."""
        try:
            from ..serializers import VideoImageExtractionSerializer
            from ..utils.storage_adapter import get_storage_adapter
            from ..utils.media_extractor import MediaFeatureExtractor
            from ..utils.image_processing import clean_title
            from pathlib import Path
            import tempfile
            import requests
            import os
            
            storage_adapter = get_storage_adapter()
            media_extractor = MediaFeatureExtractor()
            
            # Validate request data
            serializer = VideoImageExtractionSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error_response(
                    "Invalid request data", details=serializer.errors
                )

            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)

            # Extract video file ID and processing parameters
            video_file_id = serializer.validated_data["video_file_id"]
            
            # Remove 'f_' prefix if present
            if video_file_id.startswith('f_'):
                actual_file_id = video_file_id[2:]
            else:
                actual_file_id = video_file_id

            # Get the knowledge base item for metadata
            kb_item = get_object_or_404(
                KnowledgeBaseItem, id=actual_file_id, user=request.user
            )

            # Get the original video file from MinIO and download to temp location
            video_file_url = storage_adapter.get_original_file_url(actual_file_id, request.user.pk)
            if not video_file_url:
                return self.error_response(
                    f"Video file not found for ID: {video_file_id}",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Download the video file to a temporary location
            try:
                response = requests.get(video_file_url, stream=True)
                response.raise_for_status()
                
                # Create temporary file with appropriate extension
                original_filename = kb_item.metadata.get('original_filename', 'video.mp4') if kb_item.metadata else 'video.mp4'
                file_extension = os.path.splitext(original_filename)[1] or '.mp4'
                
                temp_video_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
                for chunk in response.iter_content(chunk_size=8192):
                    temp_video_file.write(chunk)
                temp_video_file.close()
                
                video_file_path = temp_video_file.name
                
            except Exception as e:
                return self.error_response(
                    f"Failed to download video file: {str(e)}",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Validate that the file is a video
            if not self._is_video_file(video_file_path):
                # Clean up temp file
                os.unlink(video_file_path)
                return self.error_response(
                    f"File is not a video: {original_filename}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Build extraction options
            extraction_options = self._build_extraction_options(serializer.validated_data)

            # Generate clean title from filename
            video_title = clean_title(Path(original_filename).stem)

            # Use temporary directory for processing
            temp_base_dir = tempfile.mkdtemp(prefix=f"video_extraction_{actual_file_id}_")
            base_file_dir = temp_base_dir

            try:
                # Process the video for image extraction
                async def process_video_async():
                    return await media_extractor.process_video_for_images(
                        file_path=video_file_path,
                        output_dir=base_file_dir,
                        video_title=video_title,
                        extraction_options=extraction_options,
                        final_images_dir_name="images"
                    )

                # Run async processing
                result = async_to_sync(process_video_async)()

                # Calculate final output paths
                final_images_dir = os.path.join(base_file_dir, 'images')
                
                # Upload extracted images to MinIO
                if result.get('success') and os.path.exists(final_images_dir):
                    self._upload_extracted_images_to_minio(final_images_dir, kb_item)
                    self._process_local_caption_data(final_images_dir, kb_item)

                # Clean up temp files
                os.unlink(video_file_path)
                import shutil
                shutil.rmtree(temp_base_dir, ignore_errors=True)

                return self.success_response({
                    "success": True,
                    "message": "Video image extraction completed successfully",
                    "file_id": video_file_id,
                    "notebook_id": notebook_id,
                    "result": result
                })

            except Exception as e:
                # Clean up temp files
                if os.path.exists(video_file_path):
                    os.unlink(video_file_path)
                import shutil
                shutil.rmtree(temp_base_dir, ignore_errors=True)
                raise e

        except Exception as e:
            return self.error_response(
                "Video image extraction failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )

    def _is_video_file(self, file_path):
        """Check if file is a video based on content type."""
        import mimetypes
        content_type, _ = mimetypes.guess_type(file_path)
        return content_type and content_type.startswith('video/')

    def _build_extraction_options(self, validated_data):
        """Build extraction options from validated data."""
        return {
            'dedup_pixel_global': validated_data.get('dedup_pixel_global', True),
            'dedup_deep_sequential': validated_data.get('dedup_deep_sequential', True),
            'dedup_deep_global': validated_data.get('dedup_deep_global', True),
            'dedup_text_ocr': validated_data.get('dedup_text_ocr', True),
            'generate_captions': validated_data.get('generate_captions', True),
        }

    def _upload_extracted_images_to_minio(self, final_images_dir, kb_item):
        """Upload extracted images to MinIO storage."""
        # Implementation would go here
        pass

    def _process_local_caption_data(self, final_images_dir, kb_item):
        """Process caption data locally."""
        # Implementation would go here
        pass


class FileImageView(StandardAPIView, FileAccessValidatorMixin):
    """Serve individual images from knowledge base items."""

    def get(self, request, notebook_id, file_id, figure_id):
        """Serve an individual image file."""
        try:
            # Validate access through notebook
            notebook, kb_item, knowledge_item = self.validate_notebook_file_access(
                notebook_id, file_id, request.user
            )

            # Find the image by figure ID
            from ..models import KnowledgeBaseImage
            
            try:
                image = KnowledgeBaseImage.objects.get(
                    knowledge_base_item=kb_item,
                    figure_id=figure_id
                )
            except KnowledgeBaseImage.DoesNotExist:
                return self.error_response(
                    f"Image '{figure_id}' not found in file",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Get pre-signed URL for the image
            image_url = image.get_image_url(expires=3600)  # 1 hour
            if not image_url:
                return self.error_response(
                    "Image not accessible",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Return the image URL or serve the image directly
            return Response({
                "image_url": image_url,
                "figure_id": str(image.figure_id),
                "caption": image.image_caption,
                "content_type": image.content_type,
                "file_size": image.file_size
            })

        except Exception as e:
            return self.error_response(
                "Failed to access image",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            ) 