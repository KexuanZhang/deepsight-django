"""
MinIO backend service for object storage operations.
Replaces local file storage with cloud-native MinIO object storage.
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from urllib.parse import urlparse

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    Minio = None
    S3Error = Exception

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class MinIOBackend:
    """MinIO-native object storage backend."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.minio_backend")
        
        # Load MinIO configuration from Django settings
        self.minio_config = getattr(settings, 'MINIO_SETTINGS', {})
        
        if not self.minio_config:
            raise ImproperlyConfigured("MINIO_SETTINGS not configured in Django settings")
        
        # Validate required configuration
        required_keys = ['ENDPOINT', 'ACCESS_KEY', 'SECRET_KEY', 'BUCKET_NAME']
        missing_keys = [key for key in required_keys if key not in self.minio_config]
        if missing_keys:
            raise ImproperlyConfigured(f"Missing MinIO configuration keys: {missing_keys}")
        
        # Initialize MinIO client
        if not Minio:
            raise ImproperlyConfigured("MinIO package not installed. Run: pip install minio")
        
        self.client = Minio(
            endpoint=self.minio_config['ENDPOINT'],
            access_key=self.minio_config['ACCESS_KEY'],
            secret_key=self.minio_config['SECRET_KEY'],
            secure=self.minio_config.get('SECURE', False),
            region=self.minio_config.get('REGION', 'us-east-1')
        )
        
        self.bucket_name = self.minio_config['BUCKET_NAME']
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
        
        self.logger.info(f"MinIO backend initialized - endpoint: {self.minio_config['ENDPOINT']}, bucket: {self.bucket_name}")
    
    def _ensure_bucket_exists(self):
        """Ensure the MinIO bucket exists."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(
                    self.bucket_name,
                    location=self.minio_config.get('REGION', 'us-east-1')
                )
                self.logger.info(f"Created MinIO bucket: {self.bucket_name}")
            else:
                self.logger.debug(f"MinIO bucket exists: {self.bucket_name}")
        except S3Error as e:
            self.logger.error(f"Failed to ensure bucket exists: {e}")
            raise
    
    def _generate_object_key(self, prefix: str, filename: str, content_hash: str = None, user_id: str = None) -> str:
        """
        Generate MinIO object key using the pattern: {user_id}/{prefix}/{timestamp}_{content_hash}_{uuid}{extension}
        
        Args:
            prefix: Object prefix (kb, reports, podcasts, kb-images, temp)
            filename: Original filename
            content_hash: First 16 chars of content SHA256 hash (optional)
            user_id: User ID for folder organization (optional)
            
        Returns:
            Generated object key
        """
        # Extract extension
        if '.' in filename:
            _, extension = filename.rsplit('.', 1)
            extension = f".{extension}"
        else:
            extension = ""
        
        # Generate timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        # Generate short UUID
        short_uuid = str(uuid.uuid4()).replace('-', '')[:8]
        
        # Use provided content hash or generate a random one
        if content_hash:
            hash_part = content_hash[:16]
        else:
            hash_part = hashlib.sha256(f"{timestamp}_{short_uuid}".encode()).hexdigest()[:16]
        
        # Generate object key with user_id prefix if provided
        if user_id:
            object_key = f"{user_id}/{prefix}/{timestamp}_{hash_part}_{short_uuid}{extension}"
        else:
            object_key = f"{prefix}/{timestamp}_{hash_part}_{short_uuid}{extension}"
        
        self.logger.debug(f"Generated object key: {object_key}")
        return object_key
    
    def save_file_with_auto_key(
        self, 
        content: bytes, 
        filename: str, 
        prefix: str, 
        content_type: str = None,
        metadata: Dict[str, str] = None,
        user_id: str = None
    ) -> str:
        """
        Save file to MinIO with auto-generated object key.
        
        Args:
            content: File content as bytes
            filename: Original filename
            prefix: Storage prefix (kb, reports, podcasts, etc.)
            content_type: MIME content type
            metadata: Additional metadata
            user_id: User ID for folder organization
            
        Returns:
            Generated object key
        """
        try:
            # Calculate content hash for deduplication
            content_hash = hashlib.sha256(content).hexdigest()
            
            # Generate object key
            object_key = self._generate_object_key(prefix, filename, content_hash, user_id)
            
            # Prepare metadata
            object_metadata = {
                'original_filename': filename,
                'content_hash': content_hash,
                'upload_timestamp': datetime.now(timezone.utc).isoformat(),
            }
            if metadata:
                object_metadata.update(metadata)
            
            # Determine content type
            if not content_type:
                import mimetypes
                content_type, _ = mimetypes.guess_type(filename)
                content_type = content_type or 'application/octet-stream'
            
            # Upload to MinIO
            content_stream = BytesIO(content)
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=content_stream,
                length=len(content),
                content_type=content_type,
                metadata=object_metadata
            )
            
            self.logger.info(f"Saved file to MinIO: {object_key} ({len(content)} bytes)")
            return object_key
            
        except S3Error as e:
            self.logger.error(f"Failed to save file to MinIO: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error saving file to MinIO: {e}")
            raise
    
    def get_file_content(self, object_key: str) -> bytes:
        """
        Retrieve file content from MinIO.
        
        Args:
            object_key: MinIO object key
            
        Returns:
            File content as bytes
        """
        try:
            response = self.client.get_object(self.bucket_name, object_key)
            content = response.read()
            response.close()
            response.release_conn()
            
            self.logger.debug(f"Retrieved file from MinIO: {object_key} ({len(content)} bytes)")
            return content
            
        except S3Error as e:
            self.logger.error(f"Failed to retrieve file from MinIO: {object_key} - {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving file from MinIO: {object_key} - {e}")
            raise
    
    def get_file_url(self, object_key: str, expires: int = 3600) -> str:
        """
        Generate pre-signed URL for file access.
        
        Args:
            object_key: MinIO object key
            expires: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Pre-signed URL
        """
        try:
            from datetime import timedelta
            
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_key,
                expires=timedelta(seconds=expires)
            )
            
            self.logger.debug(f"Generated pre-signed URL for: {object_key}")
            return url
            
        except S3Error as e:
            self.logger.error(f"Failed to generate pre-signed URL: {object_key} - {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error generating pre-signed URL: {object_key} - {e}")
            raise
    
    def delete_file(self, object_key: str) -> bool:
        """
        Delete file from MinIO.
        
        Args:
            object_key: MinIO object key
            
        Returns:
            True if deleted successfully
        """
        try:
            self.client.remove_object(self.bucket_name, object_key)
            self.logger.info(f"Deleted file from MinIO: {object_key}")
            return True
            
        except S3Error as e:
            self.logger.error(f"Failed to delete file from MinIO: {object_key} - {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error deleting file from MinIO: {object_key} - {e}")
            return False
    
    def file_exists(self, object_key: str) -> bool:
        """
        Check if file exists in MinIO.
        
        Args:
            object_key: MinIO object key
            
        Returns:
            True if file exists
        """
        try:
            self.client.stat_object(self.bucket_name, object_key)
            return True
        except S3Error:
            return False
        except Exception as e:
            self.logger.error(f"Error checking file existence: {object_key} - {e}")
            return False
    
    def get_file_metadata(self, object_key: str) -> Dict[str, Any]:
        """
        Get file metadata from MinIO.
        
        Args:
            object_key: MinIO object key
            
        Returns:
            File metadata dictionary
        """
        try:
            stat = self.client.stat_object(self.bucket_name, object_key)
            
            metadata = {
                'size': stat.size,
                'etag': stat.etag,
                'last_modified': stat.last_modified,
                'content_type': stat.content_type,
                'metadata': stat.metadata or {}
            }
            
            self.logger.debug(f"Retrieved metadata for: {object_key}")
            return metadata
            
        except S3Error as e:
            self.logger.error(f"Failed to get metadata: {object_key} - {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error getting metadata: {object_key} - {e}")
            raise
    
    def list_files_by_prefix(self, prefix: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        List files by prefix.
        
        Args:
            prefix: Object prefix to filter by
            limit: Maximum number of files to return
            
        Returns:
            List of file information dictionaries
        """
        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            
            files = []
            count = 0
            for obj in objects:
                if count >= limit:
                    break
                
                files.append({
                    'object_key': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified,
                    'etag': obj.etag
                })
                count += 1
            
            self.logger.debug(f"Listed {len(files)} files with prefix: {prefix}")
            return files
            
        except S3Error as e:
            self.logger.error(f"Failed to list files with prefix {prefix}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error listing files with prefix {prefix}: {e}")
            raise
    
    def copy_file(self, source_object_key: str, dest_object_key: str) -> bool:
        """
        Copy file within MinIO.
        
        Args:
            source_object_key: Source object key
            dest_object_key: Destination object key
            
        Returns:
            True if copied successfully
        """
        try:
            from minio.commonconfig import CopySource
            
            copy_source = CopySource(self.bucket_name, source_object_key)
            self.client.copy_object(self.bucket_name, dest_object_key, copy_source)
            
            self.logger.info(f"Copied file in MinIO: {source_object_key} -> {dest_object_key}")
            return True
            
        except S3Error as e:
            self.logger.error(f"Failed to copy file in MinIO: {source_object_key} -> {dest_object_key} - {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error copying file in MinIO: {source_object_key} -> {dest_object_key} - {e}")
            return False
    
    def get_bucket_stats(self) -> Dict[str, Any]:
        """
        Get basic bucket statistics.
        
        Returns:
            Bucket statistics dictionary
        """
        try:
            # Count objects by prefix
            prefixes = ['kb', 'reports', 'podcasts', 'kb-images', 'temp']
            stats = {
                'bucket_name': self.bucket_name,
                'total_objects': 0,
                'prefixes': {}
            }
            
            for prefix in prefixes:
                objects = list(self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True))
                count = len(objects)
                total_size = sum(obj.size for obj in objects)
                
                stats['prefixes'][prefix] = {
                    'count': count,
                    'total_size': total_size
                }
                stats['total_objects'] += count
            
            self.logger.debug(f"Retrieved bucket stats: {stats}")
            return stats
            
        except S3Error as e:
            self.logger.error(f"Failed to get bucket stats: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error getting bucket stats: {e}")
            raise


# Global singleton instance
_minio_backend = None

def get_minio_backend() -> MinIOBackend:
    """Get the global MinIO backend instance."""
    global _minio_backend
    if _minio_backend is None:
        _minio_backend = MinIOBackend()
    return _minio_backend