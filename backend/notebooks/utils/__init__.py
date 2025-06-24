"""
Notebooks utilities package.

This package provides file processing, validation, and storage utilities
for the DeepSight notebooks application.
"""

# Core utilities that are safe to import
from .config import config
from .file_validator import FileValidator

# Services that depend on external libraries (import with fallbacks)
try:
    from .upload_processor import UploadProcessor
except ImportError:
    UploadProcessor = None

try:
    from .file_storage import FileStorageService
except ImportError:
    FileStorageService = None

try:
    from .content_index import ContentIndexingService
except ImportError:
    ContentIndexingService = None

__all__ = [
    "config",
    "FileValidator",
    "UploadProcessor",
    "FileStorageService",
    "ContentIndexingService",
]
