"""
Celery tasks for podcast generation.
"""

import logging
import asyncio
from typing import List, Dict
from pathlib import Path
from celery import shared_task
import tempfile
from django.core.files import File
import os

from .models import PodcastJob
from .services import podcast_generation_service
from notebooks.utils.file_storage import FileStorageService
from notebooks.models import KnowledgeBaseItem

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_podcast_generation(self, job_id: str):
    """Process podcast generation job - this runs in the background worker"""
    try:
        # Get the job
        job = PodcastJob.objects.get(job_id=job_id)

        # Check if job was cancelled before we start
        if job.status == "cancelled":
            logger.info(f"Job {job_id} was cancelled before processing started")
            return {"status": "cancelled", "message": "Job was cancelled"}

        # Update job status to processing
        podcast_generation_service.update_job_progress(
            job_id, "Starting podcast generation", "generating"
        )

        # Get content from source files
        podcast_generation_service.update_job_progress(
            job_id, "Gathering content from source files", "generating"
        )

        # Check if job was cancelled
        job.refresh_from_db()
        if job.status == "cancelled":
            logger.info(f"Job {job_id} was cancelled during content gathering")
            return {"status": "cancelled", "message": "Job was cancelled"}

        combined_content = ""
        source_metadata = []

        # Initialize file storage service
        file_storage = FileStorageService()

        for file_id in job.source_file_ids:
            try:
                # Get parsed file content using synchronous method
                content = file_storage.get_file_content(
                    file_id, user_id=job.user_id if job.user else None
                )

                if content:
                    # Get metadata from knowledge base item
                    try:
                        kb_item = KnowledgeBaseItem.objects.get(id=file_id)
                        metadata = {
                            "filename": kb_item.title,
                            "content_type": kb_item.content_type,
                            "id": str(kb_item.id),
                            **kb_item.metadata,
                        }
                    except KnowledgeBaseItem.DoesNotExist:
                        metadata = {"filename": f"File {file_id}", "id": str(file_id)}

                    combined_content += (
                        f"\n\n--- {metadata.get('filename', 'Unknown File')} ---\n\n"
                    )
                    combined_content += content
                    source_metadata.append(metadata)
                else:
                    logger.warning(f"No content found for file {file_id}")
            except Exception as e:
                logger.warning(f"Error getting content for file {file_id}: {e}")

        if not combined_content.strip():
            raise ValueError("No content available from source files")

        # Check if job was cancelled before conversation generation
        job.refresh_from_db()
        if job.status == "cancelled":
            logger.info(f"Job {job_id} was cancelled before conversation generation")
            return {"status": "cancelled", "message": "Job was cancelled"}

        podcast_generation_service.update_job_progress(
            job_id, "Generating podcast conversation", "generating"
        )

        # Generate podcast conversation using asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            conversation_text = loop.run_until_complete(
                podcast_generation_service.generate_podcast_conversation(
                    combined_content, {"sources": source_metadata}
                )
            )

            # Check if job was cancelled before audio generation
            job.refresh_from_db()
            if job.status == "cancelled":
                logger.info(f"Job {job_id} was cancelled before audio generation")
                return {"status": "cancelled", "message": "Job was cancelled"}

            podcast_generation_service.update_job_progress(
                job_id, "Generating podcast audio", "generating"
            )

            # Generate audio file using centralized storage config
            from notebooks.utils.config import storage_config
            
            # Generate audio filename
            audio_filename = f"{job_id}.mp3"
            
            # Use the centralized function to create the path
            final_audio_path, relative_path = storage_config.create_podcast_file_path(job, audio_filename)
            
            # Generate audio directly to the final location
            podcast_generation_service.generate_podcast_audio(
                conversation_text, str(final_audio_path)
            )
            
            # Save the relative path to database
            job.audio_file.name = relative_path
            job.save()

            # Prepare result
            result = {
                "job_id": job_id,
                "title": job.title,
                "description": job.description,
                "audio_path": str(job.audio_file.url),
                "source_metadata": source_metadata,
                "conversation_text": conversation_text,
                "duration_seconds": None,  # Could add audio duration analysis
            }

            # Update job with success
            podcast_generation_service.update_job_result(job_id, result, "completed")

            logger.info(f"Successfully completed podcast generation for job {job_id}")
            return result

        finally:
            loop.close()

    except PodcastJob.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        raise
    except KeyboardInterrupt:
        logger.info(f"Job {job_id} was interrupted")
        try:
            # Make sure the job status is updated to cancelled
            job = PodcastJob.objects.get(job_id=job_id)
            if job.status != "cancelled":
                job.status = "cancelled"
                job.error_message = "Job was interrupted"
                job.progress = "Job cancelled"
                job.save()
        except PodcastJob.DoesNotExist:
            pass
        return {"status": "cancelled", "message": "Job was cancelled"}
    except Exception as e:
        logger.error(f"Error processing podcast generation job {job_id}: {e}")
        podcast_generation_service.update_job_error(job_id, str(e))
        raise


@shared_task
def cleanup_old_podcast_jobs():
    """Clean up old podcast jobs and associated files"""
    from django.utils import timezone
    from datetime import timedelta

    try:
        # Delete jobs older than 30 days that are completed or failed
        cutoff_date = timezone.now() - timedelta(days=30)
        old_jobs = PodcastJob.objects.filter(
            created_at__lt=cutoff_date, status__in=["completed", "error", "cancelled"]
        )

        deleted_count = 0
        for job in old_jobs:
            try:
                # Delete associated audio file if it exists
                if job.audio_file:
                    job.audio_file.delete(save=False)

                job.delete()
                deleted_count += 1

            except Exception as e:
                logger.error(f"Error deleting old job {job.job_id}: {e}")

        logger.info(f"Cleaned up {deleted_count} old podcast jobs")
        return deleted_count

    except Exception as e:
        logger.error(f"Error during podcast job cleanup: {e}")
        raise
