"""
Job management service following SOLID principles.
"""

import uuid
import json
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from django.core.cache import cache
from django.conf import settings
from ..models import Report
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class JobService:
    """Service responsible for managing report generation jobs"""
    
    def __init__(self):
        self.cache_timeout = getattr(settings, "REPORT_CACHE_TIMEOUT", 3600)  # 1 hour
    
    def create_job(self, report_data: Dict[str, Any], user=None, notebook=None) -> Report:
        """Create a new report generation job"""
        try:
            # Handle figure_data parameter separately
            figure_data = report_data.pop('figure_data', None)
            
            # Ensure CharField fields with blank=True are empty strings, not None
            # since these fields are CharField(blank=True) but not null=True
            string_fields = ["topic", "csv_session_code", "csv_date_filter"]
            for field in string_fields:
                if field not in report_data or report_data.get(field) is None:
                    report_data[field] = ""
            
            job_data = {
                "user": user,
                "status": Report.STATUS_PENDING,
                "progress": "Report generation job has been queued",
                **report_data,
            }
            
            if notebook:
                job_data["notebooks"] = notebook
            
            # Create the report
            report = Report.objects.create(**job_data)
            
            # Generate unique job ID
            report.job_id = str(uuid.uuid4())
            
            # Handle figure_data if provided
            if figure_data:
                from .figure_service import FigureDataService
                figure_data_path = FigureDataService.create_knowledge_base_figure_data(
                    user.pk, f"direct_{report.id}", figure_data
                )
                if figure_data_path:
                    report.figure_data_path = figure_data_path
            
            report.save(update_fields=["job_id", "figure_data_path"])
            
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
            
            logger.info(f"Created report job {report.job_id} for report {report.id}")
            return report
            
        except Exception as e:
            logger.error(f"Error creating report job: {e}")
            raise
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a report generation job"""
        try:
            # First try to get from Django model
            try:
                report = Report.objects.get(job_id=job_id)
                job_data = {
                    "job_id": job_id,
                    "report_id": report.id,
                    "user_id": report.user.pk,
                    "status": report.status,
                    "progress": report.progress,
                    "created_at": report.created_at.isoformat(),
                    "updated_at": report.updated_at.isoformat(),
                    "error": report.error_message or None,
                }
                result = self._format_result(report)
                if result:
                    job_data.update(result)
                return job_data
            except Report.DoesNotExist:
                pass
            
            # Fallback to cache
            cache_key = f"report_job:{job_id}"
            job_data = cache.get(cache_key)
            return job_data
            
        except Exception as e:
            logger.error(f"Error getting job status for {job_id}: {e}")
            return None
    
    def update_job_progress(self, job_id: str, progress: str, status: Optional[str] = None):
        """Update job progress and optionally status"""
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
                job_data.update({
                    "progress": progress,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                if status:
                    job_data["status"] = status
                cache.set(cache_key, job_data, timeout=self.cache_timeout)
                
            except Report.DoesNotExist:
                logger.warning(f"Report with job_id {job_id} not found for progress update")
                
        except Exception as e:
            logger.error(f"Error updating job progress for {job_id}: {e}")
    

    def update_job_result(self, job_id: str, result: Dict[str, Any], status: str = Report.STATUS_COMPLETED):
        """Update job with final result"""
        try:
            report = Report.objects.get(job_id=job_id)
            
            # Store the main content (prefer processed content from result data)
            if "report_content" in result and result["report_content"]:
                # Use the processed content from the report generator
                report.result_content = result["report_content"]
                logger.info("Stored processed report content from result data")
                
                # Save the processed content to Django FileField
                try:
                    filename = f"report_{report.id}.md"
                    report.main_report_file.save(
                        filename, 
                        ContentFile(result["report_content"].encode('utf-8')), 
                        save=False
                    )
                    logger.info(f"Saved main_report_file: {report.main_report_file.name}")
                except Exception as e:
                    logger.warning(f"Could not save main_report_file: {e}")
            else:
                logger.warning("No processed report content found in result data")
            
            # Update article_title with generated title from polishing
            if "article_title" in result and result["article_title"] != report.article_title:
                report.article_title = result["article_title"]
                logger.info(f"Updated article_title from GenerateOverallTitle: {result['article_title']}")
            
            # Update topic with improved/generated topic if available
            if "generated_topic" in result and result["generated_topic"] and result["generated_topic"] != report.topic:
                report.topic = result["generated_topic"]
                logger.info(f"Updated topic from STORM generation: {result['generated_topic']}")
            
            # Store additional metadata
            metadata = {
                "output_directory": result.get("output_directory", ""),
                "generated_files": result.get("generated_files", []),
                "processing_logs": result.get("processing_logs", []),
                "created_at": result.get("created_at", datetime.now(timezone.utc).isoformat()),
            }
            
            # Add main_report_file path to metadata if saved
            if report.main_report_file:
                metadata["main_report_file"] = report.main_report_file.name
                logger.info(f"Stored main_report_file path in metadata: {report.main_report_file.name}")
            
            report.result_metadata = metadata
            
            # Store generated files (no need to filter since we no longer create duplicate files)
            if result.get("generated_files"):
                report.generated_files = result["generated_files"]
            
            if result.get("processing_logs"):
                report.processing_logs = result["processing_logs"]
            
            # Save all changes to database including result_content, result_metadata, article_title, topic, and main_report_file
            report.save(update_fields=["result_content", "result_metadata", "article_title", "topic", "generated_files", "processing_logs", "main_report_file", "updated_at"])
            
            # Update status after saving content and metadata
            report.update_status(status, progress="Report generation completed successfully")
            
            # Update cache
            cache_key = f"report_job:{job_id}"
            job_data = cache.get(cache_key, {})
            job_data.update({
                "status": status,
                "progress": "Report generation completed successfully",
                "result": self._format_result(report),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            cache.set(cache_key, job_data, timeout=self.cache_timeout)
            
            logger.info(f"Updated job {job_id} with final result, status: {status}")
            
        except Report.DoesNotExist:
            logger.error(f"Report with job_id {job_id} not found for result update")
        except Exception as e:
            logger.error(f"Error updating job result for {job_id}: {e}")
    
    def update_job_error(self, job_id: str, error: str):
        """Update job with error information"""
        try:
            report = Report.objects.get(job_id=job_id)
            report.update_status(
                Report.STATUS_FAILED, 
                progress=f"Job failed: {error}", 
                error=error
            )
            
            # Update cache
            cache_key = f"report_job:{job_id}"
            job_data = cache.get(cache_key, {})
            job_data.update({
                "status": Report.STATUS_FAILED,
                "progress": f"Job failed: {error}",
                "error": error,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            cache.set(cache_key, job_data, timeout=self.cache_timeout)
            
            logger.error(f"Updated job {job_id} with error: {error}")
            
        except Report.DoesNotExist:
            logger.error(f"Report with job_id {job_id} not found for error update")
        except Exception as e:
            logger.error(f"Error updating job error for {job_id}: {e}")
    
    def cancel_job(self, job_id: str) -> bool:
        """Dispatch a task to cancel a running or pending job."""
        try:
            report = Report.objects.get(job_id=job_id)

            # Check if job is in a cancellable state
            if report.status not in [Report.STATUS_PENDING, Report.STATUS_RUNNING]:
                logger.warning(f"Report job {job_id} is not in a cancellable state (status: {report.status})")
                return False

            # Dispatch the cancellation task
            from ..tasks import cancel_report_generation
            cancel_report_generation.delay(job_id)
            
            logger.info(f"Cancellation task queued for report job {job_id}")
            return True
            
        except Report.DoesNotExist:
            logger.warning(f"Report with job_id {job_id} not found for cancellation")
            return False
        except Exception as e:
            logger.error(f"Error dispatching cancellation for job {job_id}: {e}")
            return False
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job and its associated data"""
        try:
            report = Report.objects.get(job_id=job_id)
            
            # Remove from cache
            cache_key = f"report_job:{job_id}"
            cache.delete(cache_key)
            
            logger.info(f"Prepared job {job_id} for deletion")
            return True
            
        except Report.DoesNotExist:
            logger.warning(f"Report with job_id {job_id} not found for deletion")
            return False
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {e}")
            return False
    
    def list_jobs(self, user_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List report generation jobs"""
        try:
            query = Report.objects.select_related("user").order_by("-created_at")
            
            if user_id:
                query = query.filter(user_id=user_id)
            
            reports = query[:limit]
            
            jobs = []
            for report in reports:
                jobs.append({
                    "job_id": report.job_id,
                    "report_id": report.id,
                    "user_id": report.user.pk,
                    "status": report.status,
                    "progress": report.progress,
                    "created_at": report.created_at.isoformat(),
                    "updated_at": report.updated_at.isoformat(),
                    "result": self._format_result(report) if report.status == Report.STATUS_COMPLETED else None,
                    "error": report.error_message or None,
                })
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
            return []
    
    def cleanup_old_jobs(self, days: int = 7):
        """Clean up old completed jobs"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            old_reports = Report.objects.filter(
                created_at__lt=cutoff_date,
                status__in=[Report.STATUS_COMPLETED, Report.STATUS_FAILED, Report.STATUS_CANCELLED],
            )
            
            count = 0
            for report in old_reports:
                # Clean up cache
                if report.job_id:
                    cache_key = f"report_job:{report.job_id}"
                    cache.delete(cache_key)
                count += 1
            
            logger.info(f"Cleaned up {count} old report job cache entries")
            
        except Exception as e:
            logger.error(f"Error cleaning up old jobs: {e}")
    
    def _format_result(self, report: Report) -> Optional[Dict[str, Any]]:
        """Format the result data for API responses"""
        if report.status != Report.STATUS_COMPLETED or not report.result_metadata:
            return None
        
        result = report.result_metadata.copy()
        if report.result_content:
            result["report_content"] = report.result_content
        
        return result