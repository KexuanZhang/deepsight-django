"""
Custom exceptions for the notebooks module.
"""

from rest_framework import status
from rest_framework.views import exception_handler
from rest_framework.response import Response


class NotebooksException(Exception):
    """Base exception for notebooks module."""
    
    default_message = "An error occurred in the notebooks module"
    default_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def __init__(self, message=None, status_code=None, details=None):
        self.message = message or self.default_message
        self.status_code = status_code or self.default_status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(NotebooksException):
    """Exception for validation errors."""
    
    default_message = "Validation failed"
    default_status_code = status.HTTP_400_BAD_REQUEST


class FileProcessingError(NotebooksException):
    """Exception for file processing errors."""
    
    default_message = "File processing failed"
    default_status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class URLProcessingError(NotebooksException):
    """Exception for URL processing errors."""
    
    default_message = "URL processing failed"
    default_status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class StorageError(NotebooksException):
    """Exception for storage-related errors."""
    
    default_message = "Storage operation failed"
    default_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class NotebookNotFoundError(NotebooksException):
    """Exception when notebook is not found or access denied."""
    
    default_message = "Notebook not found or access denied"
    default_status_code = status.HTTP_404_NOT_FOUND


class FileNotFoundError(NotebooksException):
    """Exception when file is not found."""
    
    default_message = "File not found"
    default_status_code = status.HTTP_404_NOT_FOUND


class ProcessingTimeoutError(NotebooksException):
    """Exception for processing timeout."""
    
    default_message = "Processing operation timed out"
    default_status_code = status.HTTP_408_REQUEST_TIMEOUT


class ServiceUnavailableError(NotebooksException):
    """Exception when external service is unavailable."""
    
    default_message = "External service unavailable"
    default_status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class AuthenticationError(NotebooksException):
    """Exception for authentication errors."""
    
    default_message = "Authentication failed"
    default_status_code = status.HTTP_401_UNAUTHORIZED


class PermissionError(NotebooksException):
    """Exception for permission errors."""
    
    default_message = "Permission denied"
    default_status_code = status.HTTP_403_FORBIDDEN


class RateLimitError(NotebooksException):
    """Exception for rate limiting."""
    
    default_message = "Rate limit exceeded"
    default_status_code = status.HTTP_429_TOO_MANY_REQUESTS


class ConfigurationError(NotebooksException):
    """Exception for configuration errors."""
    
    default_message = "Configuration error"
    default_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


def custom_exception_handler(exc, context):
    """Custom exception handler for notebooks exceptions."""
    
    # Handle notebooks-specific exceptions
    if isinstance(exc, NotebooksException):
        return Response(
            {
                'error': exc.message,
                'details': exc.details,
                'status_code': exc.status_code
            },
            status=exc.status_code
        )
    
    # Fall back to default handler for other exceptions
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            'error': 'An error occurred',
            'details': response.data,
            'status_code': response.status_code
        }
        response.data = custom_response_data
    
    return response


# Utility functions for common error patterns
def raise_validation_error(message, details=None):
    """Raise a validation error with message and details."""
    raise ValidationError(message=message, details=details)


def raise_file_processing_error(message, details=None):
    """Raise a file processing error with message and details."""
    raise FileProcessingError(message=message, details=details)


def raise_url_processing_error(message, details=None):
    """Raise a URL processing error with message and details."""
    raise URLProcessingError(message=message, details=details)


def raise_storage_error(message, details=None):
    """Raise a storage error with message and details."""
    raise StorageError(message=message, details=details)


def raise_not_found_error(resource_type, resource_id=None):
    """Raise a not found error for a specific resource."""
    message = f"{resource_type} not found"
    if resource_id:
        message += f" (ID: {resource_id})"
    
    if resource_type.lower() == 'notebook':
        raise NotebookNotFoundError(message=message)
    elif resource_type.lower() == 'file':
        raise FileNotFoundError(message=message)
    else:
        raise NotebooksException(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND
        ) 