"""
Celery configuration for Django project.
"""

import os
import sys
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

# Fix for macOS fork() issues with Metal Performance Shaders
if sys.platform == "darwin":  # macOS
    import multiprocessing
    multiprocessing.set_start_method('spawn', force=True)

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
        "notebooks.tasks.process_url_document_task": {"queue": "notebook_processing"},
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
    # Use solo pool on macOS to avoid fork() issues
    worker_pool="solo" if sys.platform == "darwin" else "prefork",
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
