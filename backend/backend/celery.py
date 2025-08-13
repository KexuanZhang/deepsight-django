"""
Celery configuration for Django project.
"""

import os
import logging
from celery import Celery
from celery.signals import worker_init
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

app = Celery("backend")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Custom logging filter to suppress WARNING messages in Celery workers
class CeleryWarningFilter(logging.Filter):
    def filter(self, record):
        # Suppress WARNING level messages, allow DEBUG, INFO, ERROR, CRITICAL
        return record.levelno != logging.WARNING

# Configure logging for Celery workers to suppress streaming character warnings
def setup_celery_logging():
    """Configure Celery logging to suppress WARNING messages."""
    # Get the root logger and add filter
    root_logger = logging.getLogger()
    root_logger.addFilter(CeleryWarningFilter())
    
    # Also add filter to specific loggers that might generate these warnings
    for logger_name in ['strands', 'openai', 'httpx']:
        logger = logging.getLogger(logger_name)
        logger.addFilter(CeleryWarningFilter())

# Set up logging configuration when Celery starts
setup_celery_logging()

# Also set up logging when workers initialize
@worker_init.connect
def configure_worker_logging(sender=None, conf=None, **kwargs):
    """Configure logging when Celery worker initializes."""
    setup_celery_logging()

# Configure Celery settings
app.conf.update(
    # Task routing
    task_routes={
        "podcast.tasks.process_podcast_generation": {"queue": "podcast"},
        "podcast.tasks.cancel_podcast_generation": {"queue": "podcast"},
        "podcast.tasks.cleanup_old_podcast_jobs": {"queue": "maintenance"},
        "reports.tasks.process_report_generation": {"queue": "reports"},
        "reports.tasks.cleanup_old_reports": {"queue": "maintenance"},
        "reports.tasks.cancel_report_generation": {"queue": "reports"},
        "reports.tasks.validate_report_configuration": {"queue": "validation"},
        "notebooks.tasks.process_url_task": {"queue": "notebook_processing"},
        "notebooks.tasks.process_url_media_task": {"queue": "notebook_processing"},
        "notebooks.tasks.process_file_upload_task": {"queue": "notebook_processing"},
        "notebooks.tasks.generate_image_captions_task": {"queue": "notebook_processing"},
        "notebooks.tasks.test_caption_generation_task": {"queue": "notebook_processing"},
    },
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task time limits
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-old-podcast-jobs": {
            "task": "podcast.tasks.cleanup_old_podcast_jobs",
            "schedule": 86400.0,  # Run daily
        },
        "cleanup-old-reports": {
            "task": "reports.tasks.cleanup_old_reports",
            "schedule": 86400.0,  # Run daily
        },
    },
)


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
