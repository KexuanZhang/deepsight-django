"""
Factory for creating file storage handlers.
"""

import shutil
import logging
import os
import io
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from django.core.files.base import ContentFile
from ..interfaces.file_storage_interface import FileStorageInterface

logger = logging.getLogger(__name__)


class DjangoFileStorage(FileStorageInterface):
    """Django-based file storage implementation"""
    
    def create_output_directory(self, user_id: int, report_id: str, notebook_id: Optional[int] = None) -> Path:
        """Create output directory for report files"""
        try:
            from notebooks.utils.config import storage_config
            
            current_date = datetime.now()
            year_month = current_date.strftime('%Y-%m')
            
            output_dir = storage_config.get_report_path(
                user_id=user_id,
                year_month=year_month,
                report_id=report_id,
                notebook_id=notebook_id
            )
            
            # Clean existing directory if it exists
            if output_dir.exists():
                try:
                    shutil.rmtree(output_dir)
                    logger.info(f"Cleaned existing output directory: {output_dir}")
                except Exception as e:
                    logger.warning(f"Could not clean output directory {output_dir}: {e}")
            
            # Create the directory
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output directory: {output_dir}")
            
            return output_dir
            
        except Exception as e:
            logger.error(f"Error creating output directory: {e}")
            raise
    
    def store_generated_files(self, source_files: List[str], target_dir: Path) -> List[str]:
        """Store generated files and return list of stored file paths"""
        stored_files = []
        
        try:
            for file_path in source_files:
                try:
                    source_path = Path(file_path)
                    if not source_path.exists() or not source_path.is_file():
                        continue
                    
                    filename = source_path.name
                    target_path = target_dir / filename
                    
                    # Check if source and target are the same file (resolve to handle symlinks)
                    try:
                        source_resolved = source_path.resolve()
                        target_resolved = target_path.resolve()
                        
                        if source_resolved == target_resolved:
                            # File is already in the correct location, no need to copy
                            logger.info(f"File already in target location: {filename}")
                        else:
                            # Copy the file to target directory
                            shutil.copy2(source_path, target_path)
                            logger.info(f"Copied file: {filename} from {source_path} to {target_path}")
                    except Exception as copy_error:
                        # If path resolution fails, try a simple copy and handle same file error gracefully
                        try:
                            shutil.copy2(source_path, target_path)
                            logger.info(f"Copied file: {filename}")
                        except shutil.SameFileError:
                            # File is already in the correct location
                            logger.info(f"File already in target location: {filename}")
                        except Exception as e:
                            logger.warning(f"Failed to copy file {file_path}: {e}")
                            continue
                    
                    # Store relative path for database
                    relative_path = str(target_path.relative_to(target_dir.parent.parent.parent.parent))
                    stored_files.append(relative_path)
                    
                except Exception as e:
                    logger.warning(f"Failed to store file {file_path}: {e}")
                    continue
            
            return stored_files
            
        except Exception as e:
            logger.error(f"Error storing generated files: {e}")
            return stored_files
    
    def get_main_report_file(self, file_list: List[str]) -> Optional[str]:
        """Identify the main report file from a list of generated files and return absolute path"""
        # First, look specifically for report_{id}.md files (highest priority)
        for filename in file_list:
            basename = Path(filename).name
            if basename.startswith("report_") and basename.endswith(".md"):
                # If it's already an absolute path, return it
                if os.path.isabs(filename):
                    return filename
                # Otherwise, try to make it absolute
                try:
                    return str(Path(filename).absolute())
                except:
                    return filename
        
        # Look for polished files second
        for filename in file_list:
            basename = Path(filename).name
            if basename.endswith((".md", ".html", ".pdf")) and "polished" in basename.lower():
                if os.path.isabs(filename):
                    return filename
                try:
                    return str(Path(filename).absolute())
                except:
                    return filename
        
        # Look for any report files third
        for filename in file_list:
            basename = Path(filename).name
            if basename.endswith((".md", ".html", ".pdf")) and "report" in basename.lower():
                if os.path.isabs(filename):
                    return filename
                try:
                    return str(Path(filename).absolute())
                except:
                    return filename
        
        # Fallback to any markdown file
        for filename in file_list:
            if filename.endswith(".md"):
                if os.path.isabs(filename):
                    return filename
                try:
                    return str(Path(filename).absolute())
                except:
                    return filename
        
        return None
    
    def clean_output_directory(self, directory: Path) -> bool:
        """Clean an output directory before generation"""
        try:
            if directory.exists():
                shutil.rmtree(directory)
                logger.info(f"Cleaned output directory: {directory}")
            return True
        except Exception as e:
            logger.warning(f"Failed to clean output directory {directory}: {e}")
            return False
    
    def delete_report_files(self, report_id: str, user_id: int) -> bool:
        """Delete all files associated with a report"""
        try:
            from notebooks.utils.config import storage_config
            
            # Try to find the report directory
            # Since we don't know the exact year-month, we'll need to search
            user_dir = storage_config.get_user_storage_path(user_id)
            
            # Search for report directories
            report_dirs = []
            if user_dir.exists():
                # Look in both notebook-specific and general report directories
                for path in user_dir.rglob(f"r_{report_id}"):
                    if path.is_dir():
                        report_dirs.append(path)
            
            deleted_count = 0
            for report_dir in report_dirs:
                try:
                    shutil.rmtree(report_dir)
                    deleted_count += 1
                    logger.info(f"Deleted report directory: {report_dir}")
                except Exception as e:
                    logger.warning(f"Failed to delete report directory {report_dir}: {e}")
            
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting report files for report {report_id}: {e}")
            return False
    
    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get metadata for a specific file"""
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                return {}
            
            stat = path_obj.stat()
            return {
                "filename": path_obj.name,
                "size": stat.st_size,
                "type": path_obj.suffix.lower(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Failed to get metadata for {file_path}: {e}")
            return {}


class MinIOFileStorage(FileStorageInterface):
    """MinIO-based file storage implementation"""
    
    def __init__(self):
        """Initialize MinIO storage"""
        from notebooks.utils.storage import get_minio_backend
        self.minio_backend = get_minio_backend()
    
    def create_output_directory(self, user_id: int, report_id: str, notebook_id: Optional[int] = None) -> Path:
        """Create temporary directory for report generation, then upload to MinIO"""
        import tempfile
        
        # Always create a temporary directory for local processing
        # The files will be uploaded to MinIO later via store_generated_files
        temp_dir = tempfile.mkdtemp(prefix=f'report_{report_id}_')
        
        logger.info(f"Created temporary directory for MinIO report generation: {temp_dir}")
        
        return Path(temp_dir)
    
    def store_generated_files(self, source_files: List[str], user_id: int, report_id: str, notebook_id: Optional[int] = None) -> List[str]:
        """Store generated files in MinIO and return list of stored object keys"""
        stored_object_keys = []
        
        try:
            # Use the provided parameters to construct MinIO path
            notebook_part = notebook_id or 'standalone'

            # Process files
            for file_path in source_files:
                try:
                    source_path = Path(file_path)
                    if not source_path.exists() or not source_path.is_file():
                        continue
                    
                    filename = source_path.name
                    # Generate MinIO key
                    minio_key = f"{user_id}/notebook/{notebook_part}/report/{report_id}/{filename}"
                    
                    # Read file content
                    with open(source_path, 'rb') as f:
                        file_content = f.read()
                    
                    content_stream = io.BytesIO(file_content)
                    file_size = len(file_content)
                    
                    # Determine content type
                    content_type = "application/octet-stream"
                    if filename.endswith('.md'):
                        content_type = "text/markdown"
                    elif filename.endswith('.html'):
                        content_type = "text/html"
                    elif filename.endswith('.pdf'):
                        content_type = "application/pdf"
                    elif filename.endswith('.json'):
                        content_type = "application/json"
                    elif filename.endswith('.jsonl'):
                        content_type = "application/jsonl"
                    elif filename.endswith('.txt'):
                        content_type = "text/plain"
                    
                    # Upload to MinIO
                    self.minio_backend.client.put_object(
                        bucket_name=self.minio_backend.bucket_name,
                        object_name=minio_key,
                        data=content_stream,
                        length=file_size,
                        content_type=content_type
                    )
                    
                    stored_object_keys.append(minio_key)
                    logger.info(f"Stored file in MinIO: {minio_key}")
                    
                except Exception as e:
                    logger.warning(f"Failed to store file {file_path} in MinIO: {e}")
                    continue
            
            return stored_object_keys
            
        except Exception as e:
            logger.error(f"Error storing generated files in MinIO: {e}")
            return stored_object_keys
    
    def get_main_report_file(self, file_list: List[str]) -> Optional[str]:
        """Identify the main report file from a list of object keys"""
        # First, look specifically for report_{id}.md files (highest priority)
        for object_key in file_list:
            filename = Path(object_key).name
            if filename.startswith("report_") and filename.endswith(".md"):
                return object_key
        
        # Look for polished files second
        for object_key in file_list:
            filename = Path(object_key).name
            if filename.endswith((".md", ".html", ".pdf")) and "polished" in filename.lower():
                return object_key
        
        # Look for any report files third
        for object_key in file_list:
            filename = Path(object_key).name
            if filename.endswith((".md", ".html", ".pdf")) and "report" in filename.lower():
                return object_key
        
        # Fallback to any markdown file
        for object_key in file_list:
            if object_key.endswith(".md"):
                return object_key
        
        return None
    
    def _cleanup_temp_directory(self, temp_dir: Path) -> None:
        """Clean up temporary directory after successful upload to MinIO"""
        try:
            import shutil
            if temp_dir.exists() and temp_dir.is_dir():
                shutil.rmtree(str(temp_dir))
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")
    
    def cleanup_failed_generation(self, temp_dir: Path) -> None:
        """Clean up temporary directory for failed report generation"""
        try:
            self._cleanup_temp_directory(temp_dir)
            logger.info(f"Cleaned up failed generation temp directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up failed generation temp directory {temp_dir}: {e}")
    
    def clean_output_directory(self, directory: Path) -> bool:
        """Clean an output directory before generation (MinIO specific)"""
        try:
            # For MinIO, we need to delete objects with the prefix
            prefix = str(directory).replace('minio://', '') + "/"
            
            # List and delete objects with this prefix
            objects = self.minio_backend.client.list_objects(
                bucket_name=self.minio_backend.bucket_name,
                prefix=prefix,
                recursive=True
            )
            
            for obj in objects:
                self.minio_backend.client.remove_object(
                    bucket_name=self.minio_backend.bucket_name,
                    object_name=obj.object_name
                )
                logger.info(f"Deleted MinIO object: {obj.object_name}")
            
            return True
        except Exception as e:
            logger.warning(f"Failed to clean MinIO directory {directory}: {e}")
            return False
    
    def delete_report_files(self, report_id: str, user_id: int) -> bool:
        """Delete all files associated with a report from MinIO"""
        try:
            # Search for objects with the pattern user_id/*/report/report_id/*
            prefix = f"{user_id}/"
            
            objects = self.minio_backend.client.list_objects(
                bucket_name=self.minio_backend.bucket_name,
                prefix=prefix,
                recursive=True
            )
            
            deleted_count = 0
            for obj in objects:
                # Check if this object belongs to the report
                if f"/report/{report_id}/" in obj.object_name:
                    try:
                        self.minio_backend.client.remove_object(
                            bucket_name=self.minio_backend.bucket_name,
                            object_name=obj.object_name
                        )
                        deleted_count += 1
                        logger.info(f"Deleted MinIO object: {obj.object_name}")
                    except Exception as e:
                        logger.warning(f"Failed to delete MinIO object {obj.object_name}: {e}")
            
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting report files from MinIO for report {report_id}: {e}")
            return False
    
    def get_file_metadata(self, object_key: str) -> Dict[str, Any]:
        """Get metadata for a specific MinIO object"""
        try:
            stat = self.minio_backend.client.stat_object(
                bucket_name=self.minio_backend.bucket_name,
                object_name=object_key
            )
            
            filename = Path(object_key).name
            return {
                "filename": filename,
                "size": stat.size,
                "type": Path(filename).suffix.lower(),
                "modified": stat.last_modified.isoformat() if stat.last_modified else None,
                "content_type": stat.content_type,
                "object_key": object_key
            }
            
        except Exception as e:
            logger.warning(f"Failed to get metadata for MinIO object {object_key}: {e}")
            return {}


class StorageFactory:
    """Factory for creating file storage handlers"""
    
    @staticmethod
    def create_storage(storage_type: str = 'minio') -> FileStorageInterface:
        """Create file storage handler based on type"""
        if storage_type == 'django':
            return DjangoFileStorage()
        elif storage_type == 'minio':
            return MinIOFileStorage()
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")
    
    @staticmethod
    def get_available_storage_types() -> list:
        """Get list of available storage types"""
        return ['django', 'minio']