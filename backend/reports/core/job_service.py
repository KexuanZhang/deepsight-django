"""
Job management service following SOLID principles.
"""

import uuid
import json
import logging
import os
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from django.core.cache import cache
from django.conf import settings
from ..models import Report
from django.core.files.base import ContentFile
from celery.result import AsyncResult

logger = logging.getLogger(__name__)


class CriticalErrorDetector:
    """Detects critical error patterns that should cause task failure"""
    
    # Pattern to detect Celery ERROR messages from MainProcess only - these are critical
    # Format: [yyyy-mm-dd hh:mm:ss,xxx: ERROR/MainProcess] ...
    MAIN_PROCESS_ERROR_PATTERN = re.compile(
        r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}: ERROR/MainProcess\]',
        re.IGNORECASE
    )
    
    # Pattern to detect any Celery ERROR message (for display purposes)
    # Format: [yyyy-mm-dd hh:mm:ss,xxx: ERROR/ProcessName] ...
    ANY_ERROR_PATTERN = re.compile(
        r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}: ERROR/[^\]]+\]',
        re.IGNORECASE
    )
    
    def __init__(self, max_main_process_errors: int = 1):  # Only 1 MainProcess error should fail the task
        self.max_main_process_errors = max_main_process_errors
        self.main_process_error_counts = {}
    
    def should_fail_task(self, job_id: str, log_message: str) -> bool:
        """Check if log message contains MainProcess critical errors and if task should fail"""
        
        # Check if this is a MainProcess ERROR message (critical)
        if self.MAIN_PROCESS_ERROR_PATTERN.search(log_message):
            # Initialize counter for this job if not exists
            if job_id not in self.main_process_error_counts:
                self.main_process_error_counts[job_id] = 0
            
            # Increment error count
            self.main_process_error_counts[job_id] += 1
            
            logger.error(f"MainProcess ERROR detected for job {job_id} (count: {self.main_process_error_counts[job_id]}): {log_message[:200]}")
            
            # Check if we've exceeded the threshold
            if self.main_process_error_counts[job_id] >= self.max_main_process_errors:
                logger.error(f"Job {job_id} exceeded maximum MainProcess errors ({self.max_main_process_errors}), failing task")
                return True
        
        return False
    
    def is_error_message(self, log_message: str) -> bool:
        """Check if message is any Celery ERROR (for display in SSE without failing task)"""
        return bool(self.ANY_ERROR_PATTERN.search(log_message))
    
    def reset_job_errors(self, job_id: str):
        """Reset error count for a job"""
        self.main_process_error_counts.pop(job_id, None)


