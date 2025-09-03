"""
Abstract storage interface following Dependency Inversion Principle.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, BinaryIO
from pathlib import Path


class StorageInterface(ABC):
    """
    Abstract interface for storage operations.
    
    This interface allows different storage backends (MinIO, S3, local filesystem)
    to be used interchangeably without changing business logic.
    """
    
    @abstractmethod
    def save_file(self, file_content: bytes, object_key: str, 
                  content_type: str = None, metadata: Dict = None) -> str:
        """
        Save file content to storage.
        
        Args:
            file_content: Binary content of the file
            object_key: Unique key/path for the file
            content_type: MIME type of the file
            metadata: Additional metadata for the file
            
        Returns:
            Storage URL or identifier for the saved file
        """
        pass
    
    @abstractmethod
    def get_file(self, object_key: str) -> Optional[bytes]:
        """
        Retrieve file content from storage.
        
        Args:
            object_key: Key/path of the file
            
        Returns:
            File content as bytes, or None if not found
        """
        pass
    
    @abstractmethod
    def delete_file(self, object_key: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            object_key: Key/path of the file
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def file_exists(self, object_key: str) -> bool:
        """
        Check if file exists in storage.
        
        Args:
            object_key: Key/path of the file
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_file_url(self, object_key: str, expires: int = 3600) -> Optional[str]:
        """
        Get a URL for accessing the file.
        
        Args:
            object_key: Key/path of the file
            expires: URL expiration time in seconds
            
        Returns:
            Accessible URL for the file, or None if not available
        """
        pass
    
    @abstractmethod
    def get_file_metadata(self, object_key: str) -> Optional[Dict]:
        """
        Get metadata for a file.
        
        Args:
            object_key: Key/path of the file
            
        Returns:
            Dictionary with file metadata, or None if not found
        """
        pass
    
    @abstractmethod
    def list_files(self, prefix: str = "", limit: int = 100) -> list:
        """
        List files with optional prefix filter.
        
        Args:
            prefix: Prefix to filter files
            limit: Maximum number of files to return
            
        Returns:
            List of file keys/paths
        """
        pass