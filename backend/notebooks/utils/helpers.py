"""
Common utilities for the notebooks module.
Consolidated configuration, media extraction, and helper functions.
"""

import os
import hashlib
import logging
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Union, Any, Optional, Tuple
from urllib.parse import urlparse

from django.conf import settings as django_settings
from django.http import JsonResponse, Http404
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response


# ===== CONFIGURATION =====

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
            [".txt", ".md", ".pdf", ".mp3", ".wav", ".m4a", ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".3gp", ".ogv", ".m4v", ".pptx", ".docx"],
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

        # MinIO configuration
        self.MINIO_ENDPOINT = getattr(django_settings, "MINIO_ENDPOINT", os.getenv("MINIO_ENDPOINT", "localhost:9000"))
        self.MINIO_ACCESS_KEY = getattr(django_settings, "MINIO_ACCESS_KEY", os.getenv("MINIO_ACCESS_KEY", "minioadmin"))
        self.MINIO_SECRET_KEY = getattr(django_settings, "MINIO_SECRET_KEY", os.getenv("MINIO_SECRET_KEY", "minioadmin"))
        self.MINIO_USE_SSL = getattr(django_settings, "MINIO_USE_SSL", os.getenv("MINIO_USE_SSL", "False").lower() == "true")
        self.MINIO_BUCKET_NAME = getattr(django_settings, "MINIO_BUCKET_NAME", os.getenv("MINIO_BUCKET_NAME", "deepsight-users"))

    def get_temp_dir(self, prefix: str = "deepsight") -> str:
        """Get temporary directory for processing."""
        return tempfile.mkdtemp(prefix=f"{prefix}_")


# Global config instance
config = NotebooksConfig()


# ===== TEXT UTILITIES =====

def clean_title(title: str) -> str:
    """Clean the title by replacing non-alphanumeric characters with underscores."""
    if not title:
        return "untitled"
    
    # Replace all non-alphanumeric characters (except for underscores) with underscores
    cleaned = re.sub(r'[^\w\d]', '_', title)
    # Replace consecutive underscores with a single underscore
    cleaned = re.sub(r'_+', '_', cleaned)
    # Remove leading/trailing underscores
    cleaned = cleaned.strip('_')
    
    return cleaned or "untitled"


def calculate_source_hash(source_identifier: str, user_id: int) -> str:
    """
    Calculate SHA256 hash of source identifier (filename or URL) for early duplicate detection.
    
    This is used as the primary hash for source_hash field in KnowledgeBaseItem.
    For files: uses original filename before clean_title
    For URLs: uses the raw URL
    User ID is included to scope duplicates per user.
    
    Args:
        source_identifier: Original filename or raw URL
        user_id: User ID to scope the hash per user
        
    Returns:
        SHA256 hash as hexadecimal string for use in KnowledgeBaseItem.source_hash
    """
    # Combine source identifier with user ID for user-scoped hashing
    combined_source = f"{user_id}:{source_identifier}"
    content_bytes = combined_source.encode('utf-8')
    return hashlib.sha256(content_bytes).hexdigest()


def calculate_content_hash(content: Union[str, bytes]) -> str:
    """
    Calculate SHA256 hash of content for content-based deduplication (fallback check).
    
    This is used as a secondary check to catch duplicates when different filenames
    contain the same content.
    
    Args:
        content: File content as string or bytes
        
    Returns:
        SHA256 hash as hexadecimal string
    """
    if isinstance(content, str):
        content_bytes = content.encode('utf-8')
    else:
        content_bytes = content
    
    return hashlib.sha256(content_bytes).hexdigest()


def calculate_user_content_hash(content: str, user_id: int) -> str:
    """
    Calculate SHA256 hash of text content for duplicate detection of pasted text.
    
    Used specifically for pasted text content to detect identical content
    regardless of generated filename. User-scoped to prevent cross-user conflicts.
    
    Args:
        content: The actual text content
        user_id: User ID to scope the hash per user
        
    Returns:
        SHA256 hash as hexadecimal string
    """
    # Normalize content (strip whitespace, normalize line endings)
    normalized_content = content.strip().replace('\r\n', '\n').replace('\r', '\n')
    combined_content = f"{user_id}:{normalized_content}"
    content_bytes = combined_content.encode('utf-8')
    return hashlib.sha256(content_bytes).hexdigest()


