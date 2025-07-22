"""
Input validation utilities for the notebooks module.
Provides comprehensive validation for files and URLs.
"""

import os
import magic
from typing import Dict, List, Union
from pathlib import Path
from urllib.parse import urlparse
from django.core.files.uploadedfile import UploadedFile
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator as DjangoURLValidator

# Constants for file validation
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_FILE_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp4": "video/mp4",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".flv": "video/x-flv",
    ".wmv": "video/x-ms-wmv",
    ".3gp": "video/3gpp",
    ".ogv": "video/ogg",
    ".m4v": "video/x-m4v",
}


class FileValidator:
    """Enhanced file validation with security checks."""

    def __init__(self):
        self.max_file_size = MAX_FILE_SIZE
        self.allowed_extensions = ALLOWED_FILE_EXTENSIONS

    def validate_file(self, file: Union[UploadedFile, any]) -> Dict[str, any]:
        """Validate uploaded file with comprehensive checks."""
        errors = []
        warnings = []

        # Basic file checks
        if not file:
            return {"valid": False, "errors": ["No file provided"]}

        if not hasattr(file, 'name') or not file.name:
            return {"valid": False, "errors": ["File has no name"]}

        # File size validation
        try:
            file_size = file.size if hasattr(file, 'size') else len(file.read())
            if file_size > self.max_file_size:
                errors.append(f"File size {file_size} bytes exceeds maximum {self.max_file_size} bytes")
        except Exception as e:
            warnings.append(f"Could not determine file size: {e}")

        # File extension validation
        file_path = Path(file.name)
        file_extension = file_path.suffix.lower()
        
        if file_extension not in self.allowed_extensions:
            errors.append(f"File extension '{file_extension}' not allowed. Allowed: {list(self.allowed_extensions.keys())}")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "file_extension": file_extension,
                "content_type": None
            }

        # Content type validation
        expected_content_type = self.allowed_extensions[file_extension]
        actual_content_type = getattr(file, 'content_type', None)

        if actual_content_type and actual_content_type != expected_content_type:
            # Check for common variations
            content_type_variations = {
                "application/pdf": ["application/x-pdf"],
                "text/plain": ["text/x-python", "application/x-python-code"],
                "text/markdown": ["text/x-markdown"],
                "audio/mpeg": ["audio/mp3"],
                "video/mp4": ["video/mp4v-es"],
            }
            
            variations = content_type_variations.get(expected_content_type, [])
            if actual_content_type not in variations:
                warnings.append(f"Content type mismatch: expected {expected_content_type}, got {actual_content_type}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "file_extension": file_extension,
            "content_type": expected_content_type
        }

    def validate_file_content(self, file_path: str) -> Dict[str, any]:
        """Validate file content using magic number detection."""
        errors = []
        warnings = []

        if not os.path.exists(file_path):
            return {"valid": False, "errors": ["File does not exist"]}

        try:
            # Use python-magic to detect actual file type
            detected_type = magic.from_file(file_path, mime=True)
            file_extension = Path(file_path).suffix.lower()
            expected_type = self.allowed_extensions.get(file_extension)

            if expected_type and detected_type != expected_type:
                # Check for acceptable variations
                type_variations = {
                    "application/pdf": ["application/x-pdf"],
                    "text/plain": ["text/x-python", "application/x-python-code", "inode/x-empty"],
                    "text/markdown": ["text/plain", "text/x-markdown"],
                    "audio/mpeg": ["audio/mp3"],
                    "video/mp4": ["video/mp4v-es"],
                }
                
                variations = type_variations.get(expected_type, [])
                if detected_type not in variations:
                    errors.append(f"File content type mismatch: expected {expected_type}, detected {detected_type}")

        except Exception as e:
            warnings.append(f"Could not validate file content: {e}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


class URLValidator:
    """Validate URLs for processing."""
    
    BLOCKED_DOMAINS = {'localhost', '127.0.0.1', '0.0.0.0'}
    ALLOWED_SCHEMES = {'http', 'https'}
    
    def __init__(self):
        self.django_validator = DjangoURLValidator()
    
    def validate_url(self, url: str) -> Dict[str, any]:
        """Validate URL format and security."""
        errors = []
        warnings = []
        
        if not url:
            return {"valid": False, "errors": ["No URL provided"]}
        
        # Basic format validation
        try:
            self.django_validator(url)
        except ValidationError as e:
            errors.append(f"Invalid URL format: {e}")
            return {"valid": False, "errors": errors}
        
        # Parse URL for additional checks
        try:
            parsed = urlparse(url)
        except Exception as e:
            errors.append(f"Could not parse URL: {e}")
            return {"valid": False, "errors": errors}
        
        # Scheme validation
        if parsed.scheme.lower() not in self.ALLOWED_SCHEMES:
            errors.append(f"URL scheme '{parsed.scheme}' not allowed. Allowed: {list(self.ALLOWED_SCHEMES)}")
        
        # Domain validation
        if parsed.netloc.lower() in self.BLOCKED_DOMAINS:
            errors.append(f"Domain '{parsed.netloc}' is blocked")
        
        # Check for private IP ranges (basic check)
        if parsed.netloc.startswith('192.168.') or parsed.netloc.startswith('10.'):
            warnings.append("URL appears to point to private network")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "parsed_url": parsed
        }


def validate_file_type(filename: str) -> bool:
    """Quick file type validation by extension."""
    file_extension = Path(filename).suffix.lower()
    return file_extension in ALLOWED_FILE_EXTENSIONS


def get_content_type_for_extension(extension: str) -> str:
    """Get expected content type for file extension."""
    return ALLOWED_FILE_EXTENSIONS.get(extension.lower(), "application/octet-stream")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    # Remove any path components
    filename = os.path.basename(filename)
    
    # Replace problematic characters
    problematic_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    for char in problematic_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename 