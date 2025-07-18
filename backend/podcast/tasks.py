"""
Celery tasks for podcast generation.
"""

import logging
import asyncio
from celery import shared_task

from .models import PodcastJob
from .orchestrator import podcast_orchestrator
from notebooks.utils.storage_adapter import get_storage_adapter
from notebooks.models import KnowledgeBaseItem

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_podcast_generation(self, job_id: str):
    """Process podcast generation job - this runs in the background worker"""
    try:
        # Get the job
        job = PodcastJob.objects.get(id=job_id)

        # Check if job was cancelled before we start
        if job.status == "cancelled":
            logger.info(f"Job {job_id} was cancelled before processing started")
            return {"status": "cancelled", "message": "Job was cancelled"}

        # Update job status to processing (10% progress)
        podcast_orchestrator.update_job_progress(
            job_id, "Starting podcast generation (10%)", "generating"
        )

        # Get content from source files (20% progress)
        podcast_orchestrator.update_job_progress(
            job_id, "Gathering content from source files (20%)", "generating"
        )

        # Check if job was cancelled
        job.refresh_from_db()
        if job.status == "cancelled":
            logger.info(f"Job {job_id} was cancelled during content gathering")
            return {"status": "cancelled", "message": "Job was cancelled"}

        combined_content = ""
        source_metadata = []

        # Initialize storage adapter
        storage_adapter = get_storage_adapter()

        for file_id in job.source_file_ids:
            try:
                # Get parsed file content using synchronous method
                content = storage_adapter.get_file_content(
                    file_id, user_id=job.user.id if job.user else None
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

        podcast_orchestrator.update_job_progress(
            job_id, "Generating podcast conversation and title (40%)", "generating"
        )

        # Generate podcast conversation using asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            conversation_text = loop.run_until_complete(
                podcast_orchestrator.generate_podcast_conversation(
                    combined_content, {"sources": source_metadata}
                )
            )
            
            # Generate title based on content and conversation (first stage)
            if job.title == "Generated Podcast" or not job.title.strip():
                # Generate a better title based on the content
                title_prompt = f"Based on this podcast conversation, generate a concise, engaging title (max 50 characters):\n\n{conversation_text[:500]}..."
                try:
                    generated_title = podcast_orchestrator.generate_title(title_prompt)
                    if generated_title and generated_title.strip():
                        job.title = generated_title.strip()[:50]  # Limit to 50 characters
                        logger.info(f"Generated title for job {job_id}: {job.title}")
                except Exception as e:
                    logger.warning(f"Failed to generate title for job {job_id}: {e}")
                    # Keep the original title if generation fails
            
            # Save conversation_text, source_metadata, and title immediately after generation (first stage)
            job.conversation_text = conversation_text
            job.source_metadata = source_metadata
            job.save()
            
            logger.info(f"Saved conversation script, source metadata, and title for job {job_id}")
            
            # Update progress to reflect completion of first stage (70% progress)
            podcast_orchestrator.update_job_progress(
                job_id, "Conversation script and title generated - preparing audio generation (70%)", "generating"
            )

            # Check if job was cancelled before audio generation
            job.refresh_from_db()
            if job.status == "cancelled":
                logger.info(f"Job {job_id} was cancelled before audio generation")
                return {"status": "cancelled", "message": "Job was cancelled"}

            podcast_orchestrator.update_job_progress(
                job_id, "Generating podcast audio (80%)", "generating"
            )

            # Generate audio file using MinIO storage
            from notebooks.utils.storage import get_minio_backend
            import tempfile
            import os
            import re
            
            # Generate audio filename using title
            # Sanitize title for filename
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', job.title)
            audio_filename = f"{safe_title}.mp3"
            
            # Create MinIO key: userId/notebook/notebookID/podcast/podcastID/title.mp3
            minio_key = f"{job.user.id}/notebook/{job.notebooks.id}/podcast/{job.id}/{audio_filename}"
            
            # Create temporary file for audio generation
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_audio_path = temp_file.name
            
            try:
                # Generate audio to temporary file
                podcast_orchestrator.generate_podcast_audio(
                    conversation_text, temp_audio_path
                )
                
                # Upload to MinIO
                minio_backend = get_minio_backend()
                with open(temp_audio_path, 'rb') as f:
                    file_content = f.read()
                    file_size = len(file_content)
                    
                    # Use MinIO client directly to upload with specific key
                    from io import BytesIO
                    content_stream = BytesIO(file_content)
                    minio_backend.client.put_object(
                        bucket_name=minio_backend.bucket_name,
                        object_name=minio_key,
                        data=content_stream,
                        length=file_size,
                        content_type="audio/mpeg"
                    )
                
                # Save MinIO key to database
                job.audio_object_key = minio_key
                
                # Store file metadata including size
                job.file_metadata = {
                    "filename": audio_filename,
                    "size": file_size,
                    "content_type": "audio/mpeg",
                    "minio_key": minio_key
                }
                job.save()
                
                # Update progress to show audio upload completed (95% progress)
                podcast_orchestrator.update_job_progress(
                    job_id, "Audio file uploaded successfully (95%)", "generating"
                )
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)

            # Prepare result
            result = {
                "job_id": job_id,
                "title": job.title,
                "description": job.description,
                "audio_url": job.get_audio_url(),
                "source_metadata": source_metadata,
                "conversation_text": conversation_text,
                "file_metadata": job.file_metadata,
            }

            # Update job with success
            podcast_orchestrator.update_job_result(job_id, result, "completed")

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
            job = PodcastJob.objects.get(id=job_id)
            if job.status != "cancelled":
                job.status = "cancelled"
                job.error_message = "Job was interrupted"
                job.progress = "Job cancelled"
                job.save()
                # Update status cache for frontend
                podcast_orchestrator.update_job_progress(job_id, "Job cancelled", "cancelled")
        except PodcastJob.DoesNotExist:
            pass
        return {"status": "cancelled", "message": "Job was cancelled"}
    except Exception as e:
        logger.error(f"Error processing podcast generation job {job_id}: {e}")
        podcast_orchestrator.update_job_error(job_id, str(e))
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
                if job.audio_object_key:
                    try:
                        from notebooks.utils.storage import get_minio_backend
                        minio_backend = get_minio_backend()
                        minio_backend.delete_file(job.audio_object_key)
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


@shared_task(bind=True)
def cancel_podcast_generation(self, job_id: str):
    """Cancel a podcast generation job"""
    try:
        logger.info(f"Cancelling podcast generation for job {job_id}")
        
        # Get the job
        job = PodcastJob.objects.get(id=job_id)
        
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
        
        # Update job status in database
        job.status = "cancelled"
        job.error_message = "Job cancelled by user"
        job.progress = "Job cancelled"
        job.save()
        
        # Update status cache for frontend
        podcast_orchestrator.update_job_progress(job_id, "Job cancelled", "cancelled")
        
        logger.info(f"Successfully cancelled podcast generation for job {job_id}")
        return {"status": "cancelled", "job_id": job_id}
    
    except PodcastJob.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        return {"status": "failed", "job_id": job_id, "message": "Job not found"}
    except Exception as e:
        logger.error(f"Error cancelling podcast generation for job {job_id}: {e}")
        raise
