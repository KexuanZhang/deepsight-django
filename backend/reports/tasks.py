"""
Celery tasks for report generation.
"""

import logging
import re
import time
from typing import Dict, Any
from celery import shared_task
from .orchestrator import report_orchestrator

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_report_generation(self, report_id: int):
    """Process report generation job - this runs in the background worker"""
    try:
        logger.info(f"Starting report generation task for report {report_id}")
        
        # Update job status to running
        # First get job_id from report
        from .models import Report
        try:
            report = Report.objects.get(id=report_id)
            job_id = report.job_id
        except Report.DoesNotExist:
            logger.error(f"Report {report_id} not found")
            raise Exception(f"Report {report_id} not found")
        
        # -------------------------------------------------------------------
        # Attach progress-log handler so INFO messages update frontend
        # -------------------------------------------------------------------
        progress_handler = ReportProgressLogHandler(job_id, report_orchestrator)
        root_logger = logging.getLogger()  # capture logs from all modules
        root_logger.addHandler(progress_handler)
        
        # Check if job was cancelled before we start
        if report.status == Report.STATUS_CANCELLED:
            logger.info(f"Report {report_id} was cancelled before processing started")
            root_logger.removeHandler(progress_handler)
            return {"status": "cancelled", "message": "Report was cancelled"}
        
        # Update job status to running
        report_orchestrator.update_job_progress(
            job_id, "Starting report generation", Report.STATUS_RUNNING
        )
        
        # Generate the report
        start_ts = time.time()
        try:
            result = report_orchestrator.generate_report(report_id)
        finally:
            # Detach handler regardless of success/failure to avoid leaks
            root_logger.removeHandler(progress_handler)
        
        if result.get('success', False):
            # Update job with success
            report_orchestrator.update_job_result(job_id, result, Report.STATUS_COMPLETED)
            # Push final success progress so that frontend can display last stage
            elapsed = time.time() - start_ts
            success_msg = (
                f"Task reports.tasks.process_report_generation[{self.request.id}] succeeded in {elapsed:.1f}s"
            )
            report_orchestrator.update_job_progress(job_id, success_msg)
            logger.info(f"Successfully completed report generation for report {report_id}")
            return result
        else:
            # Handle generation failure
            error_msg = result.get('error_message', 'Report generation failed')
            report_orchestrator.update_job_error(job_id, error_msg)
            raise Exception(error_msg)
    
    except Exception as e:
        logger.error(f"Error processing report generation for report {report_id}: {e}")
        
        # Update job with error
        try:
            from .models import Report
            report = Report.objects.get(id=report_id)
            report_orchestrator.update_job_error(report.job_id, str(e))
        except Report.DoesNotExist:
            logger.error(f"Could not update error for report {report_id} - report not found")
        
        # Re-raise for Celery to handle
        raise


@shared_task
def cleanup_old_reports():
    """Clean up old report jobs and associated files"""
    try:
        logger.info("Starting cleanup of old reports")
        report_orchestrator.cleanup_old_jobs()
        logger.info("Completed cleanup of old reports")
        return {"status": "success", "message": "Cleanup completed"}
    
    except Exception as e:
        logger.error(f"Error during report cleanup: {e}")
        raise


