"""
File Views - Handle file upload and management operations only
"""
import logging
import traceback
from pathlib import Path
from uuid import uuid4

from asgiref.sync import async_to_sync
from django.core.exceptions import ValidationError
from django.http import Http404, FileResponse
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
        """Serve raw file through notebook context."""
        try:
            # Validate access through notebook
            notebook, kb_item, knowledge_item = self.validate_notebook_file_access(
                notebook_id, file_id, request.user
            )

            # Try to serve original file first
            if kb_item.original_file_object_key:
                return self._serve_minio_file(kb_item.original_file_object_key, kb_item.title)

            # Fallback to processed file
            if kb_item.file_object_key:
                return self._serve_minio_file(kb_item.file_object_key, kb_item.title)

            raise Http404("Raw file not found")

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

    def _serve_minio_file(self, object_key, title):
        """Serve a file from MinIO through Django's FileResponse."""
        try:
            from ..utils.storage import get_minio_backend
            from io import BytesIO
            import mimetypes
            
            minio_backend = get_minio_backend()
            file_content = minio_backend.get_file(object_key)
            
            # Guess content type from the title/filename
            content_type, _ = mimetypes.guess_type(title)
            if not content_type:
                content_type = "application/octet-stream"

            # Create a BytesIO stream from the content
            file_stream = BytesIO(file_content)
            
            response = FileResponse(
                file_stream, content_type=content_type, as_attachment=False
            )
            response["Content-Disposition"] = f'inline; filename="{title}"'
            response["X-Content-Type-Options"] = "nosniff"
            response["X-Frame-Options"] = "DENY"
            return response
        except Exception as e:
            raise Http404(f"File not accessible: {str(e)}")


