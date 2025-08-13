from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse, HttpResponse
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
import logging
import json
import time
import redis
from django.conf import settings

from .models import Podcast
from .serializers import (
    PodcastSerializer,
    PodcastListSerializer,
    NotebookPodcastCreateSerializer,
)
from notebooks.models import Notebook

logger = logging.getLogger(__name__)


# Notebook-specific views
class NotebookPodcastListCreateView(APIView):
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
            jobs = Podcast.objects.filter(
                user=request.user,
                notebook=notebook
            ).order_by('-created_at')
            
            # Calculate last modified time for caching
            last_modified = None
            if jobs:
                last_modified = max(job.updated_at for job in jobs)
            
            serializer = PodcastListSerializer(jobs, many=True)
            response = Response(serializer.data)
            
            # Add caching headers
            if last_modified:
                response['Last-Modified'] = last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            # Use minimal caching to ensure delete operations are immediately reflected
            has_active_jobs = any(job_data.get('status') in ['pending', 'generating'] for job_data in serializer.data)
            cache_timeout = 2 if has_active_jobs else 5
            response['Cache-Control'] = f'max-age={cache_timeout}, must-revalidate'
            
            return response
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
            serializer = NotebookPodcastCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Extract data
            source_file_ids = serializer.validated_data["source_file_ids"]
            title = serializer.validated_data.get("title", "Generated Podcast")
            description = serializer.validated_data.get("description", "")

            # Create podcast job directly using Django model
            job = Podcast.objects.create(
                user=request.user,
                notebook=notebook,
                title=title,
                description=description,
                source_file_ids=source_file_ids,
                source_metadata={},  # Will be populated by worker
                status="pending"
            )

            # Queue the job for background processing
            from .tasks import process_podcast_generation

            task_result = process_podcast_generation.delay(str(job.id))

            # Store the Celery task ID for cancellation purposes
            job.celery_task_id = task_result.id
            job.save()

            # Return job details
            response_serializer = PodcastSerializer(job)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating podcast-job for notebook {notebook_id}: {e}")
            return Response(
                {"error": f"Failed to create podcast-job: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class NotebookPodcastDetailView(APIView):
    """Retrieve, update, or delete a specific podcast-job within a notebook"""
    permission_classes = [permissions.IsAuthenticated]

    def get_job(self, notebook_id, job_id):
        """Get the job and verify user and notebook access"""
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )
        return get_object_or_404(
            Podcast.objects.filter(user=self.request.user, notebook=notebook),
            id=job_id
        )

    def get(self, request, notebook_id, job_id):
        """Get detailed status of a specific podcast-job"""
        try:
            job = self.get_job(notebook_id, job_id)
            serializer = PodcastSerializer(job)
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

            # Delete the podcast audio file from MinIO
            if job.audio_object_key:
                try:
                    from notebooks.utils.storage import get_minio_backend
                    minio_backend = get_minio_backend()
                    minio_backend.delete_file(job.audio_object_key)
                    logger.info(f"Successfully deleted podcast audio file for job {job_id}")
                        
                except Exception as e:
                    logger.error(f"Error deleting podcast audio file for job {job_id}: {e}")
            
            # Delete the job record from database
            job.delete()
            
            response = Response(status=status.HTTP_204_NO_CONTENT)
            
            # Add cache-busting headers to ensure browsers don't cache delete responses
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            return response

        except Exception as e:
            logger.error(f"Error deleting podcast-job {job_id} for notebook {notebook_id}: {e}")
            return Response(
                {"error": f"Failed to delete job: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class NotebookPodcastCancelView(APIView):
    """Cancel a podcast-job within a notebook"""
    permission_classes = [permissions.IsAuthenticated]

    def get_job(self, notebook_id, job_id):
        """Get the job and verify user and notebook access"""
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )
        return get_object_or_404(
            Podcast.objects.filter(user=self.request.user, notebook=notebook),
            id=job_id
        )

    def post(self, request, notebook_id, job_id):
        """Cancel a podcast generation podcast-job"""
        try:
            job = self.get_job(notebook_id, job_id)

            if job.status in ["pending", "generating"]:
                # Cancel the background task using the Celery task from tasks.py
                from .tasks import cancel_podcast_generation
                
                task_result = cancel_podcast_generation.delay(str(job.id))
                result = task_result.get(timeout=10)  # Wait up to 10 seconds
                
                if result.get("status") == "cancelled":
                    # Refresh job from database to get updated status
                    job.refresh_from_db()
                    serializer = PodcastSerializer(job)
                    return Response(serializer.data)
                else:
                    return Response(
                        {"error": result.get("message", "Failed to cancel job")},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
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


class NotebookPodcastAudioView(APIView):
    """Serve audio files for podcast-jobs within a notebook"""
    permission_classes = [permissions.IsAuthenticated]

    def get_job(self, notebook_id, job_id):
        """Get the job and verify user and notebook access"""
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )
        return get_object_or_404(
            Podcast.objects.filter(user=self.request.user, notebook=notebook),
            id=job_id
        )

    def get(self, request, notebook_id, job_id):
        """Stream the generated audio file"""
        try:
            job = self.get_job(notebook_id, job_id)

            # Debug logging
            logger.info(f"Audio request for job {job_id}: status={job.status}, audio_object_key={job.audio_object_key}")
            
            if not job.audio_object_key:
                logger.warning(f"No audio file for job {job_id} - status: {job.status}")
                return Response(
                    {"error": "Audio file not available"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get pre-signed URL for audio file
            audio_url = job.get_audio_url()
            if not audio_url:
                logger.error(f"Could not generate audio URL for job {job_id}")
                return Response(
                    {"error": "Audio file not accessible"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Return URL in JSON for API consistency, or redirect based on Accept header
            if request.headers.get('Accept') == 'application/json':
                return Response({"audio_url": audio_url})
            else:
                # Redirect to the pre-signed URL for direct access
                from django.http import HttpResponseRedirect
                return HttpResponseRedirect(audio_url)

        except Exception as e:
            logger.error(f"Error serving audio for job {job_id} in notebook {notebook_id}: {e}")
            return Response(
                {"error": f"Failed to serve audio: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class NotebookPodcastDownloadView(APIView):
    """Download audio files for podcast-jobs within a notebook"""
    permission_classes = [permissions.IsAuthenticated]

    def get_job(self, notebook_id, job_id):
        """Get the job and verify user and notebook access"""
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )
        return get_object_or_404(
            Podcast.objects.filter(user=self.request.user, notebook=notebook),
            id=job_id
        )

    def get(self, request, notebook_id, job_id):
        """Download the generated audio file"""
        try:
            job = self.get_job(notebook_id, job_id)

            # Debug logging
            logger.info(f"Download request for job {job_id}: status={job.status}, audio_object_key={job.audio_object_key}")
            
            if not job.audio_object_key:
                logger.warning(f"No audio file for job {job_id} - status: {job.status}")
                return Response(
                    {"error": "Audio file not available"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Generate download URL with proper headers
            try:
                from notebooks.utils.storage import get_minio_backend
                minio_backend = get_minio_backend()
                
                # Generate filename
                safe_title = "".join(c for c in (job.title or "podcast") if c.isalnum() or c in (' ', '-', '_')).rstrip()
                filename = f"{safe_title}.mp3" if safe_title else f"podcast-{job.id}.mp3"
                
                # Get pre-signed URL with download headers
                download_url = minio_backend.get_presigned_url(
                    object_key=job.audio_object_key,
                    response_headers={
                        'Content-Disposition': f'attachment; filename="{filename}"',
                        'Content-Type': 'audio/mpeg'
                    }
                )
                
                if not download_url:
                    logger.error(f"Could not generate download URL for job {job_id}")
                    return Response(
                        {"error": "Audio file not accessible"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                # Redirect to the pre-signed download URL
                from django.http import HttpResponseRedirect
                return HttpResponseRedirect(download_url)

            except Exception as e:
                logger.error(f"Error generating download URL for job {job_id}: {e}")
                return Response(
                    {"error": f"Failed to generate download URL: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            logger.error(f"Error downloading audio for job {job_id} in notebook {notebook_id}: {e}")
            return Response(
                {"error": f"Failed to download audio: {str(e)}"},
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
        if not Podcast.objects.filter(
            id=job_id, 
            user=request.user, 
            notebook=notebook
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
            max_duration = 3600  # 60 minutes maximum
            start_time = time.time()
            poll_interval = 2  # Check every 2 seconds

            while time.time() - start_time < max_duration:
                try:
                    # Check if job still exists and get current status
                    current_job = Podcast.objects.filter(
                        id=job_id, user=request.user, notebook=notebook
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
                            "job_id": str(current_job.id),
                            "status": current_job.status,
                            "progress": current_job.progress,
                            "error_message": current_job.error_message,
                            "audio_file_url": current_job.get_audio_url(),
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
