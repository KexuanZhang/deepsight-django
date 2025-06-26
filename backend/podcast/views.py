from django.shortcuts import render, get_object_or_404
from django.http import Http404, FileResponse, StreamingHttpResponse, HttpResponse
from rest_framework import status, permissions, authentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
import logging
import json
import time
import redis
from pathlib import Path
from django.conf import settings

from .models import PodcastJob
from .serializers import (
    PodcastJobSerializer,
    PodcastJobListSerializer,
    NotebookPodcastJobCreateSerializer,
)
from .services import podcast_generation_service
from notebooks.models import Notebook

logger = logging.getLogger(__name__)


# Notebook-specific views
class NotebookPodcastJobListCreateView(APIView):
    """List and create podcast-jobs for a specific notebook"""
    permission_classes = [permissions.IsAuthenticated]

    def get_notebook(self, notebook_id):
        """Get the notebook and verify user access"""
        return get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )

    def get(self, request, notebook_id):
        """List podcast-jobs for a specific notebook"""
        try:
            notebook = self.get_notebook(notebook_id)
            jobs = PodcastJob.objects.filter(
                user=request.user,
                notebooks=notebook
            ).order_by('-created_at')
            
            serializer = PodcastJobListSerializer(jobs, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error listing podcast-jobs for notebook {notebook_id}: {e}")
            return Response(
                {"error": f"Failed to list jobs: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request, notebook_id):
        """Create a new podcast-job for a specific notebook"""
        try:
            notebook = self.get_notebook(notebook_id)
            serializer = NotebookPodcastJobCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Extract data
            source_file_ids = serializer.validated_data["source_file_ids"]
            title = serializer.validated_data.get("title", "Generated Podcast")
            description = serializer.validated_data.get("description", "")

            # Create job metadata
            job_metadata = {
                "title": title,
                "description": description,
                "source_metadata": {},  # Will be populated by worker
            }

            # Create podcast-job with notebook association
            job = podcast_generation_service.create_podcast_job(
                source_file_ids=source_file_ids,
                job_metadata=job_metadata,
                user=request.user,
                notebook=notebook,
            )

            # Queue the job for background processing
            from .tasks import process_podcast_generation

            task_result = process_podcast_generation.delay(str(job.job_id))

            # Store the Celery task ID for cancellation purposes
            job.celery_task_id = task_result.id
            job.save()

            # Return job details
            response_serializer = PodcastJobSerializer(job)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating podcast-job for notebook {notebook_id}: {e}")
            return Response(
                {"error": f"Failed to create podcast-job: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class NotebookPodcastJobDetailView(APIView):
    """Retrieve, update, or delete a specific podcast-job within a notebook"""
    permission_classes = [permissions.IsAuthenticated]

    def get_job(self, notebook_id, job_id):
        """Get the job and verify user and notebook access"""
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )
        return get_object_or_404(
            PodcastJob.objects.filter(user=self.request.user, notebooks=notebook),
            job_id=job_id
        )

    def get(self, request, notebook_id, job_id):
        """Get detailed status of a specific podcast-job"""
        try:
            job = self.get_job(notebook_id, job_id)
            serializer = PodcastJobSerializer(job)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving podcast-job {job_id} for notebook {notebook_id}: {e}")
            return Response(
                {"error": f"Failed to retrieve job: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def delete(self, request, notebook_id, job_id):
        """Delete a podcast-job and its associated files/directory"""
        try:
            job = self.get_job(notebook_id, job_id)

            # Delete the podcast directory using centralized storage config
            if job.audio_file:
                from notebooks.utils.config import storage_config
                
                try:
                    # Use the centralized deletion function
                    deletion_success = storage_config.delete_podcast_directory(job)
                    if deletion_success:
                        logger.info(f"Successfully deleted podcast directory for job {job_id}")
                    else:
                        logger.warning(f"Podcast directory not found or already deleted for job {job_id}")
                        
                except Exception as e:
                    logger.error(f"Error deleting podcast directory for job {job_id}: {e}")
                    # Fallback: try to delete the file directly if it exists
                    try:
                        from pathlib import Path
                        from django.conf import settings
                        
                        if job.audio_file.name:
                            audio_file_path = Path(settings.MEDIA_ROOT) / job.audio_file.name
                            if audio_file_path.exists():
                                audio_file_path.unlink()
                                logger.info(f"Deleted audio file: {audio_file_path}")
                    except Exception as fallback_error:
                        logger.error(f"Fallback deletion also failed: {fallback_error}")
            
            # Delete the job record from database
            job.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting podcast-job {job_id} for notebook {notebook_id}: {e}")
            return Response(
                {"error": f"Failed to delete job: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class NotebookPodcastJobCancelView(APIView):
    """Cancel a podcast-job within a notebook"""
    permission_classes = [permissions.IsAuthenticated]

    def get_job(self, notebook_id, job_id):
        """Get the job and verify user and notebook access"""
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )
        return get_object_or_404(
            PodcastJob.objects.filter(user=self.request.user, notebooks=notebook),
            job_id=job_id
        )

    def post(self, request, notebook_id, job_id):
        """Cancel a podcast generation podcast-job"""
        try:
            job = self.get_job(notebook_id, job_id)

            if job.status in ["pending", "generating"]:
                # Import here to avoid circular imports
                from backend.celery import app as celery_app

                # Cancel the background task if it's running
                try:
                    if job.celery_task_id:
                        celery_app.control.revoke(
                            job.celery_task_id, terminate=True, signal="SIGTERM"
                        )
                        logger.info(
                            f"Revoked Celery task {job.celery_task_id} for job {job.job_id}"
                        )
                    else:
                        logger.warning(f"No Celery task ID stored for job {job.job_id}")
                except Exception as e:
                    logger.warning(
                        f"Failed to revoke Celery task for job {job.job_id}: {e}"
                    )

                # Update job status in database
                job.status = "cancelled"
                job.error_message = "Job cancelled by user"
                job.progress = "Job cancelled"
                job.save()

                serializer = PodcastJobSerializer(job)
                return Response(serializer.data)
            else:
                return Response(
                    {"error": f"Cannot cancel job with status: {job.status}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error cancelling podcast-job {job_id} for notebook {notebook_id}: {e}")
            return Response(
                {"error": f"Failed to cancel job: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class NotebookPodcastJobAudioView(APIView):
    """Serve audio files for podcast-jobs within a notebook"""
    permission_classes = [permissions.IsAuthenticated]

    def get_job(self, notebook_id, job_id):
        """Get the job and verify user and notebook access"""
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )
        return get_object_or_404(
            PodcastJob.objects.filter(user=self.request.user, notebooks=notebook),
            job_id=job_id
        )

    def get(self, request, notebook_id, job_id):
        """Download the generated audio file"""
        try:
            job = self.get_job(notebook_id, job_id)

            # Debug logging
            logger.info(f"Audio request for job {job_id}: status={job.status}, audio_file={job.audio_file}")
            
            if not job.audio_file:
                logger.warning(f"No audio file for job {job_id} - status: {job.status}")
                return Response(
                    {"error": "Audio file not available"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Check if file exists on disk
            try:
                if not job.audio_file.storage.exists(job.audio_file.name):
                    logger.error(f"Audio file not found on disk for job {job_id}: {job.audio_file.name}")
                    return Response(
                        {"error": "Audio file not found on disk"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            except Exception as storage_error:
                logger.error(f"Error checking file existence for job {job_id}: {storage_error}")
                return Response(
                    {"error": "Audio file not accessible"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Return file response
            response = FileResponse(
                job.audio_file.open(), 
                as_attachment=True, 
                filename=f"{job.title}.mp3",
                content_type="audio/mpeg"
            )
            return response

        except Exception as e:
            logger.error(f"Error serving audio for job {job_id} in notebook {notebook_id}: {e}")
            return Response(
                {"error": f"Failed to serve audio: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


def notebook_job_status_stream(request, notebook_id, job_id):
    """Server-Sent Events endpoint for real-time job status updates within a notebook"""
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        response = HttpResponse(status=200)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Cache-Control, Authorization"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

    # Check authentication manually since we can't use DRF decorators with SSE
    if not request.user.is_authenticated:
        response = StreamingHttpResponse(
            f"data: {json.dumps({'type': 'error', 'message': 'Authentication required'})}\n\n",
            content_type="text/event-stream",
            status=401,
        )
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

    try:
        # Verify user has access to this job and notebook
        notebook = get_object_or_404(
            Notebook.objects.filter(user=request.user),
            pk=notebook_id
        )
        if not PodcastJob.objects.filter(
            job_id=job_id, 
            user=request.user, 
            notebooks=notebook
        ).exists():
            response = StreamingHttpResponse(
                f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n",
                content_type="text/event-stream",
                status=404,
            )
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Credentials"] = "true"
            return response

        def event_stream():
            """Generator function for SSE events"""
            redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            last_status = None
            max_duration = 300  # 5 minutes maximum
            start_time = time.time()
            poll_interval = 2  # Check every 2 seconds

            while time.time() - start_time < max_duration:
                try:
                    # Check if job still exists and get current status
                    current_job = PodcastJob.objects.filter(
                        job_id=job_id, user=request.user, notebooks=notebook
                    ).first()
                    if not current_job:
                        yield f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n"
                        break

                    # Get status from Redis cache (updated by worker) or fallback to DB
                    cached_status = redis_client.get(f"podcast_job_status:{job_id}")
                    if cached_status:
                        status_data = json.loads(cached_status.decode("utf-8"))
                    else:
                        # Fallback to database
                        status_data = {
                            "job_id": str(current_job.job_id),
                            "status": current_job.status,
                            "progress": current_job.progress,
                            "error_message": current_job.error_message,
                            "audio_file_url": current_job.audio_file.url
                            if current_job.audio_file
                            else None,
                            "title": current_job.title,
                        }

                    # Only send update if status changed
                    current_status_str = json.dumps(status_data, sort_keys=True)
                    if current_status_str != last_status:
                        yield f"data: {json.dumps({'type': 'job_status', 'data': status_data})}\n\n"
                        last_status = current_status_str

                    # Stop streaming if job is completed, failed, or cancelled
                    if status_data["status"] in ["completed", "error", "cancelled"]:
                        break

                    # Wait before next check
                    time.sleep(poll_interval)

                except Exception as e:
                    logger.error(f"Error in SSE stream for job {job_id} in notebook {notebook_id}: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    break

            # Send final close event
            yield f"data: {json.dumps({'type': 'stream_closed'})}\n\n"

        response = StreamingHttpResponse(
            event_stream(), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control"
        response["Access-Control-Allow-Credentials"] = "true"

        return response

    except Exception as e:
        logger.error(f"Error setting up SSE stream for job {job_id} in notebook {notebook_id}: {e}")
        response = StreamingHttpResponse(
            f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n",
            content_type="text/event-stream",
        )
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Credentials"] = "true"
        return response