def check_content_duplicate(content: str, user_id: int, notebook_id: str = None):
    """
    Check if identical text content already exists within the specific notebook.
    
    Used for pasted text to detect duplicates based on actual content
    rather than generated filename.
    
    Args:
        content: The text content to check
        user_id: User ID to check duplicates for
        notebook_id: Notebook ID to check within (required since content is now notebook-specific)
        
    Returns:
        KnowledgeBaseItem if duplicate content found, None otherwise
    """
    from django.contrib.auth import get_user_model
    from ..models import KnowledgeBaseItem, Notebook
    
    if not notebook_id:
        return None
    
    # Normalize content for comparison (strip whitespace, normalize line endings)
    normalized_content = content.strip().replace('\r\n', '\n').replace('\r', '\n')
    
    # Check existing items by comparing actual content field directly
    # Filter by notebook and look for exact content match
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        notebook = Notebook.objects.get(id=notebook_id, user=user)
        duplicate_item = KnowledgeBaseItem.objects.filter(
            notebook=notebook,
            content=normalized_content
        ).first()
        return duplicate_item
    except (User.DoesNotExist, Notebook.DoesNotExist):
        return None


def check_source_duplicate(source_identifier: str, user_id: int, notebook_id: str = None):
    """
    Check if source (filename or URL) already exists within the specific notebook.
    Since sources are now notebook-specific, we only check within the given notebook.
    
    Args:
        source_identifier: Original filename or raw URL
        user_id: User ID to check within
        notebook_id: Notebook ID to check within (required for notebook-specific sources)
        
    Returns:
        KnowledgeBaseItem if duplicate found, None otherwise
    """
    from ..models import KnowledgeBaseItem, Notebook
    from django.contrib.auth import get_user_model
    
    # notebook_id is required for notebook-specific duplicate checking
    if not notebook_id:
        return None
        
    source_hash = calculate_source_hash(source_identifier, user_id)
    
    # Check for duplicates within the specific notebook only
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        notebook = Notebook.objects.get(id=notebook_id, user=user)
        duplicate_item = KnowledgeBaseItem.objects.filter(
            notebook=notebook,
            source_hash=source_hash
        ).first()
        return duplicate_item
    except (User.DoesNotExist, Notebook.DoesNotExist):
        return None


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


def sanitize_path(path: str) -> str:
    """Sanitize file path for safe storage."""
    # Remove any directory traversal attempts
    path = os.path.normpath(path)
    if path.startswith('/') or '\\' in path or '..' in path:
        path = os.path.basename(path)
    
    return path


# ===== MEDIA UTILITIES =====

class MediaFeatureExtractor:
    """Extract features and metadata from media files."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.media_extractor")
        self.supported_video_formats = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.3gp', '.ogv', '.m4v'}
        self.supported_audio_formats = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg'}
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from media file using ffprobe."""
        try:
            import subprocess
            import json
            
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            metadata = {
                'format': data.get('format', {}),
                'streams': data.get('streams', []),
                'duration': float(data.get('format', {}).get('duration', 0)),
                'size': int(data.get('format', {}).get('size', 0)),
                'bitrate': int(data.get('format', {}).get('bit_rate', 0))
            }
            
            # Extract video/audio specific info
            for stream in metadata['streams']:
                if stream.get('codec_type') == 'video':
                    metadata['has_video'] = True
                    metadata['video_codec'] = stream.get('codec_name')
                    metadata['width'] = stream.get('width')
                    metadata['height'] = stream.get('height')
                elif stream.get('codec_type') == 'audio':
                    metadata['has_audio'] = True
                    metadata['audio_codec'] = stream.get('codec_name')
                    metadata['sample_rate'] = stream.get('sample_rate')
                    metadata['channels'] = stream.get('channels')
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata from {file_path}: {e}")
            return {'error': str(e)}
    
    def is_media_file(self, filename: str) -> bool:
        """Check if file is a supported media file."""
        ext = Path(filename).suffix.lower()
        return ext in self.supported_video_formats or ext in self.supported_audio_formats


# ===== VIEW MIXINS =====

class NotebookPermissionMixin:
    """Mixin for views that require notebook access permission."""
    
    def get_notebook_or_404(self, notebook_id: str, user):
        """Get notebook with permission check."""
        try:
            from ..models import Notebook
            return Notebook.objects.get(id=notebook_id, user=user)
        except Notebook.DoesNotExist:
            raise Http404("Notebook not found")


