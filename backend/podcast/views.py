from django.shortcuts import render, get_object_or_404
from django.http import Http404, FileResponse, StreamingHttpResponse, HttpResponse
from rest_framework import status, permissions, authentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
import logging
import json
import time
import redis
from pathlib import Path
from django.conf import settings

from .models import PodcastJob
from .serializers import (
    PodcastJobSerializer,
    PodcastJobCreateSerializer,
    PodcastJobListSerializer,
)
from .services import podcast_generation_service

logger = logging.getLogger(__name__)


class PodcastJobViewSet(ModelViewSet):
    """ViewSet for managing podcast generation jobs"""

    serializer_class = PodcastJobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter jobs by current user"""
        return PodcastJob.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "create":
            return PodcastJobCreateSerializer
        elif self.action == "list":
            return PodcastJobListSerializer
        return PodcastJobSerializer

    def create(self, request):
        """Create a new podcast generation job"""
        try:
            serializer = self.get_serializer(data=request.data)
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

            # Create podcast job
            job = podcast_generation_service.create_podcast_job(
                source_file_ids=source_file_ids,
                job_metadata=job_metadata,
                user=request.user,
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
            logger.error(f"Error creating podcast job: {e}")
            return Response(
                {"error": f"Failed to create podcast job: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, pk=None):
        """Get detailed status of a specific podcast job"""
        try:
            job = get_object_or_404(self.get_queryset(), job_id=pk)
            serializer = self.get_serializer(job)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving podcast job {pk}: {e}")
            return Response(
                {"error": f"Failed to retrieve job: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, pk=None):
        """Delete a podcast job"""
        try:
            job = get_object_or_404(self.get_queryset(), job_id=pk)

            # Delete associated audio file if it exists
            if job.audio_file:
                job.audio_file.delete(save=False)

            job.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting podcast job {pk}: {e}")
            return Response(
                {"error": f"Failed to delete job: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a podcast generation job"""
        try:
            job = get_object_or_404(self.get_queryset(), job_id=pk)

            if job.status in ["pending", "generating"]:
                # Import here to avoid circular imports
                from backend.celery import app as celery_app

                # Cancel the background task if it's running
                try:
                    if job.celery_task_id:
                        # Revoke the task using the proper Celery task ID - using terminate=True to forcefully kill it
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

                serializer = self.get_serializer(job)
                return Response(serializer.data)
            else:
                return Response(
                    {"error": f"Cannot cancel job with status: {job.status}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error cancelling podcast job {pk}: {e}")
            return Response(
                {"error": f"Failed to cancel job: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"])
    def audio(self, request, pk=None):
        """Download the generated audio file"""
        try:
            job = get_object_or_404(self.get_queryset(), job_id=pk)

            if not job.audio_file:
                return Response(
                    {"error": "Audio file not available"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Return file response
            response = FileResponse(
                job.audio_file.open(), as_attachment=True, filename=f"{job.title}.mp3"
            )
            return response

        except Exception as e:
            logger.error(f"Error serving audio for job {pk}: {e}")
            return Response(
                {"error": f"Failed to serve audio: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def podcast_audio_serve(request, filename):
    """Serve podcast audio files directly"""
    try:
        # Extract job_id from filename (assuming format: job_id.mp3)
        job_id = filename.replace(".mp3", "")

        # Get the job and verify ownership
        job = get_object_or_404(
            PodcastJob.objects.filter(user=request.user), job_id=job_id
        )

        if not job.audio_file:
            raise Http404("Audio file not found")

        # Return file response
        response = FileResponse(job.audio_file.open(), content_type="audio/mpeg")
        return response

    except Exception as e:
        logger.error(f"Error serving audio file {filename}: {e}")
        raise Http404("Audio file not found")


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def podcast_jobs_summary(request):
    """Get summary statistics of podcast jobs for the current user"""
    try:
        jobs = PodcastJob.objects.filter(user=request.user)

        stats = {
            "total_jobs": jobs.count(),
            "pending_jobs": jobs.filter(status="pending").count(),
            "generating_jobs": jobs.filter(status="generating").count(),
            "completed_jobs": jobs.filter(status="completed").count(),
            "error_jobs": jobs.filter(status="error").count(),
            "cancelled_jobs": jobs.filter(status="cancelled").count(),
        }

        return Response(stats)

    except Exception as e:
        logger.error(f"Error getting podcast jobs summary: {e}")
        return Response(
            {"error": f"Failed to get summary: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )


def job_status_stream(request, job_id):
    """Server-Sent Events endpoint for real-time job status updates"""
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
        # Verify user has access to this job
        if not PodcastJob.objects.filter(job_id=job_id, user=request.user).exists():
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
                        job_id=job_id, user=request.user
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
                    logger.error(f"Error in SSE stream for job {job_id}: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    break

            # Send final close event
            yield f"data: {json.dumps({'type': 'stream_closed'})}\n\n"

        response = StreamingHttpResponse(
            event_stream(), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        # Remove Connection header - Django's development server doesn't handle this properly
        # response['Connection'] = 'keep-alive'  # Commented out to fix WSGI error
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control"
        response["Access-Control-Allow-Credentials"] = "true"

        return response

    except Exception as e:
        logger.error(f"Error setting up SSE stream for job {job_id}: {e}")
        response = StreamingHttpResponse(
            f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n",
            content_type="text/event-stream",
        )
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Credentials"] = "true"
        return response
