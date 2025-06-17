"""
File storage service for managing processed files and metadata.
"""

import json
import shutil
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, UTC

from .base_service import BaseService
from ..core.config import settings

class FileStorageService(BaseService):
    """Service for storing and managing processed files."""
    
    def __init__(self):
        super().__init__("file_storage")
        
        # Create storage directories
        self.processed_files_dir = self.data_dir / "processed_files"
        self.processed_files_dir.mkdir(exist_ok=True)
        
        # Create index for quick lookups
        self.index_file = self.data_dir / "file_index.json"
    
    async def store_processed_file(
        self, 
        content: str, 
        metadata: Dict[str, Any], 
        processing_result: Dict[str, Any]
    ) -> str:
        """Store processed file content and metadata."""
        try:
            # Generate file ID
            file_id = self.generate_id()
            
            # Create file directory
            file_dir = self.processed_files_dir / file_id
            file_dir.mkdir(exist_ok=True)
            
            # Prepare comprehensive metadata
            file_metadata = {
                "file_id": file_id,
                "original_filename": metadata.get("filename", "unknown"),
                "file_extension": metadata.get("file_extension", ""),
                "content_type": metadata.get("content_type", ""),
                "file_size": metadata.get("file_size", 0),
                "upload_timestamp": datetime.now(UTC).isoformat(),
                "processing_timestamp": datetime.now(UTC).isoformat(),
                "processing_type": processing_result.get("processing_type", "immediate"),
                "content_length": len(content),
                "features_available": processing_result.get("features_available", []),
                "status": "completed",
                "parsing_status": metadata.get("parsing_status", "completed"),
                "processing_metadata": processing_result.get("metadata", {}),
                "upload_file_id": metadata.get("upload_file_id")
            }
            
            # Save content
            content_path = file_dir / "content.md"
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Save metadata
            metadata_path = file_dir / "metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(file_metadata, f, indent=2)
            
            # Update index
            await self._update_file_index(file_id, file_metadata)
            
            self.log_operation("store_file", f"file_id={file_id}, filename={metadata.get('filename')}")
            return file_id
            
        except Exception as e:
            self.log_operation("store_file_error", str(e), "error")
            raise
    
    async def get_file_content(self, file_id: str) -> Optional[str]:
        """Retrieve file content by ID."""
        try:
            content_path = self.processed_files_dir / file_id / "content.md"
            if content_path.exists():
                with open(content_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return None
        except Exception as e:
            self.log_operation("get_content_error", f"file_id={file_id}, error={str(e)}", "error")
            return None
    
    async def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve file metadata by ID."""
        try:
            metadata_path = self.processed_files_dir / file_id / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.log_operation("get_metadata_error", f"file_id={file_id}, error={str(e)}", "error")
            return None
    
    async def get_file_by_upload_id(self, upload_file_id: str) -> Optional[Dict[str, Any]]:
        """Get file by upload file ID."""
        try:
            index = await self._load_file_index()
            for file_id, file_info in index.items():
                if file_info.get("upload_file_id") == upload_file_id:
                    content = await self.get_file_content(file_id)
                    metadata = await self.get_file_metadata(file_id)
                    return {
                        "file_id": file_id,
                        "content": content,
                        "metadata": metadata
                    }
            return None
        except Exception as e:
            self.log_operation("get_by_upload_id_error", f"upload_id={upload_file_id}, error={str(e)}", "error")
            return None
    
    async def list_files(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List stored files with pagination."""
        try:
            files = []
            for file_dir in self.processed_files_dir.iterdir():
                if file_dir.is_dir():
                    metadata_path = file_dir / "metadata.json"
                    if metadata_path.exists():
                        try:
                            with open(metadata_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                                files.append(metadata)
                        except Exception as e:
                            self.log_operation("list_file_error", f"file_id={file_dir.name}, error={str(e)}", "error")
                            continue
            
            # Sort by upload timestamp (newest first)
            files.sort(key=lambda x: x.get("upload_timestamp", ""), reverse=True)
            
            # Apply pagination
            paginated_files = files[offset:offset + limit]
            
            self.log_operation("list_files", f"found {len(files)} files, returned {len(paginated_files)}")
            return paginated_files
            
        except Exception as e:
            self.log_operation("list_files_error", str(e), "error")
            return []
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete a stored file and its metadata."""
        try:
            file_dir = self.processed_files_dir / file_id
            if file_dir.exists():
                shutil.rmtree(file_dir)
                
                # Remove from index
                await self._remove_from_index(file_id)
                
                self.log_operation("delete_file", f"file_id={file_id}")
                return True
            return False
            
        except Exception as e:
            self.log_operation("delete_file_error", f"file_id={file_id}, error={str(e)}", "error")
            return False
    
    async def delete_file_by_upload_id(self, upload_file_id: str) -> bool:
        """Delete a file by upload file ID."""
        try:
            # Find the file by upload_file_id
            file_data = await self.get_file_by_upload_id(upload_file_id)
            if file_data and file_data.get("file_id"):
                file_id = file_data["file_id"]
                return await self.delete_file(file_id)
            return False
        except Exception as e:
            self.log_operation("delete_file_by_upload_id_error", f"upload_id={upload_file_id}, error={str(e)}", "error")
            return False
    
    async def store_extraction_result(
        self, 
        file_id: str, 
        extraction_type: str, 
        result: Dict[str, Any]
    ) -> str:
        """Store feature extraction results."""
        try:
            # Create extraction directory
            file_dir = self.processed_files_dir / file_id
            extractions_dir = file_dir / "extractions"
            extractions_dir.mkdir(exist_ok=True)
            
            # Generate extraction ID
            extraction_id = f"{extraction_type}_{self.generate_id()[:8]}"
            
            # Store extraction result
            extraction_path = extractions_dir / f"{extraction_id}.json"
            extraction_data = {
                "extraction_id": extraction_id,
                "extraction_type": extraction_type,
                "file_id": file_id,
                "result": result,
                "created_at": datetime.now(UTC).isoformat()
            }
            
            with open(extraction_path, 'w', encoding='utf-8') as f:
                json.dump(extraction_data, f, indent=2)
            
            self.log_operation("store_extraction", f"file_id={file_id}, type={extraction_type}")
            return extraction_id
            
        except Exception as e:
            self.log_operation("store_extraction_error", str(e), "error")
            raise
    
    async def get_extraction_result(self, file_id: str, extraction_id: str) -> Optional[Dict[str, Any]]:
        """Get extraction result by ID."""
        try:
            extraction_path = self.processed_files_dir / file_id / "extractions" / f"{extraction_id}.json"
            if extraction_path.exists():
                with open(extraction_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.log_operation("get_extraction_error", f"file_id={file_id}, extraction_id={extraction_id}, error={str(e)}", "error")
            return None
    
    async def _update_file_index(self, file_id: str, metadata: Dict[str, Any]):
        """Update file index for quick lookups."""
        try:
            index = await self._load_file_index()
            index[file_id] = {
                "filename": metadata["original_filename"],
                "file_extension": metadata["file_extension"],
                "upload_timestamp": metadata["upload_timestamp"],
                "upload_file_id": metadata.get("upload_file_id"),
                "features_available": metadata["features_available"]
            }
            
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)
                
        except Exception as e:
            self.log_operation("update_index_error", str(e), "error")
    
    async def _load_file_index(self) -> Dict[str, Any]:
        """Load file index."""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.log_operation("load_index_error", str(e), "error")
            return {}
    
    async def _remove_from_index(self, file_id: str):
        """Remove file from index."""
        try:
            index = await self._load_file_index()
            if file_id in index:
                del index[file_id]
                with open(self.index_file, 'w', encoding='utf-8') as f:
                    json.dump(index, f, indent=2)
        except Exception as e:
            self.log_operation("remove_index_error", str(e), "error")


# Global singleton instance to prevent repeated initialization
file_storage_service = FileStorageService() 