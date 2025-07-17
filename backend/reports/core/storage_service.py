"""
Storage management service following SOLID principles.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from ..interfaces.file_storage_interface import FileStorageInterface

logger = logging.getLogger(__name__)


class StorageService:
    """Service responsible for managing file storage operations"""
    
    def __init__(self, file_storage: FileStorageInterface):
        self.file_storage = file_storage
    
    def setup_report_storage(self, user_id: int, report_id: str, notebook_id: Optional[int] = None) -> Path:
        """Set up storage directory for a report"""
        try:
            output_dir = self.file_storage.create_output_directory(
                user_id=user_id,
                report_id=report_id,
                notebook_id=notebook_id
            )
            logger.info(f"Set up storage directory for report {report_id}: {output_dir}")
            return output_dir
        except Exception as e:
            logger.error(f"Error setting up storage for report {report_id}: {e}")
            raise
    
    def store_report_files(self, generated_files: List[str], user_id: int, report_id: str, notebook_id: int = None) -> Dict[str, Any]:
        """Store generated report files and return storage information"""
        try:
            # Store the files - use new signature for MinIO, fallback for others
            if hasattr(self.file_storage, 'store_generated_files'):
                # Check if the storage supports the new signature
                import inspect
                sig = inspect.signature(self.file_storage.store_generated_files)
                if 'user_id' in sig.parameters:
                    # New MinIO signature
                    stored_files = self.file_storage.store_generated_files(generated_files, user_id, report_id, notebook_id)
                else:
                    # Old signature - create output_dir and use it
                    output_dir = self.file_storage.create_output_directory(user_id, report_id, notebook_id)
                    stored_files = self.file_storage.store_generated_files(generated_files, output_dir)
            else:
                # Fallback
                output_dir = self.file_storage.create_output_directory(user_id, report_id, notebook_id)
                stored_files = self.file_storage.store_generated_files(generated_files, output_dir)
            
            # Identify main report file
            main_file = self.file_storage.get_main_report_file(stored_files)
            
            # Get file metadata
            file_metadata = []
            for file_path in stored_files:
                metadata = self.file_storage.get_file_metadata(file_path)
                if metadata:
                    file_metadata.append(metadata)
            
            return {
                "stored_files": stored_files,
                "main_report_object_key": main_file,  # For MinIO, this will be an object key
                "file_metadata": file_metadata,
                "storage_directory": f"{user_id}/notebook/{notebook_id or 'standalone'}/report/{report_id}"
            }
            
        except Exception as e:
            logger.error(f"Error storing report files: {e}")
            return {
                "stored_files": [],
                "main_report_object_key": None,
                "file_metadata": [],
                "storage_directory": f"{user_id}/notebook/{notebook_id or 'standalone'}/report/{report_id}"
            }
    
    def clean_report_directory(self, output_dir: Path) -> bool:
        """Clean report directory before generation"""
        try:
            success = self.file_storage.clean_output_directory(output_dir)
            if success:
                logger.info(f"Cleaned report directory: {output_dir}")
            return success
        except Exception as e:
            logger.error(f"Error cleaning report directory {output_dir}: {e}")
            return False
    
    def delete_report_storage(self, report_id: str, user_id: int) -> bool:
        """Delete all storage for a report"""
        try:
            success = self.file_storage.delete_report_files(report_id, user_id)
            if success:
                logger.info(f"Deleted storage for report {report_id}")
            return success
        except Exception as e:
            logger.error(f"Error deleting storage for report {report_id}: {e}")
            return False
    
    def cleanup_failed_generation(self, output_dir: Path) -> bool:
        """Clean up resources for failed report generation"""
        try:
            # For MinIO storage, clean up the temporary directory
            if hasattr(self.file_storage, 'cleanup_failed_generation'):
                self.file_storage.cleanup_failed_generation(output_dir)
                logger.info(f"Cleaned up failed generation resources: {output_dir}")
                return True
            else:
                logger.warning(f"Storage doesn't support cleanup_failed_generation: {type(self.file_storage)}")
                return False
        except Exception as e:
            logger.error(f"Error cleaning up failed generation for {output_dir}: {e}")
            return False
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about a specific file"""
        try:
            metadata = self.file_storage.get_file_metadata(file_path)
            return metadata
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return {}
    
    def validate_storage_setup(self, output_dir: Path) -> bool:
        """Validate that storage is properly set up"""
        try:
            # For MinIO storage, we don't need to check physical directory existence
            if str(output_dir).startswith('minio://'):
                logger.info(f"MinIO storage path validated: {output_dir}")
                return True
            else:
                # For local storage, check directory exists
                return output_dir.exists() and output_dir.is_dir()
        except Exception as e:
            logger.error(f"Error validating storage setup: {e}")
            return False