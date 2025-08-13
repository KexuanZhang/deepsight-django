"""
Simplified Celery tasks for podcast generation using Panel Discussion Framework.
"""

import logging
import json
import asyncio
import redis
from celery import shared_task
from django.utils import timezone
from django.conf import settings

from .models import Podcast
from .service import PodcastService

logger = logging.getLogger(__name__)


def update_job_status(job, redis_client=None):
    """Update job status in both database and Redis cache"""
    job.save()
    
    if not redis_client:
        redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
    
    # Create status data for Redis
    status_data = {
        "job_id": str(job.id),
        "status": job.status,
        "progress": job.progress,
        "error_message": job.error_message,
        "audio_file_url": job.get_audio_url() if hasattr(job, 'get_audio_url') else None,
        "title": job.title,
        "status_message": getattr(job, 'status_message', None),
    }
    
    # Update Redis cache with 1 hour expiration
    redis_client.setex(
        f"podcast_job_status:{job.id}",
        3600,  # 1 hour
        json.dumps(status_data)
    )


@shared_task(bind=True)
def process_podcast_generation(self, job_id: str):
    """
    Simplified podcast generation using panel discussion framework.
    
    Args:
        job_id: UUID of the Podcast to process
    """
    try:
        # Get the job and Redis client
        job = Podcast.objects.get(id=job_id)
        redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        logger.info(f"Starting podcast generation for job {job_id}")

        # Check if job was cancelled before we start
        if job.status == "cancelled":
            logger.info(f"Job {job_id} was cancelled before processing started")
            return {"status": "cancelled", "message": "Job was cancelled"}

        # Update job status to processing
        job.status = "generating"
        job.progress = 10
        job.status_message = "Preparing content from selected sources..."
        job.processing_started_at = timezone.now()
        update_job_status(job, redis_client)
        # Get selected item IDs from job metadata
        selected_item_ids = job.source_file_ids or []
        

        # Update job status to generating panel discussion
        job.status_message = "Generating panel discussion..."
        update_job_status(job, redis_client)
        # Generate the podcast using service instance
        podcast_service = PodcastService()
        result = asyncio.run(podcast_service.create_podcast_with_panel_crew(
            selected_item_ids=selected_item_ids,
            user_id=job.user.id,
            podcast_id=str(job.id),
            notebook_id=job.notebook.id if job.notebook else None,
            custom_instruction=getattr(job, 'custom_instruction', None)
        ))
        
        # Update progress - generating audio
        job.progress = 70
        job.status_message = "Converting conversation to audio..."
        update_job_status(job, redis_client)
        
        if result["status"] == "completed":
            # Update job with results
            job.status = "completed"
            job.progress = 100
            job.status_message = "Podcast generation completed successfully"
            job.processing_completed_at = timezone.now()
            
            # Store the audio object key in the database
            job.audio_object_key = result.get("audio_object_key")
            
            # Store file metadata
            if result.get("audio_object_key"):
                job.file_metadata = {
                    "filename": f"podcast_{job.id}.mp3",
                    "content_type": "audio/mpeg",
                    "object_key": result["audio_object_key"],
                    "participants": result["metadata"]["participants"],
                    "conversation_turns": result["metadata"]["total_turns"]
                }
            
            # Store conversation text for search/display
            conversation_text = "\n\n".join([
                f"{turn['speaker']}: {turn['content']}" 
                for turn in result["conversation_turns"]
            ])
            job.conversation_text = conversation_text
            
            # Store the results
            job.result_data = json.dumps({
                "conversation_turns": result["metadata"]["total_turns"],
                "participants": result["metadata"]["participants"],
                "audio_object_key": result.get("audio_object_key"),
                "generated_at": result["metadata"]["generated_at"],
                "selected_items_count": result["metadata"]["selected_items_count"],
                "topic": result["metadata"]["topic"]
            })
            
            # Conversation JSON formatting available via utils if needed in the future
            
            update_job_status(job, redis_client)
            
            logger.info(f"Podcast generation completed successfully for job {job_id}")
            return {
                "status": "completed",
                "message": "Podcast generated successfully",
                "audio_object_key": result["audio_object_key"],
                "conversation_turns": result["metadata"]["total_turns"]
            }
        else:
            # Handle failure
            job.status = "error"
            job.progress = 0
            job.status_message = f"Generation failed: {result['error']}"
            job.processing_completed_at = timezone.now()
            update_job_status(job, redis_client)
            
            logger.error(f"Podcast generation failed for job {job_id}: {result['error']}")
            return {
                "status": "failed",
                "message": result["error"]
            }
            
    except Podcast.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        return {"status": "failed", "message": "Job not found"}
        
    except Exception as e:
        logger.error(f"Unexpected error in podcast generation for job {job_id}: {e}")
        try:
            job = Podcast.objects.get(id=job_id)
            redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            job.status = "error"
            job.progress = 0
            job.status_message = f"Unexpected error: {str(e)}"
            job.processing_completed_at = timezone.now()
            update_job_status(job, redis_client)
        except:
            pass
            
        return {"status": "failed", "message": str(e)}



@shared_task(bind=True)
def cancel_podcast_generation(self, job_id: str):
    """Cancel a podcast generation job"""
    try:
        logger.info(f"Cancelling podcast generation for job {job_id}")
        
        # Get the job
        job = Podcast.objects.get(id=job_id)
        
        # Cancel the background task if it's running
        if job.celery_task_id:
            try:
                from backend.celery import app as celery_app
                celery_app.control.revoke(
                    job.celery_task_id, terminate=True, signal="SIGTERM"
                )
                logger.info(f"Revoked Celery task {job.celery_task_id} for job {job_id}")
            except Exception as e:
                logger.warning(f"Failed to revoke Celery task for job {job_id}: {e}")
        
        # Update job status in database and Redis
        redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        job.status = "cancelled"
        job.error_message = "Job cancelled by user"
        job.progress = 0
        job.status_message = "Job cancelled"
        update_job_status(job, redis_client)
        
        logger.info(f"Successfully cancelled podcast generation for job {job_id}")
        return {"status": "cancelled", "job_id": job_id}
    
    except Podcast.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        return {"status": "failed", "job_id": job_id, "message": "Job not found"}
    except Exception as e:
        logger.error(f"Error cancelling podcast generation for job {job_id}: {e}")
        raise


@shared_task
def cleanup_old_podcast_jobs():
    """Clean up old podcast jobs and associated files"""
    from django.utils import timezone
    from datetime import timedelta

    try:
        # Delete jobs older than 30 days that are completed or failed
        cutoff_date = timezone.now() - timedelta(days=30)
        old_jobs = Podcast.objects.filter(
            created_at__lt=cutoff_date, 
            status__in=["completed", "error", "cancelled"]
        )

        deleted_count = 0
        for job in old_jobs:
            try:
                # Delete associated audio file from MinIO if it exists
                if hasattr(job, 'audio_object_key') and job.audio_object_key:
                    try:
                        from .storage import PodcastStorageService
                        storage_service = PodcastStorageService()
                        storage_service.delete_podcast_audio(job.audio_object_key)
                    except Exception as e:
                        logger.error(f"Error deleting audio file from MinIO: {e}")

                job.delete()
                deleted_count += 1

            except Exception as e:
                logger.error(f"Error deleting old job {job.id}: {e}")

        logger.info(f"Cleaned up {deleted_count} old podcast jobs")
        return deleted_count

    except Exception as e:
        logger.error(f"Error during podcast job cleanup: {e}")
        raise