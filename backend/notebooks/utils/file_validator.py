"""
Enhanced file validation service.
"""

import os
import magic
from typing import Dict, List, Union
from pathlib import Path
from django.core.files.uploadedfile import UploadedFile

try:
    from .config import config as settings
except ImportError:
    settings = None

# Constants for file validation
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_FILE_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
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

        # Check filename
        if not file.name:
            errors.append("Filename is required")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Check for potentially dangerous filenames
        if any(char in file.name for char in ["<", ">", ":", '"', "|", "?", "*"]):
            errors.append("Filename contains invalid characters")

        # Check file extension
        file_extension = Path(file.name).suffix.lower()
        if file_extension not in self.allowed_extensions:
            errors.append(
                f"File type {file_extension} is not supported. Allowed types: {', '.join(self.allowed_extensions.keys())}"
            )

        # Check file size (if available)
        if hasattr(file, "size") and file.size:
            if file.size > self.max_file_size:
                errors.append(
                    f"File size {file.size / (1024 * 1024):.1f}MB exceeds maximum allowed size of {self.max_file_size / (1024 * 1024):.0f}MB"
                )
            elif file.size < 100:  # Less than 100 bytes is suspicious
                warnings.append("File is very small and may be empty")

        # Check MIME type if available
        content_type = getattr(file, "content_type", None)
        expected_content_type = self.allowed_extensions.get(file_extension)
        if (
            content_type
            and expected_content_type
            and not content_type.startswith(expected_content_type.split("/")[0])
        ):
            warnings.append(
                f"MIME type {content_type} doesn't match file extension {file_extension}"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "file_extension": file_extension,
            "content_type": self.allowed_extensions.get(file_extension),
        }

    def validate_file_content(self, file_path: str) -> Dict[str, any]:
        """Validate file content using python-magic for security."""
        try:
            # Get MIME type from actual file content
            mime_type = magic.from_file(file_path, mime=True)

            # Get file extension
            file_extension = Path(file_path).suffix.lower()
            expected_mime = self.allowed_extensions.get(file_extension)

            warnings = []
            errors = []

            # Check if MIME type matches extension
            if expected_mime and not mime_type.startswith(expected_mime.split("/")[0]):
                warnings.append(
                    f"File content MIME type {mime_type} doesn't match extension {file_extension}"
                )

            # Check for potentially malicious files
            dangerous_types = [
                "application/x-executable",
                "application/x-dosexec",
                "application/javascript",
            ]
            if mime_type in dangerous_types:
                errors.append(
                    f"File type {mime_type} is not allowed for security reasons"
                )

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "detected_mime_type": mime_type,
                "file_extension": file_extension,
            }

        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Could not validate file content: {str(e)}"],
                "warnings": [],
                "detected_mime_type": "unknown",
                "file_extension": Path(file_path).suffix.lower(),
            }

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return list(self.allowed_extensions.keys())

    def is_media_file(self, file_extension: str) -> bool:
        """Check if file is a media file (audio/video)."""
        media_extensions = [".mp3", ".wav", ".m4a", ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".3gp", ".ogv", ".m4v"]
        return file_extension.lower() in media_extensions

    def is_document_file(self, file_extension: str) -> bool:
        """Check if file is a document file."""
        doc_extensions = [".pdf", ".txt", ".md", ".ppt", ".pptx"]
        return file_extension.lower() in doc_extensions