@shared_task(bind=True)
def cancel_report_generation(self, job_id: str):
    """Cancel a report generation job by revoking the Celery task."""
    try:
        logger.info(f"Cancelling report generation for job {job_id}")
        
        from .models import Report
        report = Report.objects.get(job_id=job_id)
        
        # Revoke the main Celery task if it's running
        if report.celery_task_id:
            try:
                from backend.celery import app as celery_app
                celery_app.control.revoke(
                    report.celery_task_id, terminate=True, signal="SIGTERM"
                )
                logger.info(f"Revoked Celery task {report.celery_task_id} for job {job_id}")
            except Exception as e:
                logger.warning(f"Failed to revoke Celery task for job {job_id}: {e}")

        # Call generator cancellation to clean up temp directories
        try:
            report_orchestrator.cancel_generation(job_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup during cancellation for job {job_id}: {e}")

        # Cleanup ReportImage records for cancelled jobs
        try:
            from .core.job_service import JobService
            job_service = JobService()
            job_service._cleanup_report_images_on_cancellation(report)
        except Exception as e:
            logger.warning(f"Failed to cleanup ReportImage records for cancelled job {job_id}: {e}")

        # Update job status in database to 'cancelled'
        report.update_status(Report.STATUS_CANCELLED, progress="Job cancelled by user")
        
        logger.info(f"Successfully cancelled report generation for job {job_id}")
        return {"status": "cancelled", "job_id": job_id}
    
    except Report.DoesNotExist:
        logger.error(f"Report with job_id {job_id} not found for cancellation")
        return {"status": "failed", "job_id": job_id, "message": "Job not found"}
    except Exception as e:
        logger.error(f"Error cancelling report generation for job {job_id}: {e}")
        raise


@shared_task
def validate_report_configuration(config: Dict[str, Any]):
    """Validate report configuration in background"""
    try:
        logger.info("Validating report configuration")
        
        is_valid = report_orchestrator.validate_report_configuration(config)
        validation_results = report_orchestrator.validate_configuration_settings(config)
        
        return {
            "is_valid": is_valid,
            "validation_results": validation_results,
            "supported_options": report_orchestrator.get_supported_options()
        }
    
    except Exception as e:
        logger.error(f"Error validating report configuration: {e}")
        return {
            "is_valid": False,
            "error": str(e),
            "validation_results": {},
            "supported_options": {}
        }


# ---------------------------------------------------------------------------
# Progress-bar support – custom log handler
# ---------------------------------------------------------------------------


class ReportProgressLogHandler(logging.Handler):
    """Intercept specific Celery worker INFO messages and push them to the
    report orchestrator so that the frontend progress-bar can update in real
    time. We only care about five well-defined stages of report generation.
    
    Additionally, forward all ERROR messages to the orchestrator so they can be
    displayed in the SSE progress bar. Only MainProcess ERROR messages will cause
    task failure, while other ERROR messages are displayed without stopping the task.

    The handler is lightweight and attaches only for the lifetime of the
    `process_report_generation` task – see usage below.
    """

    # Pre-compile regexes once; keep order to map to user-visible stages
    _PATTERNS = [
        re.compile(r"run_knowledge_curation_module executed", re.IGNORECASE),
        re.compile(r"run_outline_generation_module executed", re.IGNORECASE),
        re.compile(r"run_article_generation_module executed", re.IGNORECASE),
        re.compile(r"run_article_polishing_module executed", re.IGNORECASE),
        re.compile(r"Task reports\.tasks\.process_report_generation\[.*?\] succeeded", re.IGNORECASE),
    ]

    def __init__(self, job_id: str, orchestrator):
        super().__init__(level=logging.INFO)  # Monitor both INFO and ERROR levels
        self.job_id = job_id
        self.orchestrator = orchestrator

    def emit(self, record: logging.LogRecord):
        try:
            msg = record.getMessage()
            
            # Handle ERROR messages - forward all ERROR messages to orchestrator
            # The orchestrator will decide whether to fail the task (MainProcess) or just display (others)
            if record.levelno == logging.ERROR:
                try:
                    self.orchestrator.update_job_progress(self.job_id, msg)
                except Exception as e:  # pragma: no cover – never crash handler
                    logging.getLogger(__name__).warning(
                        f"Failed to process error message for {self.job_id}: {e}"
                    )
                return
            
            # Handle INFO messages that match our progress patterns
            if record.levelno == logging.INFO:
                for pattern in self._PATTERNS:
                    if pattern.search(msg):
                        # Push raw log line to progress – keeps message identical to log
                        try:
                            self.orchestrator.update_job_progress(self.job_id, msg)
                        except Exception as e:  # pragma: no cover – never crash handler
                            logging.getLogger(__name__).warning(
                                f"Failed to update progress for {self.job_id}: {e}"
                            )
                        break  # Stop after first match
        except Exception:
            # Never raise from a logging handler – swallow any errors gracefully
            pass