class JobService:
    """Service responsible for managing report generation jobs"""
    
    def __init__(self):
        self.cache_timeout = getattr(settings, "REPORT_CACHE_TIMEOUT", 3600)  # 1 hour
        self.error_detector = CriticalErrorDetector(max_main_process_errors=1)  # Only 1 MainProcess error should fail the task
    
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
            
            # Generate unique job ID first
            job_id = str(uuid.uuid4())
            
            job_data = {
                "user": user,
                "status": Report.STATUS_PENDING,
                "progress": "Report generation job has been queued",
                "job_id": job_id,  # Set job_id during creation
                **report_data,
            }
            
            if notebook:
                job_data["notebooks"] = notebook
            
            # Create the report with job_id already set
            report = Report.objects.create(**job_data)
            
            # Handle figure_data if provided
            if figure_data:
                from .figure_service import FigureDataService
                # Create knowledge base figure data for direct upload
                # This will store the figure data in the report's cached data
                FigureDataService.create_knowledge_base_figure_data(
                    user.pk, f"direct_{report.id}", figure_data
                )
            
            # Create job metadata for caching
            job_metadata = {
                "job_id": report.job_id,
                "report_id": str(report.id),  # Convert UUID to string for JSON serialization
                "user_id": str(report.user.pk),  # Convert UUID to string for JSON serialization
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
                
                # Always try to synchronise the database status with the underlying Celery task
                # so that errors such as `FAILURE`, `REVOKED`, or worker crashes are surfaced to
                # API consumers immediately instead of waiting for the periodic 30-minute
                # stale-check in `_check_worker_crash`.
                self._sync_report_status_with_celery_state(report)
                
                # Check for worker crashes if job is running
                if report.status == Report.STATUS_RUNNING:
                    crash_info = self._check_worker_crash(report)
                    if crash_info['crashed']:
                        # Update report status to failed with actual error message
                        error_msg = crash_info.get('error_message', 'Celery worker crashed (SIGSEGV or similar fatal error)')
                        progress_msg = crash_info.get('progress_message', 'Worker crashed during report generation')
                        
                        report.update_status(
                            Report.STATUS_FAILED,
                            progress=progress_msg,
                            error=error_msg
                        )
                        logger.error(f"Detected worker crash for job {job_id}: {error_msg}")
                
                job_data = {
                    "job_id": job_id,
                    "report_id": str(report.id),  # Convert UUID to string for JSON serialization
                    "user_id": str(report.user.pk),  # Convert UUID to string for JSON serialization
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
            # Check if the progress message contains MainProcess critical errors that should fail the task
            if self.error_detector.should_fail_task(job_id, progress):
                # Force fail the task due to MainProcess critical errors
                self.update_job_error(job_id, f"Task failed due to MainProcess critical error: {progress[:200]}")
                return
            
            # For non-MainProcess ERROR messages, just log them but continue processing
            if self.error_detector.is_error_message(progress):
                logger.warning(f"Non-critical ERROR message for job {job_id}: {progress[:200]}")
            
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
            # Clean up error detector for this job since it's completing
            self.error_detector.reset_job_errors(job_id)
            
            report = Report.objects.get(job_id=job_id)
            
            # Store the main content (prefer processed content from result data)
            if "report_content" in result and result["report_content"]:
                # Use the processed content from the report generator
                content = result["report_content"]
                
                # Update image URLs in content if include_image is enabled
                # Note: ReportImage records should already exist from prepare_report_images
                if report.include_image:
                    try:
                        from .report_image_service import ReportImageService
                        image_service = ReportImageService()
                        
                        # Get existing ReportImage records and update content with proper URLs
                        from ..models import ReportImage
                        report_images = list(ReportImage.objects.filter(report=report))
                        
                        if report_images:
                            # Update content with proper image tags using existing ReportImage records
                            content = image_service.insert_figure_images(content, report_images, report.id)
                            logger.info(f"Updated content with {len(report_images)} existing images for report {report.id}")
                        else:
                            logger.info(f"No existing ReportImage records found for report {report.id}")
                            
                    except Exception as e:
                        logger.error(f"Error updating image URLs in content: {e}")
                        # Continue without failing the report generation
                
                report.result_content = content

            # Handle file storage - upload generated files to MinIO if using MinIO storage
            generated_files = result.get("generated_files", [])
            
            # Upload files to MinIO if there are generated files
            if generated_files:
                try:
                    from ..factories.storage_factory import StorageFactory
                    storage = StorageFactory.create_storage('minio')
                    
                    # Upload files to MinIO and get MinIO keys
                    minio_keys = storage.store_generated_files(
                        generated_files, 
                        report.user.id, 
                        str(report.id), 
                        report.notebooks.id if report.notebooks else None
                    )
                    
                    # Update generated_files with MinIO keys
                    generated_files = minio_keys
                    
                    # Clean up the temporary directory
                    import shutil
                    import os
                    if result.get("generated_files"):
                        # Get temp directory from the first generated file
                        first_file = result["generated_files"][0]
                        temp_dir = os.path.dirname(first_file)
                        
                        # Only clean up if it's a temp directory (contains report_ prefix)
                        if temp_dir and os.path.exists(temp_dir) and 'report_' in os.path.basename(temp_dir):
                            shutil.rmtree(temp_dir)
                            logger.info(f"Cleaned up temporary directory: {temp_dir}")
                        else:
                            logger.info(f"Skipped cleanup of non-temp directory: {temp_dir}")
                    else:
                        logger.info("No generated files to determine temp directory for cleanup")
                        
                except Exception as e:
                    logger.error(f"Failed to upload files to MinIO: {e}")
                    # Continue without failing the job
            
            # Set main report object key from generated files (now MinIO keys)
            if generated_files:
                # Use storage factory to identify main report file
                try:
                    from ..factories.storage_factory import StorageFactory
                    storage = StorageFactory.create_storage('minio')
                    main_report_key = storage.get_main_report_file(generated_files)
                except Exception as e:
                    logger.warning(f"Failed to identify main report file using storage factory: {e}")
                    # Fallback to manual identification
                    main_report_key = None
                    for file_path in generated_files:
                        filename = os.path.basename(file_path)
                        if filename.startswith(f"report_{report.id}") and filename.endswith(".md"):
                            main_report_key = file_path
                            break
                        elif "polished" in filename.lower() and filename.endswith(".md"):
                            main_report_key = file_path
                            break
                        elif filename.endswith(".md"):
                            main_report_key = file_path  # Fallback to any .md file
                
                if main_report_key:
                    # For MinIO storage, this is already a MinIO key
                    # For local storage, this would be a file path
                    if main_report_key.startswith(('minio://', str(report.user.id))):
                        report.main_report_object_key = main_report_key
                        logger.info(f"Set main report object key: {main_report_key}")
                    else:
                        # This is a local file path, need to handle differently
                        logger.warning(f"Main report appears to be local file: {main_report_key}")
                        
                # Update file metadata with generated files info
                report.file_metadata = {
                    "generated_files_count": len(generated_files),
                    "generated_files": generated_files[:10],  # Store first 10 files to avoid huge metadata
                    "main_report_object_key": report.main_report_object_key
                }
               
            # Fallback: Save processed report content directly to MinIO if no generated files
            elif "report_content" in result and result["report_content"]:
                try:
                    from notebooks.utils.storage import get_minio_backend
                    import io
                    
                    filename = f"report_{report.id}.md"
                    # Generate MinIO key: userId/notebook/notebookID/report/reportID/filename
                    minio_key = f"{report.user.id}/notebook/{report.notebooks.id if report.notebooks else 'standalone'}/report/{report.id}/{filename}"
                    
                    # Upload to MinIO
                    content_bytes = result["report_content"].encode('utf-8')
                    content_stream = io.BytesIO(content_bytes)
                    file_size = len(content_bytes)
                    
                    minio_backend = get_minio_backend()
                    minio_backend.client.put_object(
                        bucket_name=minio_backend.bucket_name,
                        object_name=minio_key,
                        data=content_stream,
                        length=file_size,
                        content_type="text/markdown"
                    )
                    
                    # Save MinIO key and metadata to database
                    report.main_report_object_key = minio_key
                    report.file_metadata = {
                        "main_report_filename": filename,
                        "main_report_size": file_size,
                        "main_report_content_type": "text/markdown",
                        "main_report_minio_key": minio_key
                    }
                    logger.info(f"Saved main report content to MinIO: {minio_key}")
                except Exception as e:
                    logger.warning(f"Could not save main report to MinIO: {e}")
            else:
                logger.warning("No generated files or report content found in result data")
            
            # Update article_title with generated title from polishing
            if "article_title" in result and result["article_title"] != report.article_title:
                report.article_title = result["article_title"]
                logger.info(f"Updated article_title from GenerateOverallTitle: {result['article_title']}")
            
            # Update topic with improved/generated topic if available
            if "generated_topic" in result and result["generated_topic"] and result["generated_topic"] != report.topic:
                report.topic = result["generated_topic"]
            
            # Store additional metadata in file_metadata (use MinIO keys if available, otherwise use original paths)
            file_metadata = report.file_metadata.copy() if report.file_metadata else {}
            file_metadata.update({
                "output_directory": result.get("output_directory", ""),
                "created_at": result.get("created_at", datetime.now(timezone.utc).isoformat()),
            })
            
            # Add main report info to metadata if saved
            if report.main_report_object_key:
                file_metadata["main_report_object_key"] = report.main_report_object_key
                logger.info(f"Stored main report object key in file_metadata: {report.main_report_object_key}")
            
            report.file_metadata = file_metadata
            
            # Store generated files (use MinIO keys if available, otherwise use original paths)
            if generated_files:
                report.generated_files = generated_files
            
            if result.get("processing_logs"):
                report.processing_logs = result["processing_logs"]
            
            # Save all changes to database including result_content, file_metadata, article_title, topic, and MinIO fields
            report.save(update_fields=["result_content", "file_metadata", "article_title", "topic", "generated_files", "processing_logs", "main_report_object_key", "updated_at"])
            
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
            # Clean up error detector for this job since it's failing
            self.error_detector.reset_job_errors(job_id)
            
            report = Report.objects.get(job_id=job_id)
            
            # Cleanup ReportImage records for failed jobs
            self._cleanup_report_images_on_failure(report)
            
            report.update_status(
                Report.STATUS_FAILED, 
                progress=f"Job failed: {error}", 
                error=error
            )
            
            # Also terminate the celery task if it's still running
            if report.celery_task_id:
                self._terminate_celery_task(report.celery_task_id)
            
            # Cleanup temp directories and prevent MinIO upload for failed jobs
            try:
                from ..orchestrator import report_orchestrator
                report_orchestrator.cleanup_failed_job(job_id)
                logger.info(f"Cleaned up temp directories for failed job {job_id}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp directories for failed job {job_id}: {cleanup_error}")
            
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
            # Clean up error detector for this job since it's being cancelled
            self.error_detector.reset_job_errors(job_id)
            
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
                query = query.filter(user=user_id)
            
            reports = query[:limit]
            
            jobs = []
            for report in reports:
                jobs.append({
                    "job_id": report.job_id,
                    "report_id": str(report.id),  # Convert UUID to string for JSON serialization
                    "user_id": str(report.user.pk),  # Convert UUID to string for JSON serialization
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
        if report.status != Report.STATUS_COMPLETED:
            return None
        
        result = {}
        
        # Add report content
        if report.result_content:
            result["report_content"] = report.result_content
            
        # Add file metadata
        if report.file_metadata:
            result.update(report.file_metadata)
            
        # Add generated files
        if report.generated_files:
            result["generated_files"] = report.generated_files
            
        # Add processing logs
        if report.processing_logs:
            result["processing_logs"] = report.processing_logs
            
        # Add main report object key
        if report.main_report_object_key:
            result["main_report_object_key"] = report.main_report_object_key
        
        return result if result else None
    
    def _check_worker_crash(self, report: Report) -> Dict[str, Any]:
        """Check if a Celery worker has crashed for a running job"""
        try:
            # Check if job has been running for too long without updates
            if report.updated_at:
                time_since_update = datetime.now(timezone.utc) - report.updated_at
                # Consider job crashed if no updates for 60 minutes
                if time_since_update > timedelta(minutes=60):
                    logger.warning(f"Job {report.job_id} has not been updated for {time_since_update}")
                    
                    # If we have a celery_task_id, check the actual task state
                    if report.celery_task_id:
                        return self._check_celery_task_state(report.celery_task_id)
                    else:
                        # No celery_task_id, assume crashed if stale for too long
                        return {
                            'crashed': True,
                            'error_message': f'Task timeout: No updates for {time_since_update}',
                            'progress_message': 'Worker appears to have crashed or hung'
                        }
            
            return {'crashed': False}
            
        except Exception as e:
            logger.error(f"Error checking worker crash for job {report.job_id}: {e}")
            return {'crashed': False}
    
    def _check_celery_task_state(self, celery_task_id: str) -> Dict[str, Any]:
        """Check if a Celery task has failed or is in an unknown state"""
        try:
            task_result = AsyncResult(celery_task_id)
            
            # Check task state
            if task_result.state == 'FAILURE':
                # Extract actual error message from Celery
                error_msg = "Celery task failed"
                progress_msg = "Task failed during execution"
                
                if hasattr(task_result, 'info') and task_result.info:
                    if isinstance(task_result.info, dict):
                        error_msg = task_result.info.get('error', str(task_result.info))
                    else:
                        error_msg = str(task_result.info)
                
                if hasattr(task_result, 'traceback') and task_result.traceback:
                    # Include traceback for debugging
                    error_msg += f"\nTraceback: {task_result.traceback}"
                
                logger.warning(f"Celery task {celery_task_id} failed: {error_msg}")
                return {
                    'crashed': True,
                    'error_message': error_msg,
                    'progress_message': progress_msg
                }
                
            elif task_result.state == 'REVOKED':
                logger.warning(f"Celery task {celery_task_id} was revoked")
                return {
                    'crashed': True,
                    'error_message': 'Task was revoked/cancelled',
                    'progress_message': 'Task was cancelled by system or user'
                }
                
            elif task_result.state in ['PENDING', 'RETRY', 'STARTED']:
                # Task is in a valid running state
                return {'crashed': False}
                
            else:
                # Unknown state, could indicate a problem
                logger.warning(f"Celery task {celery_task_id} in unknown state: {task_result.state}")
                return {
                    'crashed': True,
                    'error_message': f'Task in unknown state: {task_result.state}',
                    'progress_message': 'Task is in an unexpected state'
                }
                
        except Exception as e:
            logger.error(f"Error checking Celery task state {celery_task_id}: {e}")
            # If we can't check task state, assume it might be crashed
            return {
                'crashed': True,
                'error_message': f'Unable to check task state: {str(e)}',
                'progress_message': 'Worker may have crashed or be unreachable'
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sync_report_status_with_celery_state(self, report: "Report") -> None:
        """Synchronise the Report object's status/progress with the actual Celery task state.

        This method checks the task state unconditionally (if ``report.celery_task_id`` is set)
        and updates the report (and the associated cache entry) if the task has **already**
        failed or been revoked.  By doing this check every time a client polls the
        ``/report-jobs/{job_id}`` endpoint we can surface errors as soon as they happen instead
        of waiting for the 30-minute stale check performed by ``_check_worker_crash``.
        """

        if not report.celery_task_id:
            return  # Nothing to synchronise

        try:
            task_result = AsyncResult(report.celery_task_id)

            # Map Celery states to our Report status constants where appropriate
            if task_result.state == "FAILURE":
                # Extract a meaningful error message if available
                error_msg = "Celery task failed"
                if hasattr(task_result, "info") and task_result.info:
                    error_msg = str(task_result.info)

                if hasattr(task_result, "traceback") and task_result.traceback:
                    error_msg += f"\nTraceback: {task_result.traceback}"

                # Update the report only if we have not already marked it as FAILED
                if report.status not in [Report.STATUS_FAILED, Report.STATUS_COMPLETED, Report.STATUS_CANCELLED]:
                    report.update_status(
                        Report.STATUS_FAILED,
                        progress="Task failed during execution",
                        error=error_msg,
                    )

                    # Best-effort attempt to stop any lingering task processes.
                    self._terminate_celery_task(report.celery_task_id)

                    # Reflect same update in cache so that subsequent queries are consistent
                    cache_key = f"report_job:{report.job_id}"
                    job_data = cache.get(cache_key, {})
                    job_data.update(
                        {
                            "status": Report.STATUS_FAILED,
                            "progress": "Task failed during execution",
                            "error": error_msg,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    cache.set(cache_key, job_data, timeout=self.cache_timeout)

            elif task_result.state == "REVOKED":
                if report.status not in [Report.STATUS_CANCELLED, Report.STATUS_COMPLETED]:
                    report.update_status(
                        Report.STATUS_CANCELLED,
                        progress="Task was cancelled by system or user",
                        error="Task was revoked/cancelled",
                    )

                    # Ensure the task is fully terminated on the worker side.
                    self._terminate_celery_task(report.celery_task_id)

                    cache_key = f"report_job:{report.job_id}"
                    job_data = cache.get(cache_key, {})
                    job_data.update(
                        {
                            "status": Report.STATUS_CANCELLED,
                            "progress": "Task was cancelled by system or user",
                            "error": "Task was revoked/cancelled",
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    cache.set(cache_key, job_data, timeout=self.cache_timeout)

            # We purposefully ignore SUCCESS here because successful completion will be handled
            # by the report generation pipeline via ``update_job_result`` which persists the
            # generated content and metadata.  Other running-states (PENDING, RETRY, STARTED)
            # do not require immediate action.

        except Exception as e:
            # Failure to synchronise should not blow up the polling endpoint; just log.
            logger.error(
                f"Error synchronising Celery task state for report {report.job_id}: {e}"
            )

    def _terminate_celery_task(self, celery_task_id: str):
        """Send a revoke/terminate signal to the given Celery task.

        This is a defensive measure to make sure that, once a fatal condition has been
        detected, the worker process is not left running expensive computation that will
        eventually be discarded.  Using ``terminate=True`` ensures the underlying OS
        process gets a ``SIGTERM`` (default) or the provided signal.
        """
        try:
            if not celery_task_id:
                return

            task_result = AsyncResult(celery_task_id)

            # Only attempt termination if the task is still deemed active by Celery.
            if task_result.state in ["PENDING", "STARTED", "RETRY"]:
                task_result.revoke(terminate=True, signal="SIGTERM")
                logger.info(f"Sent terminate signal to Celery task {celery_task_id}")
        except Exception as e:
            logger.error(f"Error terminating Celery task {celery_task_id}: {e}")
    
    def prepare_report_images(self, report: Report) -> bool:
        """Prepare ReportImage records before report generation starts.
        
        This creates ReportImage records early so they're available during figure insertion.
        
        Args:
            report: Report instance
            
        Returns:
            bool: True if preparation was successful, False otherwise
        """
        if not report.include_image:
            logger.info(f"Image processing disabled for report {report.id}")
            return True
        
        try:
            from .report_image_service import ReportImageService
            from .figure_service import FigureDataService
            
            # Get figure data from cache or direct upload
            figure_data = FigureDataService.get_cached_figure_data(
                report.user.pk, f"direct_{report.id}"
            ) or FigureDataService.get_cached_figure_data(
                report.user.pk, report.notebooks.id if report.notebooks else None
            )
            
            if figure_data and "figures" in figure_data:
                # Extract figure IDs from cached figure data
                figure_ids = [fig.get("figure_id") for fig in figure_data["figures"] if fig.get("figure_id")]
                
                if figure_ids:
                    image_service = ReportImageService()
                    
                    # Find corresponding images in knowledge base
                    kb_images = image_service.find_images_by_figure_ids(figure_ids, report.user.id)
                    
                    if kb_images:
                        # Copy images to report folder and create ReportImage records
                        report_images = image_service.copy_images_to_report(report, kb_images)
                        logger.info(f"Prepared {len(report_images)} ReportImage records for report {report.id}")
                        return True
                    else:
                        logger.warning(f"No images found for figure IDs: {figure_ids}")
                else:
                    logger.info(f"No figure IDs found in cached figure data for report {report.id}")
            else:
                logger.info(f"No cached figure data found for report {report.id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error preparing report images for report {report.id}: {e}")
            return False
    
    def _cleanup_report_images_on_failure(self, report: Report):
        """Clean up ReportImage records when a job fails.
        
        Args:
            report: Report instance
        """
        try:
            from .report_image_service import ReportImageService
            image_service = ReportImageService()
            image_service.cleanup_report_images(report)
            logger.info(f"Cleaned up ReportImage records for failed report {report.id}")
        except Exception as e:
            logger.error(f"Error cleaning up ReportImage records for failed report {report.id}: {e}")
    
    def _cleanup_report_images_on_cancellation(self, report: Report):
        """Clean up ReportImage records when a job is cancelled.
        
        Args:
            report: Report instance
        """
        try:
            from .report_image_service import ReportImageService
            image_service = ReportImageService()
            image_service.cleanup_report_images(report)
            logger.info(f"Cleaned up ReportImage records for cancelled report {report.id}")
        except Exception as e:
            logger.error(f"Error cleaning up ReportImage records for cancelled report {report.id}: {e}")