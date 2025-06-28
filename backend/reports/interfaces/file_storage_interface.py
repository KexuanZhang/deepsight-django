"""
File Storage Interface for dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path


class FileStorageInterface(ABC):
    """Interface for file storage operations"""
    
    @abstractmethod
    def create_output_directory(self, user_id: int, report_id: str, notebook_id: Optional[int] = None) -> Path:
        """Create output directory for report files"""
        pass
    
    @abstractmethod
    def store_generated_files(self, source_files: List[str], target_dir: Path) -> List[str]:
        """Store generated files and return list of stored file paths"""
        pass
    
    @abstractmethod
    def get_main_report_file(self, file_list: List[str]) -> Optional[str]:
        """Identify the main report file from a list of generated files"""
        pass
    
    @abstractmethod
    def clean_output_directory(self, directory: Path) -> bool:
        """Clean an output directory before generation"""
        pass
    
    @abstractmethod
    def delete_report_files(self, report_id: str, user_id: int) -> bool:
        """Delete all files associated with a report"""
        pass
    
    @abstractmethod
    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get metadata for a specific file"""
        pass