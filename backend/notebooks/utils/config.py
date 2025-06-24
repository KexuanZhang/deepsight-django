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
        self.REDIS_HOST = getattr(django_settings, 'REDIS_HOST', os.getenv('REDIS_HOST', 'localhost'))
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
    
    # Legacy data directory properties removed - now using Django's MEDIA_ROOT


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
            redis_url = f"redis://{os.getenv('REDIS_HOST', 'localhost')}:6379/0"
            
        return MinimalConfig()


# Global instance
config = get_notebooks_config()


class DeepSightStorageConfig:
    """Configuration for DeepSight storage system."""
    
    def __init__(self):
        # Base path for all DeepSight data
        self.base_data_path = Path(django_settings.MEDIA_ROOT)
        
        # Ensure base directory exists
        self.base_data_path.mkdir(parents=True, exist_ok=True)
        
        # Ensure Global folder exists
        global_folder = self.base_data_path / "Global"
        global_folder.mkdir(exist_ok=True)
        
    def get_user_base_path(self, user_id: int) -> Path:
        """Get the base path for a specific user."""
        return self.base_data_path / "Users" / f"u_{user_id}"
    
    def get_knowledge_base_path(self, user_id: int, year_month: str, file_id: str) -> Path:
        """Get the knowledge base path for a specific file."""
        return self.get_user_base_path(user_id) / "knowledge_base_item" / year_month / f"f_{file_id}"
    

    
    def get_report_path(self, user_id: int, year_month: str, report_id: str) -> Path:
        """Get the report path for a specific report."""
        return self.get_user_base_path(user_id) / "report" / year_month / f"r_{report_id}"
    
    def get_podcast_path(self, user_id: int, year_month: str, podcast_id: str) -> Path:
        """Get the podcast path for a specific podcast."""
        return self.get_user_base_path(user_id) / "podcast" / year_month / f"p_{podcast_id}"
    
    def get_global_path(self) -> Path:
        """Get the global shared folder path."""
        return self.base_data_path / "Global"
    
    def ensure_user_directories(self, user_id: int):
        """Ensure all necessary directories exist for a user."""
        user_base = self.get_user_base_path(user_id)
        user_base.mkdir(parents=True, exist_ok=True)
        
        # Create standard subdirectories
        (user_base / "knowledge_base_item").mkdir(exist_ok=True)
        (user_base / "report").mkdir(exist_ok=True)
        (user_base / "podcast").mkdir(exist_ok=True)


# Global storage configuration instance
storage_config = DeepSightStorageConfig()