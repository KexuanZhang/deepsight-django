"""
Configuration settings for the notebooks app utilities.
Simplified Django-compatible configuration without Pydantic dependencies.
"""

import os
from pathlib import Path
from typing import List, Optional
from django.conf import settings as django_settings


class NotebooksConfig:
    """Simple configuration class for notebooks utilities."""
    
    def __init__(self):
        # Project paths
        self.PROJECT_ROOT = getattr(django_settings, 'BASE_DIR', 
                                  os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        
        # File processing settings
        self.MAX_FILE_SIZE = getattr(django_settings, 'NOTEBOOKS_MAX_FILE_SIZE', 100 * 1024 * 1024)  # 100MB
        self.ALLOWED_FILE_TYPES = getattr(django_settings, 'NOTEBOOKS_ALLOWED_FILE_TYPES', 
                                        [".txt", ".md", ".pdf", ".mp3", ".wav", ".m4a", ".mp4", ".avi", ".mov", ".ppt", ".pptx"])
        
        # Processing settings
        self.MAX_CONCURRENT_JOBS = getattr(django_settings, 'NOTEBOOKS_MAX_CONCURRENT_JOBS', 3)
        self.JOB_TIMEOUT = getattr(django_settings, 'NOTEBOOKS_JOB_TIMEOUT', 3600)
        
        # Redis configuration for job queues (with fallbacks)
        self.REDIS_HOST = getattr(django_settings, 'REDIS_HOST', 'localhost')
        self.REDIS_PORT = getattr(django_settings, 'REDIS_PORT', 6379)
        self.REDIS_DB = getattr(django_settings, 'REDIS_DB', 0)
        self.REDIS_PASSWORD = getattr(django_settings, 'REDIS_PASSWORD', None)
        
        # Whisper model for audio processing
        self.DEFAULT_WHISPER_MODEL = getattr(django_settings, 'NOTEBOOKS_WHISPER_MODEL', 'base')
        
        # Content indexing settings
        self.ENABLE_CONTENT_INDEXING = getattr(django_settings, 'NOTEBOOKS_ENABLE_CONTENT_INDEXING', True)
        self.MAX_SEARCH_RESULTS = getattr(django_settings, 'NOTEBOOKS_MAX_SEARCH_RESULTS', 50)
        
        # File validation settings
        self.ENABLE_MAGIC_VALIDATION = getattr(django_settings, 'NOTEBOOKS_ENABLE_MAGIC_VALIDATION', True)
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def data_dir(self) -> Path:
        """Get data directory path."""
        return Path(self.PROJECT_ROOT) / "data"
    
    @property
    def upload_dir(self) -> Path:
        """Get upload directory path."""
        return self.data_dir / "uploads"
    
    @property
    def processed_files_dir(self) -> Path:
        """Get processed files directory path."""
        return self.data_dir / "processed_files"


# Create a single shared settings instance
def get_notebooks_config():
    """Get the notebooks configuration instance."""
    try:
        return NotebooksConfig()
    except Exception:
        # Return a minimal config if Django settings are not available
        class MinimalConfig:
            MAX_FILE_SIZE = 100 * 1024 * 1024
            ALLOWED_FILE_TYPES = [".txt", ".md", ".pdf", ".mp3", ".wav", ".m4a", ".mp4", ".avi", ".mov", ".ppt", ".pptx"]
            redis_url = "redis://localhost:6379/0"
            
        return MinimalConfig()


# Global instance
config = get_notebooks_config()