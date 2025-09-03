"""
Core exception classes for the DeepSight application.
"""


class DeepSightException(Exception):
    """Base exception class for DeepSight application."""
    pass


class ValidationError(DeepSightException):
    """Raised when data validation fails."""
    pass


class ProcessingError(DeepSightException):
    """Raised when content processing fails."""
    pass


class StorageError(DeepSightException):
    """Raised when storage operations fail."""
    pass


class SearchError(DeepSightException):
    """Raised when search operations fail."""
    pass


class AIServiceError(DeepSightException):
    """Raised when AI service operations fail."""
    pass