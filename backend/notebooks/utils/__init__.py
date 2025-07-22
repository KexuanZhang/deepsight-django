"""
Notebooks utilities package.

This package provides organized utilities for the DeepSight notebooks application:
- validators.py: Input validation for files and URLs
- storage.py: Storage operations using MinIO backend
- helpers.py: Common utilities and configuration
"""

# Core configuration
from .helpers import config, NotebooksConfig

# Validators
from .validators import (
    FileValidator,
    URLValidator,
    validate_file_type,
    get_content_type_for_extension,
    sanitize_filename,
    ALLOWED_FILE_EXTENSIONS,
    MAX_FILE_SIZE
)

# Storage operations
from .storage import (
    FileStorageService,
    StorageAdapter,
    MinIOBackend,
    get_storage_adapter,
    get_minio_backend
)

# Helper utilities and services
from .helpers import (
    clean_title,
    calculate_content_hash,
    check_duplicate_before_processing,
    extract_domain,
    sanitize_path,
    get_file_extension,
    get_mime_type_from_extension,
    is_safe_filename,
    generate_unique_filename,
    create_temp_file,
    cleanup_temp_file,
    format_file_size,
    truncate_text,
    ContentIndexingService,
    RAGChatbot,
    NotebookPermissionMixin,
    ErrorHandlingMixin,
    AsyncResponseMixin
)

# Legacy imports with fallbacks for backward compatibility
try:
    from ..processors.upload_processor import UploadProcessor
except ImportError:
    UploadProcessor = None

try:
    from ..processors.url_extractor import URLExtractor
except ImportError:
    URLExtractor = None

try:
    from ..processors.media_processors import MediaProcessor
except ImportError:
    MediaProcessor = None

# RAG import with fallback
try:
    from rag.rag import RAGChatbot as ExternalRAGChatbot
except ImportError:
    ExternalRAGChatbot = None

__all__ = [
    # Configuration
    'config',
    'NotebooksConfig',
    
    # Validators
    'FileValidator',
    'URLValidator',
    'validate_file_type',
    'get_content_type_for_extension',
    'sanitize_filename',
    'ALLOWED_FILE_EXTENSIONS',
    'MAX_FILE_SIZE',
    
    # Storage
    'FileStorageService',
    'StorageAdapter',
    'MinIOBackend',
    'get_storage_adapter',
    'get_minio_backend',
    
    # Helpers
    'clean_title',
    'calculate_content_hash',
    'check_duplicate_before_processing',
    'extract_domain',
    'sanitize_path',
    'get_file_extension',
    'get_mime_type_from_extension',
    'is_safe_filename',
    'generate_unique_filename',
    'create_temp_file',
    'cleanup_temp_file',
    'format_file_size',
    'truncate_text',
    'ContentIndexingService',
    'RAGChatbot',
    'NotebookPermissionMixin',
    'ErrorHandlingMixin',
    'AsyncResponseMixin',
    
    # Legacy processors (may be None if not available)
    'UploadProcessor',
    'URLExtractor',
    'MediaProcessor',
    'ExternalRAGChatbot'
]