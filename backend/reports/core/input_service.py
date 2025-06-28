"""
Input processing service following SOLID principles.
"""

import logging
from typing import Dict, Any, List
from ..interfaces.input_processor_interface import InputProcessorInterface

logger = logging.getLogger(__name__)


class InputService:
    """Service responsible for processing input data from knowledge base"""
    
    def __init__(self, input_processor: InputProcessorInterface):
        self.input_processor = input_processor
    
    def process_knowledge_base_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process files from knowledge base and prepare for report generation"""
        try:
            logger.info(f"Processing {len(file_paths)} file paths from knowledge base")
            
            # Validate input
            if not file_paths:
                return {"text_input": "", "caption_files": []}
            
            # Process selected files
            processed_data = self.input_processor.process_selected_files(file_paths)
            
            # Validate processed data
            if not self.input_processor.validate_input_data(processed_data):
                logger.warning("Processed data validation failed")
                return {"text_input": "", "caption_files": []}
            
            # Get consolidated content data for report generation
            content_data = self.input_processor.get_content_data(processed_data)
            
            logger.info(
                f"Prepared content data: "
                f"text_input length: {len(content_data.get('text_input', ''))} chars, "
                f"{len(content_data.get('caption_files', []))} caption files"
            )
            
            return content_data
            
        except Exception as e:
            logger.error(f"Error processing knowledge base files: {e}")
            return {"text_input": "", "caption_files": []}
    
    def cleanup_temporary_files(self, temp_file_paths: List[str]):
        """
        No-op since we're not using temp files anymore.
        Kept for interface compatibility.
        """
        pass  # Using direct content approach like podcast
    
    def validate_input_structure(self, data: Dict[str, Any]) -> bool:
        """Validate input data structure"""
        try:
            return self.input_processor.validate_input_data(data)
        except Exception as e:
            logger.error(f"Error validating input structure: {e}")
            return False
    
    def get_supported_file_types(self) -> List[str]:
        """Get list of supported file types"""
        try:
            return self.input_processor.get_supported_file_types()
        except Exception as e:
            logger.error(f"Error getting supported file types: {e}")
            return []