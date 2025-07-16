"""
Configuration settings for the notebooks app utilities.
Centralized storage and processing configuration for DeepSight.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Tuple
from django.conf import settings as django_settings


class NotebooksConfig:
    """Configuration class for notebooks utilities."""

    def __init__(self):
        # Project paths
        self.PROJECT_ROOT = getattr(
            django_settings,
            "BASE_DIR",
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        )

        # File processing settings
        self.MAX_FILE_SIZE = getattr(django_settings, "NOTEBOOKS_MAX_FILE_SIZE", 100 * 1024 * 1024)
        self.ALLOWED_FILE_TYPES = getattr(
            django_settings,
            "NOTEBOOKS_ALLOWED_FILE_TYPES",
            [".txt", ".md", ".pdf", ".mp3", ".wav", ".m4a", ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".3gp", ".ogv", ".m4v", ".ppt", ".pptx"],
        )

        # Processing settings
        self.MAX_CONCURRENT_JOBS = getattr(django_settings, "NOTEBOOKS_MAX_CONCURRENT_JOBS", 3)
        self.JOB_TIMEOUT = getattr(django_settings, "NOTEBOOKS_JOB_TIMEOUT", 3600)

        # Redis configuration
        self.REDIS_HOST = getattr(django_settings, "REDIS_HOST", os.getenv("REDIS_HOST", "localhost"))
        self.REDIS_PORT = getattr(django_settings, "REDIS_PORT", 6379)
        self.REDIS_DB = getattr(django_settings, "REDIS_DB", 0)
        self.REDIS_PASSWORD = getattr(django_settings, "REDIS_PASSWORD", None)

        # Audio processing
        self.DEFAULT_WHISPER_MODEL = getattr(django_settings, "NOTEBOOKS_WHISPER_MODEL", "base")

        # Content indexing
        self.ENABLE_CONTENT_INDEXING = getattr(django_settings, "NOTEBOOKS_ENABLE_CONTENT_INDEXING", True)
        self.MAX_SEARCH_RESULTS = getattr(django_settings, "NOTEBOOKS_MAX_SEARCH_RESULTS", 50)

        # File validation
        self.ENABLE_MAGIC_VALIDATION = getattr(django_settings, "NOTEBOOKS_ENABLE_MAGIC_VALIDATION", True)

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


def get_notebooks_config():
    """Get the notebooks configuration instance."""
    try:
        return NotebooksConfig()
    except Exception:
        # Minimal fallback config
        class MinimalConfig:
            MAX_FILE_SIZE = 100 * 1024 * 1024
            ALLOWED_FILE_TYPES = [".txt", ".md", ".pdf", ".mp3", ".wav", ".m4a", ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".3gp", ".ogv", ".m4v", ".ppt", ".pptx"]
            redis_url = f"redis://{os.getenv('REDIS_HOST', 'localhost')}:6379/0"
        return MinimalConfig()


# Global configuration instance
config = get_notebooks_config()


class DeepSightStorageConfig:
    """Configuration for DeepSight storage system."""

    def __init__(self):
        self.base_data_path = Path(django_settings.MEDIA_ROOT)
        self.base_data_path.mkdir(parents=True, exist_ok=True)
        
        # Ensure Global folder exists
        (self.base_data_path / "Global").mkdir(exist_ok=True)

    # ========== PATH GENERATORS ==========
    def get_user_base_path(self, user_id: int) -> Path:
        """Get the base path for a specific user."""
        return self.base_data_path / "Users" / f"u_{user_id}"

    def get_knowledge_base_path(self, user_id: int, year_month: str, file_id: str) -> Path:
        """Get the knowledge base path for a specific file."""
        return self.get_user_base_path(user_id) / "knowledge_base_item" / year_month / f"f_{file_id}"
    
    def get_report_path(self, user_id: int, year_month: str, report_id: str, notebook_id: int = None) -> Path:
        """Get the report directory path for a specific report."""
        base_path = self.get_user_base_path(user_id)
        if notebook_id:
            return base_path / f"n_{notebook_id}" / "report" / year_month / f"r_{report_id}"
        return base_path / "report" / year_month / f"r_{report_id}"
    
    def get_podcast_path(self, user_id: int, year_month: str, podcast_id: str, notebook_id: int = None) -> Path:
        """Get the podcast directory path for a specific podcast."""
        base_path = self.get_user_base_path(user_id)
        if notebook_id:
            return base_path / f"n_{notebook_id}" / "podcast" / year_month / f"p_{podcast_id}"
        return base_path / "podcast" / year_month / f"p_{podcast_id}"
    
    def get_global_path(self) -> Path:
        """Get the global shared folder path."""
        return self.base_data_path / "Global"

    # ========== DIRECTORY CREATORS ==========
    def ensure_user_directories(self, user_id: int) -> Path:
        """Ensure user base directory exists."""
        user_base = self.get_user_base_path(user_id)
        user_base.mkdir(parents=True, exist_ok=True)
        return user_base
    
    def ensure_notebook_base(self, user_id: int, notebook_id: int) -> Path:
        """Ensure notebook base directory exists."""
        user_base = self.ensure_user_directories(user_id)
        notebook_base = user_base / f"n_{notebook_id}"
        notebook_base.mkdir(exist_ok=True)
        return notebook_base

    # ========== HIGH-LEVEL OPERATIONS ==========
    def create_podcast_file_path(self, podcast_job, filename: str) -> Tuple[Path, str]:
        """
        Create complete file path for podcast and return absolute and relative paths.
        
        Args:
            podcast_job: PodcastJob instance
            filename: Audio file name
            
        Returns:
            Tuple[Path, str]: (absolute_path, relative_path_for_db)
        """
        user_id = podcast_job.user.pk
        current_date = podcast_job.created_at or datetime.now()
        year_month = current_date.strftime('%Y-%m')
        podcast_id = str(podcast_job.pk)
        notebook_id = podcast_job.notebooks.pk if podcast_job.notebooks else None
        
        # Get podcast directory and ensure it exists
        podcast_dir = self.get_podcast_path(user_id, year_month, podcast_id, notebook_id)
        podcast_dir.mkdir(parents=True, exist_ok=True)
        
        # Create full file path
        full_file_path = podcast_dir / filename
        
        # Create relative path for database
        try:
            relative_path = full_file_path.relative_to(self.base_data_path)
            return full_file_path, str(relative_path)
        except ValueError:
            return full_file_path, str(full_file_path)
    
    def delete_podcast_directory(self, podcast_job) -> bool:
        """
        Delete entire podcast directory for a given job.
        
        Args:
            podcast_job: PodcastJob instance
            
        Returns:
            bool: Success status
        """
        try:
            user_id = podcast_job.user.pk
            current_date = podcast_job.created_at or datetime.now()
            year_month = current_date.strftime('%Y-%m')
            podcast_id = str(podcast_job.pk)
            notebook_id = podcast_job.notebooks.pk if podcast_job.notebooks else None
            
            podcast_dir = self.get_podcast_path(user_id, year_month, podcast_id, notebook_id)
            
            if podcast_dir.exists():
                shutil.rmtree(podcast_dir)
                return True
            return False
            
        except Exception:
            return False


# DEPRECATED: DeepSightStorageConfig has been replaced by MinIO storage adapter
# Commented out to prevent usage - all storage operations should use storage_adapter
# storage_config = DeepSightStorageConfig()
storage_config = None  # This will cause errors if legacy code tries to use it
