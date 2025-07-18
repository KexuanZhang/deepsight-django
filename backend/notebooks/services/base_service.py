"""
Base service classes providing common functionality for all services.
"""

import uuid
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
from datetime import datetime, UTC
from pathlib import Path

try:
    from redis import Redis
    from rq import Queue

    redis_available = True
except ImportError:
    Redis = None
    Queue = None
    redis_available = False

try:
    from ..utils.helpers import config as settings
except ImportError:
    settings = None


class BaseService(ABC):
    """
    Abstract base service class providing common functionality.

    This class establishes patterns for:
    - Logging
    - Data directory management
    - Configuration access
    - Error handling
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # Create service-specific data directory
        if settings and hasattr(settings, "PROJECT_ROOT"):
            self.data_dir = Path(settings.PROJECT_ROOT) / "data" / service_name
            self.data_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Fallback to a default data directory
            import tempfile

            self.data_dir = (
                Path(tempfile.gettempdir()) / "deepsight_data" / service_name
            )
            self.data_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"{service_name} service initialized")

    def generate_id(self) -> str:
        """Generate a unique ID for service operations."""
        return str(uuid.uuid4())

    def get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(UTC).isoformat()

    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log service operations with consistent formatting."""
        message = f"[{self.service_name}] {operation}"
        if details:
            message += f": {details}"

        getattr(self.logger, level)(message)


