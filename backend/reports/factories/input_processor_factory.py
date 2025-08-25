"""
Factory for creating input processor instances.
"""

import tempfile
import logging
import os
import mimetypes
import uuid
from typing import Dict, Any, List
from pathlib import Path
from ..interfaces.input_processor_interface import InputProcessorInterface

logger = logging.getLogger(__name__)


class KnowledgeBaseInputProcessor(InputProcessorInterface):
    """Input processor for knowledge base files"""
    
    def __init__(self):
        pass  # No temp files to track - using direct content approach like podcast
    
    def process_selected_files(self, file_paths: List[str], user_id: int) -> Dict[str, Any]:
        """Process selected files from knowledge base and extract content"""
        input_data = {"text_files": [], "selected_file_ids": []}
        
        try:
            from notebooks.models import KnowledgeBaseItem
            
            for file_id in file_paths:
                try:
                    # Handle UUID file identifiers (only UUID format supported)
                    if isinstance(file_id, str):
                        # Validate that it's a proper UUID
                        try:
                            uuid.UUID(file_id)
                            # It's a valid UUID string, use as-is
                        except ValueError:
                            logger.warning(f"Invalid UUID file ID: {file_id}")
                            continue
                    elif hasattr(file_id, 'hex'):
                        # Already a UUID object, convert to string
                        file_id = str(file_id)
                    else:
                        logger.warning(f"Unsupported file ID type: {type(file_id)} for {file_id}")
                        continue
                    
                    # Store file ID for figure data combination
                    input_data["selected_file_ids"].append(f"f_{file_id}")
                    
                    # Get file content using the model manager for consistency
                    content = KnowledgeBaseItem.objects.get_content(file_id, user_id)
                    
                    if content:
                        # Get metadata from knowledge base item
                        try:
                            kb_item = KnowledgeBaseItem.objects.get(id=file_id)
                            filename = kb_item.title or f"file_{file_id}"
                            content_type = getattr(kb_item, 'content_type', 'unknown')
                            # Get original file extension and MIME type from MinIO metadata
                            raw_extension = None
                            raw_mime = None
                            if kb_item.original_file_object_key:
                                # Extract filename from metadata or use the title
                                original_filename = kb_item.file_metadata.get('original_filename') or kb_item.title
                                raw_extension = os.path.splitext(original_filename)[1].lower()
                                raw_mime, _ = mimetypes.guess_type(original_filename)
                            file_data = {
                                "content": content,
                                "filename": filename,
                                "file_path": f"kb_item_{file_id}",
                                "content_type": content_type,
                                "raw_extension": raw_extension,
                                "raw_mime": raw_mime,
                                "metadata": kb_item.metadata or {},
                            }
                            
                            # All files are treated as text files (no more caption file separation)
                            input_data["text_files"].append(file_data)
                            logger.info(f"Loaded text file: {filename} (ID: {file_id})")
                                
                        except KnowledgeBaseItem.DoesNotExist:
                            logger.warning(f"Knowledge base item not found for ID: {file_id}")
                            continue
                    else:
                        logger.warning(f"No content found for file ID: {file_id}")
                        
                except Exception as e:
                    logger.warning(f"Failed to process file ID {file_id}: {e}")
                    continue
            
            logger.info(
                f"Processed input data: {len(input_data['text_files'])} text files, "
                f"{len(input_data['selected_file_ids'])} file IDs for figure data"
            )
            
            return input_data
            
        except Exception as e:
            logger.error(f"Error processing selected files: {e}")
            return input_data
    
    def _process_folder_path(self, folder_path_obj: Path, input_data: Dict[str, Any]):
        """Legacy method to process folder paths (for backward compatibility)"""
        try:
            # Process all markdown files as text files
            all_md_files = list(folder_path_obj.glob("*.md")) + \
                          list(folder_path_obj.glob("**/*.md"))
            
            for md_file in all_md_files:
                try:
                    with open(md_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    file_data = {
                        "content": content,
                        "filename": md_file.name,
                        "file_path": str(md_file),
                    }
                    input_data["text_files"].append(file_data)
                    logger.info(f"Loaded text file: {md_file}")
                except Exception as e:
                    logger.warning(f"Failed to read file {md_file}: {e}")
            
            # Legacy folder processing no longer handles caption files
                    
        except Exception as e:
            logger.warning(f"Failed to process folder path {folder_path_obj}: {e}")
    
    def create_temp_files(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Instead of creating temp files, return paths that represent the content directly.
        This matches the podcast service's approach of using direct content.
        """
        try:
            result = {
                "paper_path": [],
                "transcript_path": [],
                "selected_file_ids": processed_data.get("selected_file_ids", [])
            }
            
            # For backward compatibility, we still return paths but they will be ignored
            # in the new consolidated approach
            for text_file in processed_data.get("text_files", []):
                if text_file.get("file_path"):
                    result["paper_path"].append(text_file["file_path"])
            
            return result
            
        except Exception as e:
            logger.error(f"Error preparing file paths: {e}")
            return {"paper_path": [], "transcript_path": [], "selected_file_ids": []}
    
    def cleanup_temp_files(self, temp_file_paths: List[str]):
        """
        No-op since we're not creating temp files anymore.
        This maintains compatibility with the interface while using direct content approach.
        """
        pass  # No temp files to clean up - using direct content approach
    
    def get_content_data(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get content data for report generation with consolidated text_input."""
        content_data = {"text_input": "", "selected_file_ids": []}
        
        try:
            text_contents = []
            
            # Process all text files and create formatted blocks
            for file_data in processed_data.get("text_files", []):
                content = file_data.get("content", "")
                filename = file_data.get("filename", "")
                
                if not content.strip():
                    continue
                
                # Create a formatted block with clear file boundaries
                formatted_block = f"--- START OF FILE: {filename} ---\n\n{content}\n\n--- END OF FILE: {filename} ---"
                text_contents.append(formatted_block)
            
            # Join all blocks into a single text_input string
            if text_contents:
                content_data["text_input"] = "\n\n".join(text_contents)
            
            # Pass selected file IDs for figure data combination
            if processed_data.get("selected_file_ids"):
                content_data["selected_file_ids"] = processed_data["selected_file_ids"]
            
            logger.info(f"Consolidated {len(text_contents)} files into text_input")
            return content_data
            
        except Exception as e:
            logger.error(f"Error preparing content data: {e}")
            return {"text_input": "", "selected_file_ids": []}
    
    def validate_input_data(self, data: Dict[str, Any]) -> bool:
        """Validate that input data is in the correct format"""
        try:
            # Check that data has the expected structure
            required_keys = ["text_files", "selected_file_ids"]
            for key in required_keys:
                if key not in data:
                    return False
                if not isinstance(data[key], list):
                    return False
            
            # Validate file data structures
            for text_file in data["text_files"]:
                if not isinstance(text_file, dict):
                    return False
                if "content" not in text_file or "filename" not in text_file:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def get_supported_file_types(self) -> List[str]:
        """Get list of supported file types for processing"""
        return [".md", ".json"]


class InputProcessorFactory:
    """Factory for creating input processor instances"""
    
    @staticmethod
    def create_processor(processor_type: str = 'knowledge_base') -> InputProcessorInterface:
        """Create input processor based on type"""
        if processor_type == 'knowledge_base':
            return KnowledgeBaseInputProcessor()
        else:
            raise ValueError(f"Unknown input processor type: {processor_type}")
    
    @staticmethod
    def get_available_processors() -> list:
        """Get list of available input processor types"""
        return ['knowledge_base']