class FileRawSimpleView(StandardAPIView, KnowledgeBasePermissionMixin):
    """Serve raw file content without requiring notebook context."""

    def get(self, request, file_id):
        """Serve raw file directly by knowledge base item ID."""
        try:
            # Get the knowledge base item (verifies ownership)
            kb_item = self.get_user_kb_item(file_id, request.user)

            # Try to serve original file first
            if kb_item.original_file_object_key:
                return self._serve_minio_file(kb_item.original_file_object_key, kb_item.title)

            # Fallback to processed file
            if kb_item.file_object_key:
                return self._serve_minio_file(kb_item.file_object_key, kb_item.title)

            raise Http404("Raw file not found")

        except Http404 as e:
            return self.error_response(str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return self.error_response(
                "File access failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )

    def _serve_minio_file(self, object_key, title):
        """Helper to serve a file from MinIO with proper headers."""
        try:
            from ..utils.storage import get_minio_backend
            from io import BytesIO
            import mimetypes
            
            minio_backend = get_minio_backend()
            file_content = minio_backend.get_file(object_key)
            
            # Guess content type from the title/filename
            content_type, _ = mimetypes.guess_type(title)
            if not content_type:
                content_type = "application/octet-stream"

            # Create a BytesIO stream from the content
            file_stream = BytesIO(file_content)
            
            response = FileResponse(
                file_stream, content_type=content_type, as_attachment=False
            )
            response["Content-Disposition"] = f'inline; filename="{title}"'
            response["X-Content-Type-Options"] = "nosniff"
            response["X-Frame-Options"] = "DENY"
            return response
        except Exception as e:
            raise Http404(f"File not accessible: {str(e)}")


class VideoImageExtractionView(StandardAPIView, NotebookPermissionMixin):
    """Handle video image extraction with deduplication and captioning for notebook files."""

    parser_classes = [JSONParser]
    
    def post(self, request, notebook_id):
        """Extract and process images from a video file with deduplication and captioning."""
        try:
            from ..serializers import VideoImageExtractionSerializer
            from ..utils.storage_adapter import get_storage_adapter
            from ..processors.media_processors import MediaProcessor
            from ..utils.helpers import clean_title
            from pathlib import Path
            import tempfile
            import requests
            import os
            
            storage_adapter = get_storage_adapter()
            media_extractor = MediaProcessor()
            
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
            'extract_interval': validated_data.get('extract_interval'),
            'pixel_threshold': validated_data.get('pixel_threshold'),
            'sequential_deep_threshold': validated_data.get('sequential_deep_threshold'),
            'global_deep_threshold': validated_data.get('global_deep_threshold'),
            'min_words': validated_data.get('min_words'),
            'dedup_pixel_global': validated_data.get('dedup_pixel_global', True),
            'dedup_deep_sequential': validated_data.get('dedup_deep_sequential', True),
            'dedup_deep_global': validated_data.get('dedup_deep_global', True),
            'dedup_text_ocr': validated_data.get('dedup_text_ocr', True),
            'generate_captions': validated_data.get('generate_captions', True),
        }

    def _upload_extracted_images_to_minio(self, local_images_dir: str, kb_item):
        """Upload extracted images from local directory to MinIO with proper structure."""
        try:
            import glob
            import os
            from ..models import KnowledgeBaseImage
            from ..utils.storage_adapter import get_storage_adapter
            
            storage_adapter = get_storage_adapter()
            
            # First, delete any existing images for this knowledge base item to avoid duplicates
            existing_images = KnowledgeBaseImage.objects.filter(knowledge_base_item=kb_item)
            if existing_images.exists():
                logger.info(f"Deleting {existing_images.count()} existing images for kb_item {kb_item.id}")
                
                # Delete files from MinIO first
                for img in existing_images:
                    if img.minio_object_key:
                        try:
                            storage_adapter.storage_service.minio_backend.delete_file(img.minio_object_key)
                            logger.info(f"Deleted existing image from MinIO: {img.minio_object_key}")
                        except Exception as e:
                            logger.warning(f"Failed to delete existing image from MinIO: {e}")
                
                # Delete database records
                existing_images.delete()
                logger.info(f"Deleted existing image records for kb_item {kb_item.id}")
            
            # Find all image files in the local directory
            image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.svg']
            image_files = []
            for ext in image_extensions:
                image_files.extend(glob.glob(os.path.join(local_images_dir, ext)))
            
            # Note: JSON files are now processed locally and stored in database, not uploaded to MinIO
            all_files = image_files
            
            if not all_files:
                logger.info(f"No images or data files found in {local_images_dir}")
                return
            
            logger.info(f"Uploading {len(all_files)} files from {local_images_dir} to MinIO")
            
            # Upload each file to MinIO
            figure_sequence = 1
            for file_path in all_files:
                try:
                    filename = os.path.basename(file_path)
                    
                    # Read file content
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    # Determine content type
                    import mimetypes
                    content_type, _ = mimetypes.guess_type(filename)
                    content_type = content_type or 'application/octet-stream'
                    
                    # Create and save KnowledgeBaseImage record first to get UUID
                    kb_image = KnowledgeBaseImage(
                        knowledge_base_item=kb_item,
                        image_caption="",  # Will be populated from caption data if available
                        content_type=content_type,
                        file_size=len(file_content),
                        image_metadata={
                            'original_filename': filename,
                            'file_size': len(file_content),
                            'content_type': content_type,
                            'kb_item_id': str(kb_item.id),
                            'source': 'video_extraction',
                            'extracted_from': 'video_processing',
                        }
                    )
                    # Save to get UUID for MinIO object key
                    kb_image.save()
                    
                    # Store in MinIO using file ID structure with images subfolder and UUID
                    object_key = storage_adapter.storage_service.minio_backend.save_file_with_auto_key(
                        content=file_content,
                        filename=filename,
                        prefix="kb",
                        content_type=content_type,
                        metadata={
                            'kb_item_id': str(kb_item.id),
                            'user_id': str(kb_item.user.id),
                            'file_type': 'video_extracted_image',
                            'extracted_from': 'video_processing',
                        },
                        user_id=str(kb_item.user.id),
                        file_id=str(kb_item.id),
                        subfolder="images",
                        subfolder_uuid=str(kb_image.id)
                    )
                    
                    # Update the record with MinIO object key
                    kb_image.minio_object_key = object_key
                    kb_image.save(update_fields=['minio_object_key'])
                    
                    logger.info(f"Uploaded {filename} to MinIO: {object_key}")
                    figure_sequence += 1
                    
                except Exception as e:
                    logger.error(f"Failed to upload {filename} to MinIO: {str(e)}")
                    continue
            
            logger.info(f"Successfully uploaded {len(all_files)} files to MinIO for kb_item {kb_item.id}")
            
        except Exception as e:
            logger.error(f"Error uploading extracted images to MinIO: {str(e)}")

    def _process_local_caption_data(self, local_images_dir: str, kb_item):
        """Process caption data from local JSON files and update KnowledgeBaseImage records."""
        try:
            import json
            import glob
            import os
            from ..models import KnowledgeBaseImage
            
            # Find JSON files with caption data
            json_files = glob.glob(os.path.join(local_images_dir, '*.json'))
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        caption_data = json.load(f)
                    
                    # Process caption data and update database records
                    if isinstance(caption_data, list):
                        for item in caption_data:
                            if isinstance(item, dict) and 'caption' in item:
                                caption = item['caption']
                                
                                # Find image by matching existing caption or create new one
                                image_record = KnowledgeBaseImage.objects.filter(
                                    knowledge_base_item=kb_item,
                                    image_caption=""  # Find images without captions to update
                                ).first()
                                
                                if image_record:
                                    image_record.image_caption = caption
                                    image_record.save(update_fields=['image_caption'])
                                    logger.info(f"Updated caption: {caption[:50]}...")
                    
                    logger.info(f"Processed caption data from {json_file}")
                    
                except Exception as e:
                    logger.error(f"Error processing caption file {json_file}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing local caption data: {str(e)}")



class FileImageView(StandardAPIView, FileAccessValidatorMixin):
    """Serve image files from knowledge base items using database storage."""

    def get(self, request, notebook_id, file_id, image_file):
        """Serve image file through notebook context from database/MinIO."""
        try:
            from django.http import Http404, HttpResponseRedirect, FileResponse
            from django.core.exceptions import PermissionDenied
            import mimetypes
            
            # Validate access through notebook
            notebook, kb_item, knowledge_item = self.validate_notebook_file_access(
                notebook_id, file_id, request.user
            )

            # Try to find the image in the database by filename in object key
            from ..models import KnowledgeBaseImage
            
            image_record = KnowledgeBaseImage.objects.filter(
                knowledge_base_item=kb_item,
                minio_object_key__icontains=image_file
            ).first()
            
            if image_record:
                # Serve from MinIO using the database record
                return self._serve_image_from_minio(image_record)
            
            # For JSON files and video extraction files, try to find them in MinIO directly
            if image_file.endswith(('.json', '.txt', '.md')):
                try:
                    return self._serve_file_from_minio_by_filename(kb_item, image_file)
                except Http404:
                    pass  # Fall through to filesystem fallback
            
            # Fallback: try to serve from legacy filesystem approach
            # This maintains backward compatibility during migration
            return self._serve_image_from_filesystem(kb_item, image_file)

        except PermissionDenied as e:
            return self.error_response(str(e), status_code=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return self.error_response(str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return self.error_response(
                "Image access failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )
    
    def _serve_image_from_minio(self, image_record):
        """Serve image from MinIO using database record."""
        try:
            from django.http import HttpResponseRedirect
            
            # Get pre-signed URL for the image
            image_url = image_record.get_image_url(expires=3600)  # 1 hour expiration
            
            if not image_url:
                raise Http404("Image file not accessible in storage")
            
            # Return redirect to pre-signed URL
            return HttpResponseRedirect(image_url)
            
        except Exception as e:
            logger.error(f"Error serving image from MinIO: {e}")
            raise Http404("Image file not accessible")
    
    def _serve_file_from_minio_by_filename(self, kb_item, filename):
        """Serve file from MinIO by searching for object keys that contain the filename."""
        try:
            from ..utils.storage_adapter import get_storage_adapter
            from django.http import HttpResponseRedirect, Http404
            
            storage_adapter = get_storage_adapter()
            backend = storage_adapter.storage_service.minio_backend
            
            # Search for objects that match the knowledge base item and filename pattern
            # The object key pattern is: user_id/kb/file_id/subfolder/filename (for video extraction files)
            prefix = f"{kb_item.user.id}/kb/{kb_item.id}/images/"
            
            try:
                # List objects with the prefix for this knowledge base item
                objects = backend.client.list_objects(backend.bucket_name, prefix=prefix)
                
                # Find the object that ends with our filename
                for obj in objects:
                    if obj.object_name.endswith(filename):
                        # Generate pre-signed URL
                        file_url = backend.get_presigned_url(obj.object_name, expires=3600)
                        
                        # Return redirect to pre-signed URL
                        return HttpResponseRedirect(file_url)
                
                # If no object found, try alternative prefix patterns
                # For backward compatibility with different object key structures
                alternative_prefixes = [
                    f"{kb_item.user.id}/kb/{kb_item.id}/",  # Files in root kb folder (no subfolder)
                    f"kb/{kb_item.user.id}/{kb_item.id}/images/",  # Alternative structure 1
                    f"kb/images/{kb_item.user.id}/{kb_item.id}/",  # Alternative structure 2
                ]
                
                for alt_prefix in alternative_prefixes:
                    try:
                        objects = backend.client.list_objects(backend.bucket_name, prefix=alt_prefix)
                        for obj in objects:
                            if obj.object_name.endswith(filename):
                                file_url = backend.get_presigned_url(obj.object_name, expires=3600)
                                return HttpResponseRedirect(file_url)
                    except Exception:
                        continue
                
                raise Http404(f"File not found in MinIO: {filename}")
                
            except Exception as e:
                logger.error(f"Error searching for file in MinIO: {filename} - {e}")
                raise Http404(f"File not accessible: {filename}")
            
        except Exception as e:
            logger.error(f"Error serving file from MinIO: {filename} - {e}")
            raise Http404(f"File not accessible: {filename}")
    
    def _serve_image_from_filesystem(self, kb_item, image_file):
        """Fallback method to serve image from filesystem (legacy support)."""
        try:
            from django.http import Http404, FileResponse
            import mimetypes
            
            # Import inside the method to avoid potential circular dependencies
            from reports.core.figure_service import FigureDataService

            images_dir = FigureDataService._get_knowledge_base_images_path(
                user_id=kb_item.user.id,
                file_id=str(kb_item.id),
            )

            if not images_dir:
                raise Http404(f"Image not found: {image_file}")
            
            image_path = Path(images_dir) / image_file
            
            # Check if image exists
            if not image_path.exists():
                raise Http404(f"Image not found: {image_file}")
            
            # Serve the image file
            return self._serve_image(image_path, image_file)

        except Exception as e:
            logger.error(f"Error serving image from filesystem: {e}")
            raise Http404(f"Image not found: {image_file}")

    def _serve_image(self, image_path: Path, image_file: str):
        """Serve an image file through Django's FileResponse."""
        try:
            from django.http import FileResponse, Http404
            import mimetypes
            
            response = FileResponse(
                open(image_path, 'rb'),
                as_attachment=False,
            )
            
            # Set content type based on file extension
            content_type, _ = mimetypes.guess_type(str(image_path))
            if not content_type:
                content_type = "application/octet-stream"
            
            response["Content-Type"] = content_type
            response["Content-Disposition"] = f'inline; filename="{image_file}"'
            response["Cache-Control"] = "public, max-age=3600"  # Cache for 1 hour
            response["X-Content-Type-Options"] = "nosniff"
            
            return response
        except Exception as e:
            raise Http404(f"Image not accessible: {str(e)}")