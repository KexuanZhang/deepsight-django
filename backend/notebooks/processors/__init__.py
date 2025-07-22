"""
Processors package for the notebooks module.

This package contains all processing logic for different types of content:
- file_processors.py: New file type specific processors
  
- media_processors.py: Media processing utilities
- upload_processor.py: Legacy upload processor (moved from utils)
- url_extractor.py: Legacy URL extractor (moved from utils)
"""

# New focused processors
from .file_processors import FileProcessor
from .media_processors import MediaProcessor

# Legacy processors (moved from utils)
try:
    from .upload_processor import UploadProcessor
except ImportError:
    UploadProcessor = None

try:
    from .url_extractor import URLExtractor
except ImportError:
    URLExtractor = None

__all__ = [
    'FileProcessor',
    'MediaProcessor',
    'UploadProcessor',
    'URLExtractor'
] 