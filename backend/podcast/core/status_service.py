"""
Status management service following SOLID principles.
"""

import json
import logging
from typing import Dict, Optional
from ..models import PodcastJob
from ..config.podcast_config import podcast_config

logger = logging.getLogger(__name__)


class StatusService:
    """Service responsible for managing job status and caching"""
    
    def __init__(self):
        self._redis_client = None
        self.config = podcast_config.get_redis_config()
    
    @property
    def redis_client(self):
        """Lazy initialization of Redis client"""
        if self._redis_client is None:
            try:
                import redis
                self._redis_client = redis.Redis.from_url(self.config['url'])
                # Test connection
                self._redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed, caching disabled: {e}")
                self._redis_client = None
        return self._redis_client
    
    def update_job_progress(
        self, 
        job_id: str, 
        progress: str, 
        status: Optional[str] = None
    ):
        """Update job progress and optionally status"""
        try:
            job = PodcastJob.objects.get(id=job_id)
            job.progress = progress
            if status:
                job.status = status
            job.save()
            
            # Cache status for SSE streaming
            status_data = {
                "job_id": str(job.id),
                "status": job.status,
                "progress": job.progress,
                "error_message": job.error_message,
                "audio_file_url": job.get_audio_url(),
                "title": job.title,
            }
            self._cache_job_status(job_id, status_data)
            
            logger.debug(f"Updated podcast job {job_id} progress: {progress}")
            
        except PodcastJob.DoesNotExist:
            logger.error(f"Job {job_id} not found")
        except Exception as e:
            logger.error(f"Error updating job progress for {job_id}: {e}")
    
    def _cache_job_status(self, job_id: str, status_data: Dict):
        """Cache job status in Redis for SSE streaming"""
        if not self.redis_client:
            return  # Redis not available, skip caching
        
        try:
            cache_key = f"podcast_job_status:{job_id}"
            ttl = self.config['status_ttl']
            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(status_data),
            )
        except Exception as e:
            logger.warning(f"Failed to cache job status for {job_id}: {e}")
    
    def get_cached_status(self, job_id: str) -> Optional[Dict]:
        """Get cached job status from Redis"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = f"podcast_job_status:{job_id}"
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data.decode("utf-8"))
        except Exception as e:
            logger.warning(f"Failed to get cached status for {job_id}: {e}")
        
        return None
    
    def clear_cached_status(self, job_id: str):
        """Clear cached job status"""
        if not self.redis_client:
            return
        
        try:
            cache_key = f"podcast_job_status:{job_id}"
            self.redis_client.delete(cache_key)
        except Exception as e:
            logger.warning(f"Failed to clear cached status for {job_id}: {e}")