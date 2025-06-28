"""
Factory for creating file storage handlers.
"""

import shutil
import logging
import os
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


class StorageFactory:
    """Factory for creating file storage handlers"""
    
    @staticmethod
    def create_storage(storage_type: str = 'django') -> FileStorageInterface:
        """Create file storage handler based on type"""
        if storage_type == 'django':
            return DjangoFileStorage()
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")
    
    @staticmethod
    def get_available_storage_types() -> list:
        """Get list of available storage types"""
        return ['django']