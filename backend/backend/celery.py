"""
Celery configuration for Django project.
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

app = Celery("backend")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure Celery settings
app.conf.update(
    # Task routing
    task_routes={
        "podcast.tasks.process_podcast_generation": {"queue": "podcast"},
        "podcast.tasks.cleanup_old_podcast_jobs": {"queue": "maintenance"},
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
    },
)


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
