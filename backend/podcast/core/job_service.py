"""
Job management service following SOLID principles.
"""

import logging
from typing import Dict, List, Optional, Any
from django.core.files.base import ContentFile
from ..models import PodcastJob

logger = logging.getLogger(__name__)


class JobService:
    """Service responsible for managing podcast generation jobs"""
    
    def create_job(
        self, 
        source_file_ids: List[str], 
        job_metadata: Dict, 
        user=None, 
        notebook=None
    ) -> PodcastJob:
        """Create a new podcast generation job"""
        try:
            job_data = {
                "user": user,
                "title": job_metadata.get("title", "Generated Podcast"),
                "description": job_metadata.get("description", ""),
            }
            
            if notebook:
                job_data["notebooks"] = notebook
                
            job_data.update({
                "source_file_ids": source_file_ids,
                "source_metadata": job_metadata.get("source_metadata", {}),
                "status": "pending",
                "progress": "Job queued for processing",
            })
            
            job = PodcastJob.objects.create(**job_data)
            
            logger.info(
                f"Created podcast job {job.job_id} with {len(source_file_ids)} source files"
            )
            return job
            
        except Exception as e:
            logger.error(f"Error creating podcast job: {e}")
            raise
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get the status of a podcast generation job"""
        try:
            job = PodcastJob.objects.get(job_id=job_id)
            return {
                "job_id": str(job.job_id),
                "status": job.status,
                "progress": job.progress,
                "title": job.title,
                "description": job.description,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "source_file_ids": job.source_file_ids,
                "source_metadata": job.source_metadata,
                "audio_url": job.audio_url,
                "conversation_text": job.conversation_text,
                "error_message": job.error_message if job.error_message else None,
                "duration_seconds": job.duration_seconds,
                "result": job.get_result_dict() if job.status == "completed" else None,
            }
            
        except PodcastJob.DoesNotExist:
            logger.error(f"Job {job_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting job status for {job_id}: {e}")
            return None
    
    def update_job_result(self, job_id: str, result: Dict, status: str = "completed"):
        """Update job with final result"""
        try:
            job = PodcastJob.objects.get(job_id=job_id)
            job.status = status
            
            if status == "completed":
                job.progress = "Podcast generation completed successfully"
                if "conversation_text" in result:
                    job.conversation_text = result["conversation_text"]
                if "source_metadata" in result:
                    job.source_metadata = result["source_metadata"]
            
            job.save()
            
            logger.info(
                f"Updated podcast job {job_id} with final result, status: {status}"
            )
            
        except PodcastJob.DoesNotExist:
            logger.error(f"Job {job_id} not found")
        except Exception as e:
            logger.error(f"Error updating job result for {job_id}: {e}")
    
    def update_job_error(self, job_id: str, error: str):
        """Update job with error information"""
        try:
            job = PodcastJob.objects.get(job_id=job_id)
            job.status = "error"
            job.error_message = error
            job.progress = f"Job failed: {error}"
            job.save()
            
            logger.error(f"Updated podcast job {job_id} with error: {error}")
            
        except PodcastJob.DoesNotExist:
            logger.error(f"Job {job_id} not found")
        except Exception as e:
            logger.error(f"Error updating job error for {job_id}: {e}")
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a podcast generation job"""
        try:
            job = PodcastJob.objects.get(job_id=job_id)
            
            if job.status in ["pending", "generating"]:
                # Queue the cancellation task (same pattern as reports)
                from ..tasks import cancel_podcast_generation
                cancel_podcast_generation.delay(job_id)
                
                logger.info(f"Queued cancellation task for job {job_id}")
                return True
            else:
                logger.warning(f"Cannot cancel job {job_id}, status: {job.status}")
                return False
                
        except PodcastJob.DoesNotExist:
            logger.error(f"Job {job_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a podcast generation job and its associated files"""
        try:
            job = PodcastJob.objects.get(job_id=job_id)
            
            # Delete associated audio file if it exists
            if job.audio_file:
                job.audio_file.delete(save=False)
            
            # Delete the job
            job.delete()
            
            logger.info(f"Deleted podcast job {job_id}")
            return True
            
        except PodcastJob.DoesNotExist:
            logger.error(f"Job {job_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error deleting podcast job {job_id}: {e}")
            return False
    
    def list_jobs(self, user=None, limit: int = 50) -> List[Dict[str, Any]]:
        """List podcast generation jobs"""
        try:
            queryset = PodcastJob.objects.all()
            if user:
                queryset = queryset.filter(user=user)
            
            jobs = queryset[:limit]
            
            result = []
            for job in jobs:
                job_data = {
                    "job_id": str(job.job_id),
                    "title": job.title,
                    "description": job.description,
                    "status": job.status,
                    "progress": job.progress,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                    "source_file_ids": job.source_file_ids,
                    "source_metadata": job.source_metadata,
                    "audio_url": job.audio_url,
                    "error_message": job.error_message if job.error_message else None,
                    "duration_seconds": job.duration_seconds,
                }
                result.append(job_data)
            
            logger.info(f"Listed {len(result)} podcast jobs")
            return result
            
        except Exception as e:
            logger.error(f"Error listing podcast jobs: {e}")
            return []