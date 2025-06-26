"""
Django-compatible queue service for report generation.
Uses Django's cache system for job tracking (simplified version without django_rq).
"""

import uuid
import json
import logging
import threading
from typing import Dict, Optional, List, Any
from datetime import datetime, timezone, timedelta

from django.core.cache import cache
from django.conf import settings

from .models import Report

logger = logging.getLogger(__name__)


class ReportQueueService:
    """Queue service for managing report generation jobs in Django."""

    def __init__(self):
        self.cache_timeout = getattr(settings, "REPORT_CACHE_TIMEOUT", 3600)  # 1 hour

    def add_report_job(self, report: Report) -> str:
        """Add a report generation job to the queue."""
        try:
            # Generate unique job ID if not already set
            if not report.job_id:
                report.job_id = str(uuid.uuid4())
                report.save(update_fields=["job_id"])

            # Create job metadata for caching
            job_metadata = {
                "job_id": report.job_id,
                "report_id": report.id,
                "user_id": report.user.pk,
                "status": report.status,
                "progress": report.progress,
                "created_at": report.created_at.isoformat(),
                "updated_at": report.updated_at.isoformat(),
                "configuration": report.get_configuration_dict(),
            }

            # Store job metadata in cache
            cache_key = f"report_job:{report.job_id}"
            cache.set(cache_key, job_metadata, timeout=self.cache_timeout)

            # For now, we'll start the job directly instead of using a queue
            # In production, this should be replaced with a proper queue system
            self._start_job_thread(report.id)

            logger.info(
                f"Report generation job {report.job_id} queued successfully for report {report.id}"
            )
            return report.job_id

        except Exception as e:
            logger.error(f"Error adding report job for report {report.id}: {e}")
            report.update_status(
                Report.STATUS_FAILED, error=f"Failed to queue job: {str(e)}"
            )
            raise

    def _start_job_thread(self, report_id: int):
        """Start a background thread to process the report (temporary solution)."""

        def run_job():
            try:
                # Import here to avoid circular imports
                from .worker.report_worker import process_report_generation

                process_report_generation(report_id)
            except Exception as e:
                logger.error(f"Error in background job for report {report_id}: {e}")

        # Start the job in a separate thread
        thread = threading.Thread(target=run_job, daemon=True)
        thread.start()

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a report generation job."""
        try:
            # First try to get from Django model
            try:
                report = Report.objects.get(job_id=job_id)
                return {
                    "job_id": job_id,
                    "report_id": report.id,
                    "user_id": report.user.pk,
                    "status": report.status,
                    "progress": report.progress,
                    "created_at": report.created_at.isoformat(),
                    "updated_at": report.updated_at.isoformat(),
                    "result": self._format_result(report),
                    "error": report.error_message or None,
                }
            except Report.DoesNotExist:
                pass

            # Fallback to cache
            cache_key = f"report_job:{job_id}"
            job_data = cache.get(cache_key)

            if not job_data:
                return None

            return job_data

        except Exception as e:
            logger.error(f"Error getting job status for {job_id}: {e}")
            return None

    def update_job_progress(
        self, job_id: str, progress: str, status: Optional[str] = None
    ):
        """Update job progress and optionally status."""
        try:
            # Update in database
            try:
                report = Report.objects.get(job_id=job_id)
                if status:
                    report.update_status(status, progress=progress)
                else:
                    report.progress = progress
                    report.save(update_fields=["progress", "updated_at"])

                # Update cache
                cache_key = f"report_job:{job_id}"
                job_data = cache.get(cache_key, {})
                job_data.update(
                    {
                        "progress": progress,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                if status:
                    job_data["status"] = status
                cache.set(cache_key, job_data, timeout=self.cache_timeout)

            except Report.DoesNotExist:
                logger.warning(
                    f"Report with job_id {job_id} not found for progress update"
                )

        except Exception as e:
            logger.error(f"Error updating job progress for {job_id}: {e}")

    def update_job_result(
        self, job_id: str, result: Dict[str, Any], status: str = Report.STATUS_COMPLETED
    ):
        """Update job with final result."""
        try:
            report = Report.objects.get(job_id=job_id)

            # Store the main content
            if "report_content" in result:
                report.result_content = result["report_content"]

            # Store additional metadata
            report.result_metadata = {
                "article_title": result.get("article_title", report.article_title),
                "output_directory": result.get("output_directory", ""),
                "generated_files": result.get("generated_files", []),
                "main_report_file": result.get("main_report_file"),
                "processing_logs": result.get("processing_logs", []),
                "created_at": result.get(
                    "created_at", datetime.now(timezone.utc).isoformat()
                ),
            }

            # Update file references
            if result.get("generated_files"):
                report.generated_files = result["generated_files"]

            if result.get("processing_logs"):
                report.processing_logs = result["processing_logs"]

            # Update status
            report.update_status(
                status, progress="Report generation completed successfully"
            )

            # Update cache
            cache_key = f"report_job:{job_id}"
            job_data = cache.get(cache_key, {})
            job_data.update(
                {
                    "status": status,
                    "progress": "Report generation completed successfully",
                    "result": self._format_result(report),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            cache.set(cache_key, job_data, timeout=self.cache_timeout)

            logger.info(f"Updated job {job_id} with final result, status: {status}")

        except Report.DoesNotExist:
            logger.error(f"Report with job_id {job_id} not found for result update")
        except Exception as e:
            logger.error(f"Error updating job result for {job_id}: {e}")

    def update_job_error(self, job_id: str, error: str):
        """Update job with error information."""
        try:
            report = Report.objects.get(job_id=job_id)
            report.update_status(
                Report.STATUS_FAILED, progress=f"Job failed: {error}", error=error
            )

            # Update cache
            cache_key = f"report_job:{job_id}"
            job_data = cache.get(cache_key, {})
            job_data.update(
                {
                    "status": Report.STATUS_FAILED,
                    "progress": f"Job failed: {error}",
                    "error": error,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            cache.set(cache_key, job_data, timeout=self.cache_timeout)

            logger.error(f"Updated job {job_id} with error: {error}")

        except Report.DoesNotExist:
            logger.error(f"Report with job_id {job_id} not found for error update")
        except Exception as e:
            logger.error(f"Error updating job error for {job_id}: {e}")

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running or pending job."""
        try:
            # Update job metadata in database
            try:
                report = Report.objects.get(job_id=job_id)
                report.update_status(
                    Report.STATUS_CANCELLED, progress="Job cancelled by user"
                )

                # Update cache
                cache_key = f"report_job:{job_id}"
                job_data = cache.get(cache_key, {})
                job_data.update(
                    {
                        "status": Report.STATUS_CANCELLED,
                        "progress": "Job cancelled by user",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                cache.set(cache_key, job_data, timeout=self.cache_timeout)

                return True
            except Report.DoesNotExist:
                logger.warning(
                    f"Report with job_id {job_id} not found for cancellation"
                )
                return False

        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False

    def list_jobs(
        self, user_id: Optional[int] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List report generation jobs."""
        try:
            query = Report.objects.select_related("user").order_by("-created_at")

            if user_id:
                query = query.filter(user_id=user_id)

            reports = query[:limit]

            jobs = []
            for report in reports:
                jobs.append(
                    {
                        "job_id": report.job_id,
                        "report_id": report.id,
                        "user_id": report.user.pk,
                        "status": report.status,
                        "progress": report.progress,
                        "article_title": report.article_title,
                        "created_at": report.created_at.isoformat(),
                        "updated_at": report.updated_at.isoformat(),
                        "result": self._format_result(report)
                        if report.status == Report.STATUS_COMPLETED
                        else None,
                        "error": report.error_message or None,
                    }
                )

            return jobs

        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
            return []

    def delete_job(self, job_id: str) -> bool:
        """Delete a job and its associated data."""
        try:
            report = Report.objects.get(job_id=job_id)

            # Remove from cache
            cache_key = f"report_job:{job_id}"
            cache.delete(cache_key)

            # The report record will be deleted when the Report object is deleted
            # This is handled by the view layer

            logger.info(f"Prepared job {job_id} for deletion")
            return True

        except Report.DoesNotExist:
            logger.warning(f"Report with job_id {job_id} not found for deletion")
            return False
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {e}")
            return False

    def cleanup_old_jobs(self, days: int = 7):
        """Clean up old completed jobs."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            old_reports = Report.objects.filter(
                created_at__lt=cutoff_date,
                status__in=[
                    Report.STATUS_COMPLETED,
                    Report.STATUS_FAILED,
                    Report.STATUS_CANCELLED,
                ],
            )

            count = 0
            for report in old_reports:
                # Clean up cache
                if report.job_id:
                    cache_key = f"report_job:{report.job_id}"
                    cache.delete(cache_key)

                # The actual report deletion would be handled by a separate process
                # to avoid accidentally deleting important data
                count += 1

            logger.info(f"Cleaned up {count} old report job cache entries")

        except Exception as e:
            logger.error(f"Error cleaning up old jobs: {e}")

    def _format_result(self, report: Report) -> Optional[Dict[str, Any]]:
        """Format the result data for API responses."""
        if report.status != Report.STATUS_COMPLETED or not report.result_metadata:
            return None

        result = report.result_metadata.copy()
        if report.result_content:
            result["report_content"] = report.result_content

        return result


# Global singleton instance
report_queue_service = ReportQueueService()