class BaseQueueService(BaseService):
    """
    Base service class for services that use Redis queue functionality.

    Provides:
    - Redis connection management
    - Queue setup
    - Job metadata handling
    - Common queue operations
    """

    def __init__(self, service_name: str, queue_name: str):
        super().__init__(service_name)

        if not redis_available or not settings:
            self.logger.warning(f"Redis/RQ not available for {service_name}")
            self.redis_client = None
            self.queue = None
            self.queue_name = queue_name
            self.job_metadata_key = f"{service_name}_metadata"
            return

        try:
            # Redis connection (without string decoding for RQ compatibility)
            self.redis_client = Redis.from_url(
                settings.redis_url, decode_responses=False
            )

            # RQ Queue
            self.queue = Queue(queue_name, connection=self.redis_client)
            self.queue_name = queue_name

            # Job metadata storage key
            self.job_metadata_key = f"{service_name}_metadata"

            self.logger.info(
                f"Queue service {service_name} initialized with queue: {queue_name}"
            )
        except Exception as e:
            self.logger.warning(f"Failed to initialize Redis for {service_name}: {e}")
            self.redis_client = None
            self.queue = None
            self.queue_name = queue_name
            self.job_metadata_key = f"{service_name}_metadata"

    def _decode_redis_hash(self, data: Dict) -> Dict[str, str]:
        """Decode Redis hash data from bytes to strings."""
        if not data:
            return {}

        decoded = {}
        for key, value in data.items():
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            decoded[key] = value
        return decoded

    def store_job_metadata(self, job_id: str, metadata: Dict[str, Any]) -> None:
        """Store job metadata in Redis."""
        if not self.redis_client:
            self.log_operation(
                "store_metadata_skipped", f"Redis not available for job_id={job_id}"
            )
            return

        try:
            # Ensure all values are strings for Redis storage
            redis_data = {}
            for key, value in metadata.items():
                if isinstance(value, dict) or isinstance(value, list):
                    import json

                    redis_data[key] = json.dumps(value)
                else:
                    redis_data[key] = str(value)

            self.redis_client.hset(
                f"{self.job_metadata_key}:{job_id}", mapping=redis_data
            )
            self.log_operation("store_metadata", f"job_id={job_id}")

        except Exception as e:
            self.log_operation("store_metadata_error", str(e), "error")
            raise

    def get_job_metadata(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job metadata from Redis."""
        if not self.redis_client:
            return None

        try:
            raw_data = self.redis_client.hgetall(f"{self.job_metadata_key}:{job_id}")
            if not raw_data:
                return None

            decoded_data = self._decode_redis_hash(raw_data)

            # Try to parse JSON strings back to objects
            for key, value in decoded_data.items():
                if key in ["request", "result", "metadata"] and value:
                    try:
                        import json

                        decoded_data[key] = json.loads(value)
                    except json.JSONDecodeError:
                        pass  # Keep as string if not valid JSON

            return decoded_data

        except Exception as e:
            self.log_operation("get_metadata_error", str(e), "error")
            return None

    def update_job_progress(
        self,
        job_id: str,
        progress: str,
        status: Optional[str] = None,
        percentage: Optional[int] = None,
    ):
        """Update job progress in Redis."""
        if not self.redis_client:
            return

        try:
            update_data = {"progress": progress, "updated_at": self.get_timestamp()}

            if status:
                update_data["status"] = status

            if percentage is not None:
                update_data["progress_percentage"] = str(percentage)

            self.redis_client.hset(
                f"{self.job_metadata_key}:{job_id}", mapping=update_data
            )

            # Publish status update to Redis pub/sub for real-time updates
            if status:
                self._publish_status_update(
                    job_id,
                    {
                        "status": status,
                        "progress": progress,
                        "progress_percentage": percentage,
                        "updated_at": update_data["updated_at"],
                    },
                )

            self.log_operation(
                "update_progress", f"job_id={job_id}, progress={progress}"
            )

        except Exception as e:
            self.log_operation("update_progress_error", str(e), "error")
            raise

    def update_job_result(
        self, job_id: str, result: Dict[str, Any], status: str = "completed"
    ):
        """Update job with final result."""
        if not self.redis_client:
            return

        try:
            import json

            update_data = {
                "status": status,
                "result": json.dumps(result)
                if isinstance(result, dict)
                else str(result),
                "updated_at": self.get_timestamp(),
            }

            self.redis_client.hset(
                f"{self.job_metadata_key}:{job_id}", mapping=update_data
            )

            # Publish final status update
            self._publish_status_update(
                job_id,
                {
                    "status": status,
                    "result": result,
                    "updated_at": update_data["updated_at"],
                },
            )

            self.log_operation("update_result", f"job_id={job_id}, status={status}")

        except Exception as e:
            self.log_operation("update_result_error", str(e), "error")
            raise

    def update_job_error(self, job_id: str, error: str):
        """Update job with error information."""
        if not self.redis_client:
            return

        try:
            update_data = {
                "status": "error",
                "error": error,
                "progress": f"Job failed: {error}",
                "updated_at": self.get_timestamp(),
            }

            self.redis_client.hset(
                f"{self.job_metadata_key}:{job_id}", mapping=update_data
            )

            # Publish error status update
            self._publish_status_update(
                job_id,
                {
                    "status": "error",
                    "error": error,
                    "progress": f"Job failed: {error}",
                    "updated_at": update_data["updated_at"],
                },
            )

            self.log_operation(
                "update_error", f"job_id={job_id}, error={error[:100]}", "error"
            )

        except Exception as e:
            self.log_operation("update_error_failed", str(e), "error")
            raise

    def _publish_status_update(self, job_id: str, status_data: Dict[str, Any]):
        """Publish status update to Redis pub/sub for real-time notifications."""
        if not self.redis_client:
            return

        try:
            import json

            channel_name = f"file_parsing_status:{job_id}"
            message = json.dumps(status_data)
            self.redis_client.publish(channel_name, message)
            self.log_operation(
                "publish_status", f"job_id={job_id}, channel={channel_name}"
            )
        except Exception as e:
            self.log_operation(
                "publish_status_error", f"job_id={job_id}, error={str(e)}", "error"
            )
            # Don't raise here to avoid breaking the main flow

    def delete_job_metadata(self, job_id: str) -> bool:
        """Delete job metadata from Redis."""
        if not self.redis_client:
            return False

        try:
            result = self.redis_client.delete(f"{self.job_metadata_key}:{job_id}")
            self.log_operation("delete_metadata", f"job_id={job_id}")
            return bool(result)

        except Exception as e:
            self.log_operation("delete_metadata_error", str(e), "error")
            return False

    def list_jobs(self, pattern: str = "*", limit: int = 50) -> List[Dict[str, Any]]:
        """List jobs matching pattern."""
        try:
            keys = self.redis_client.keys(f"{self.job_metadata_key}:{pattern}")
            jobs = []

            for key in keys[:limit]:
                job_id = key.decode("utf-8").split(":")[-1]
                metadata = self.get_job_metadata(job_id)
                if metadata:
                    jobs.append(metadata)

            self.log_operation("list_jobs", f"found {len(jobs)} jobs")
            return jobs

        except Exception as e:
            self.log_operation("list_jobs_error", str(e), "error")
            return []

    def cleanup_old_jobs(self, days_old: int = 7) -> int:
        """Clean up old job metadata."""
        try:
            from datetime import timedelta

            cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

            keys = self.redis_client.keys(f"{self.job_metadata_key}:*")
            cleaned_count = 0

            for key in keys:
                job_id = key.decode("utf-8").split(":")[-1]
                metadata = self.get_job_metadata(job_id)

                if metadata and metadata.get("created_at"):
                    try:
                        created_at = datetime.fromisoformat(
                            metadata["created_at"].replace("Z", "+00:00")
                        )
                        if created_at < cutoff_date:
                            self.delete_job_metadata(job_id)
                            cleaned_count += 1
                    except ValueError:
                        # Invalid date format, skip
                        continue

            self.log_operation("cleanup_jobs", f"cleaned {cleaned_count} old jobs")
            return cleaned_count

        except Exception as e:
            self.log_operation("cleanup_jobs_error", str(e), "error")
            return 0