class ErrorHandlingMixin:
    """Mixin for consistent error handling in views."""
    
    def handle_error(self, error: Exception, operation: str = "operation") -> Response:
        """Handle errors consistently across views."""
        logger = logging.getLogger(self.__class__.__module__)
        logger.error(f"Error in {operation}: {str(error)}")
        
        if isinstance(error, ValidationError):
            return Response(
                {"error": "Validation failed", "details": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif isinstance(error, Http404):
            return Response(
                {"error": "Resource not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        else:
            return Response(
                {"error": f"Internal server error during {operation}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AsyncResponseMixin:
    """Mixin for handling async operations in views."""
    
    def async_response(self, task_id: str, message: str = "Task queued") -> Response:
        """Return standardized async response."""
        return Response(
            {
                "task_id": task_id,
                "status": "queued",
                "message": message
            },
            status=status.HTTP_202_ACCEPTED
        )


# ===== CONTENT INDEXING =====

class ContentIndexingService:
    """Service for indexing content for search and retrieval."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.content_indexing")
        self.enabled = config.ENABLE_CONTENT_INDEXING
    
    def index_content(self, file_id: str, content: str, metadata: Dict[str, Any], processing_stage: str = "immediate"):
        """Index content for search."""
        if not self.enabled:
            return
        
        try:
            # Basic indexing - could be extended with full-text search engines
            self.logger.info(f"Indexing content for file {file_id} at stage {processing_stage}")
            
            # Extract key information for indexing
            word_count = len(content.split())
            char_count = len(content)
            
            # Log indexing completion
            self.logger.debug(f"Indexed file {file_id}: {word_count} words, {char_count} characters")
            
        except Exception as e:
            self.logger.error(f"Error indexing content for {file_id}: {e}")
    
    def search_content(self, query: str, user_id: int, limit: int = None) -> List[Dict[str, Any]]:
        """Search indexed content."""
        if not self.enabled:
            return []
        
        try:
            # Basic search implementation - could be extended
            limit = limit or config.MAX_SEARCH_RESULTS
            self.logger.info(f"Searching content for user {user_id} with query: {query}")
            
            # Placeholder for search results
            return []
            
        except Exception as e:
            self.logger.error(f"Error searching content: {e}")
            return []


# ===== RAG ENGINE =====

class RAGChatbot:
    """Simple RAG (Retrieval-Augmented Generation) chatbot implementation."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.rag_chatbot")
        self.content_indexing = ContentIndexingService()
    
    def chat(self, query: str, user_id: int, notebook_id: str = None) -> Dict[str, Any]:
        """Process chat query with RAG."""
        try:
            # Search for relevant content
            relevant_content = self.content_indexing.search_content(query, user_id)
            
            # Generate response (placeholder - would integrate with LLM)
            response = {
                "query": query,
                "response": "This is a placeholder response. RAG implementation would use relevant content to generate responses.",
                "sources": relevant_content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in RAG chat: {e}")
            return {
                "query": query,
                "response": "Sorry, I encountered an error processing your request.",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# ===== UTILITY FUNCTIONS =====

def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    return Path(filename).suffix.lower()


def get_mime_type_from_extension(extension: str) -> str:
    """Get MIME type from file extension."""
    mime_types = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    return mime_types.get(extension.lower(), 'application/octet-stream')


def is_safe_filename(filename: str) -> bool:
    """Check if filename is safe for storage."""
    # Check for directory traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    
    # Check for problematic characters
    problematic_chars = ['<', '>', ':', '"', '|', '?', '*']
    for char in problematic_chars:
        if char in filename:
            return False
    
    return True


def generate_unique_filename(original_filename: str, user_id: int, timestamp: str = None) -> str:
    """Generate unique filename for storage."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    name, ext = os.path.splitext(original_filename)
    clean_name = clean_title(name)[:50]  # Limit to 50 chars after cleaning
    
    return f"{user_id}_{timestamp}_{clean_name}{ext}"


def create_temp_file(content: bytes, suffix: str = "") -> str:
    """Create temporary file with content."""
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(content)
        return tmp_file.name


def cleanup_temp_file(file_path: str):
    """Clean up temporary file."""
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to cleanup temp file {file_path}: {e}")


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to specified length with ellipsis."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..." 