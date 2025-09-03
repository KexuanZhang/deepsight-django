"""
MinIO storage implementation following the storage interface.
"""

import logging
from typing import Dict, Optional
from django.conf import settings
from minio import Minio
from minio.error import S3Error
from .base import StorageInterface


class MinIOStorage(StorageInterface):
    """
    MinIO storage backend implementation.
    
    Implements the StorageInterface for MinIO object storage,
    providing a clean abstraction over MinIO client operations.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._client = None
        self._bucket_name = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize MinIO client with settings from Django configuration."""
        try:
            minio_settings = getattr(settings, 'MINIO_SETTINGS', {})
            
            self._client = Minio(
                endpoint=minio_settings.get('ENDPOINT', 'localhost:9000'),
                access_key=minio_settings.get('ACCESS_KEY', 'minioadmin'),
                secret_key=minio_settings.get('SECRET_KEY', 'minioadmin'),
                secure=minio_settings.get('SECURE', False)
            )
            
            self._bucket_name = minio_settings.get('BUCKET_NAME', 'deepsight-users')
            
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
            self.logger.info(f"MinIO client initialized for bucket: {self._bucket_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MinIO client: {e}")
            raise
    
    def _ensure_bucket_exists(self):
        """Ensure the configured bucket exists."""
        try:
            if not self._client.bucket_exists(self._bucket_name):
                self._client.make_bucket(self._bucket_name)
                self.logger.info(f"Created MinIO bucket: {self._bucket_name}")
        except S3Error as e:
            self.logger.error(f"Failed to create/check bucket {self._bucket_name}: {e}")
            raise
    
    def save_file(self, file_content: bytes, object_key: str, 
                  content_type: str = None, metadata: Dict = None) -> str:
        """Save file content to MinIO storage."""
        try:
            from io import BytesIO
            
            file_data = BytesIO(file_content)
            file_size = len(file_content)
            
            # Prepare metadata
            minio_metadata = {}
            if metadata:
                # Convert all metadata values to strings for MinIO
                minio_metadata = {k: str(v) for k, v in metadata.items()}
            
            self._client.put_object(
                bucket_name=self._bucket_name,
                object_name=object_key,
                data=file_data,
                length=file_size,
                content_type=content_type or 'application/octet-stream',
                metadata=minio_metadata
            )
            
            self.logger.info(f"File saved to MinIO: {object_key}")
            return f"minio://{self._bucket_name}/{object_key}"
            
        except S3Error as e:
            self.logger.error(f"Failed to save file {object_key}: {e}")
            raise
    
    def get_file(self, object_key: str) -> Optional[bytes]:
        """Retrieve file content from MinIO storage."""
        try:
            response = self._client.get_object(self._bucket_name, object_key)
            content = response.read()
            response.close()
            response.release_conn()
            
            self.logger.debug(f"File retrieved from MinIO: {object_key}")
            return content
            
        except S3Error as e:
            if e.code == 'NoSuchKey':
                self.logger.debug(f"File not found in MinIO: {object_key}")
                return None
            else:
                self.logger.error(f"Failed to get file {object_key}: {e}")
                raise
    
    def delete_file(self, object_key: str) -> bool:
        """Delete file from MinIO storage."""
        try:
            self._client.remove_object(self._bucket_name, object_key)
            self.logger.info(f"File deleted from MinIO: {object_key}")
            return True
            
        except S3Error as e:
            if e.code == 'NoSuchKey':
                self.logger.debug(f"File not found for deletion: {object_key}")
                return True  # Consider non-existent file as successfully "deleted"
            else:
                self.logger.error(f"Failed to delete file {object_key}: {e}")
                return False
    
    def file_exists(self, object_key: str) -> bool:
        """Check if file exists in MinIO storage."""
        try:
            self._client.stat_object(self._bucket_name, object_key)
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            else:
                self.logger.error(f"Failed to check file existence {object_key}: {e}")
                return False
    
    def get_file_url(self, object_key: str, expires: int = 3600) -> Optional[str]:
        """Get a pre-signed URL for accessing the file."""
        try:
            from datetime import timedelta
            
            url = self._client.presigned_get_object(
                bucket_name=self._bucket_name,
                object_name=object_key,
                expires=timedelta(seconds=expires)
            )
            
            self.logger.debug(f"Pre-signed URL generated for: {object_key}")
            return url
            
        except S3Error as e:
            self.logger.error(f"Failed to generate URL for {object_key}: {e}")
            return None
    
    def get_file_metadata(self, object_key: str) -> Optional[Dict]:
        """Get metadata for a file in MinIO storage."""
        try:
            stat = self._client.stat_object(self._bucket_name, object_key)
            
            metadata = {
                'size': stat.size,
                'content_type': stat.content_type,
                'last_modified': stat.last_modified,
                'etag': stat.etag,
                'version_id': stat.version_id,
            }
            
            # Add custom metadata if available
            if stat.metadata:
                metadata['custom_metadata'] = dict(stat.metadata)
            
            return metadata
            
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return None
            else:
                self.logger.error(f"Failed to get metadata for {object_key}: {e}")
                return None
    
    def list_files(self, prefix: str = "", limit: int = 100) -> list:
        """List files with optional prefix filter."""
        try:
            objects = self._client.list_objects(
                bucket_name=self._bucket_name,
                prefix=prefix,
                recursive=True
            )
            
            file_list = []
            count = 0
            
            for obj in objects:
                if count >= limit:
                    break
                file_list.append(obj.object_name)
                count += 1
            
            self.logger.debug(f"Listed {len(file_list)} files with prefix: {prefix}")
            return file_list
            
        except S3Error as e:
            self.logger.error(f"Failed to list files with prefix {prefix}: {e}")
            return []