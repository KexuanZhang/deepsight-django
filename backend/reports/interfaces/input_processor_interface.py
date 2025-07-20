"""
Input Processor Interface for dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pathlib import Path


class InputProcessorInterface(ABC):
    """Interface for processing input data from knowledge base"""
    
    @abstractmethod
    def process_selected_files(self, file_paths: List[str], user_id: int) -> Dict[str, Any]:
        """Process selected files from knowledge base and extract content"""
        pass
    
    @abstractmethod
    def create_temp_files(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create temporary files for report generation"""
        pass
    
    @abstractmethod
    def cleanup_temp_files(self, temp_file_paths: List[str]):
        """Clean up temporary files after processing"""
        pass
    
    @abstractmethod
    def validate_input_data(self, data: Dict[str, Any]) -> bool:
        """Validate that input data is in the correct format"""
        pass
    
    @abstractmethod
    def get_supported_file_types(self) -> List[str]:
        """Get list of supported file types for processing"""
        pass