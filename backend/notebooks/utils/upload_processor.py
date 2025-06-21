"""
Immediate file processing on upload - designed to be fast and synchronous.
"""

import os
import tempfile
import subprocess
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

import fitz  # PyMuPDF
from fastapi import UploadFile, HTTPException

from .services.base_service import BaseService
from .services.file_storage import FileStorageService
from .services.content_index import ContentIndexingService
from .file_validator import FileValidator
from .core.config import settings

class UploadProcessor(BaseService):
    """Handles immediate processing of uploaded files."""
    
    def __init__(self):
        super().__init__("upload_processor")
        self.file_storage = FileStorageService()
        self.content_indexing = ContentIndexingService()
        self.validator = FileValidator()
        
        # Initialize whisper model lazily
        self._whisper_model = None
        
        # Track upload statuses in memory (in production, use Redis or database)
        self._upload_statuses = {}
    
    @property
    def whisper_model(self):
        """Lazy load whisper model."""
        if self._whisper_model is None:
            try:
                import whisper
                self._whisper_model = whisper.load_model("base")
            except ImportError:
                self.log_operation("whisper_import_error", "Whisper not available", "warning")
                self._whisper_model = None
        return self._whisper_model
    
    def get_upload_status(self, upload_file_id: str, user_pk: int = None) -> Optional[Dict[str, Any]]:
        """Get the current status of an upload by upload_file_id."""
        try:
            # Check in-memory status first
            if upload_file_id in self._upload_statuses:
                return self._upload_statuses[upload_file_id]
            
            # Check if file is already processed and stored
            file_metadata = self.file_storage.get_file_by_upload_id(upload_file_id, user_pk)
            if file_metadata:
                status = {
                    'upload_file_id': upload_file_id,
                    'file_id': file_metadata.get('file_id'),
                    'status': 'completed',
                    'parsing_status': 'completed',
                    'filename': file_metadata.get('original_filename'),
                    'metadata': file_metadata
                }
                # Cache for future requests
                self._upload_statuses[upload_file_id] = status
                return status
            
            return None
        except Exception as e:
            self.log_operation("get_upload_status_error", str(e), "error")
            return None
    
    def delete_upload(self, upload_file_id: str, user_pk: int) -> bool:
        """Delete an upload and its associated files."""
        try:
            # Remove from in-memory tracking
            if upload_file_id in self._upload_statuses:
                del self._upload_statuses[upload_file_id]
            
            # Delete from storage
            return self.file_storage.delete_file_by_upload_id(upload_file_id, user_pk)
        except Exception as e:
            self.log_operation("delete_upload_error", str(e), "error")
            return False
    
    def _update_upload_status(self, upload_file_id: str, status: str, **kwargs):
        """Update the status of an upload."""
        if upload_file_id:
            current_status = self._upload_statuses.get(upload_file_id, {})
            current_status.update({
                'upload_file_id': upload_file_id,
                'status': status,
                'parsing_status': status,
                'updated_at': datetime.now().isoformat(),
                **kwargs
            })
            self._upload_statuses[upload_file_id] = current_status

    def process_upload(self, file: UploadFile, upload_file_id: Optional[str] = None, user_pk: Optional[int] = None, notebook_id: Optional[int] = None) -> Dict[str, Any]:
        """Main entry point for immediate file processing."""
        print("upload")
        temp_path = None
        try:
            # Initialize status tracking
            if upload_file_id:
                self._update_upload_status(upload_file_id, 'pending', filename=file.name)
            
            # Validate file
            validation = self.validator.validate_file(file)
            if not validation["valid"]:
                if upload_file_id:
                    self._update_upload_status(upload_file_id, 'error', 
                                             error=f"File validation failed: {'; '.join(validation['errors'])}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"File validation failed: {'; '.join(validation['errors'])}"
                )
            
            # Update status to processing
            if upload_file_id:
                self._update_upload_status(upload_file_id, 'processing', filename=file.name)
            
            # Save file temporarily
            temp_path = self._save_uploaded_file(file)
            
            # Additional content validation
            content_validation = self.validator.validate_file_content(temp_path)
            if not content_validation["valid"]:
                if upload_file_id:
                    self._update_upload_status(upload_file_id, 'error', 
                                             error=f"File content validation failed: {'; '.join(content_validation['errors'])}")
                raise HTTPException(
                    status_code=400,
                    detail=f"File content validation failed: {'; '.join(content_validation['errors'])}"
                )
            
            # Get file size
            file_size = os.path.getsize(temp_path)
            
            # Prepare file metadata
            file_metadata = {
                "filename": file.name,
                "file_extension": validation["file_extension"],
                "content_type": validation["content_type"],
                "file_size": file_size,
                "upload_file_id": upload_file_id,
                "parsing_status": "processing"
            }
            
            # Process based on file type
            processing_result = self._process_file_by_type(temp_path, file_metadata)
            
            # Update file metadata with parsing status
            file_metadata["parsing_status"] = "completed"
            
            # Store result with user isolation
            if user_pk is None:
                raise ValueError("user_pk is required for file storage")
            if notebook_id is None:
                raise ValueError("notebook_id is required for file storage")
                
            file_id = self.file_storage.store_processed_file(
                content=processing_result['content'],
                metadata=file_metadata,
                processing_result=processing_result,
                user_id=user_pk,
                notebook_id=notebook_id
            )
            
            # Index content for search
            self.content_indexing.index_content(
                file_id=file_id,
                content=processing_result['content'],
                metadata=file_metadata,
                processing_stage="immediate"
            )
            
            # Update final status
            if upload_file_id:
                self._update_upload_status(upload_file_id, 'completed', 
                                         file_id=file_id,
                                         filename=file.name,
                                         file_size=file_size,
                                         metadata=file_metadata)
            
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            
            return {
                'file_id': file_id,
                'status': 'completed',
                'parsing_status': 'completed',
                'content_preview': processing_result['content'][:500] + '...' if len(processing_result['content']) > 500 else processing_result['content'],
                'processing_type': 'immediate',
                'features_available': processing_result.get('features_available', []),
                'metadata': processing_result.get('metadata', {}),
                'filename': file.name,
                'file_size': file_size,
                'upload_file_id': upload_file_id
            }
            
        except HTTPException:
            # Clean up and re-raise HTTP exceptions
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
        except Exception as e:
            # Handle unexpected errors
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            
            if upload_file_id:
                self._update_upload_status(upload_file_id, 'error', error=str(e))
            
            self.log_operation("process_upload_error", str(e), "error")
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    def _save_uploaded_file(self, file: UploadFile) -> str:
        """Save uploaded file to temporary directory."""
        try:
            suffix = Path(file.name).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="deepsight_") as tmp_file:
                content = file.read()
                
                # Reset file pointer for potential future reads
                file.seek(0)
                
                # Additional size check
                if len(content) > self.validator.max_file_size:
                    os.unlink(tmp_file.name)
                    raise ValueError(f"File size {len(content) / (1024*1024):.1f}MB exceeds maximum allowed size")
                
                tmp_file.write(content)
                tmp_file.flush()
                
                self.log_operation("save_file", f"Saved {file.name} to {tmp_file.name}")
                return tmp_file.name
                
        except Exception as e:
            self.log_operation("save_file_error", f"File: {file.name}, error: {str(e)}", "error")
            raise
    
    def _process_file_by_type(self, file_path: str, file_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process file based on its type."""
        file_extension = file_metadata.get('file_extension', '').lower()
        
        if file_extension == '.pdf':
            return self._process_pdf_immediate(file_path, file_metadata)
        elif file_extension in ['.mp3', '.wav', '.m4a']:
            return self._process_audio_immediate(file_path, file_metadata)
        elif file_extension in ['.mp4', '.avi', '.mov']:
            return self._process_video_immediate(file_path, file_metadata)
        elif file_extension in ['.txt', '.md']:
            return self._process_text_immediate(file_path, file_metadata)
        elif file_extension in ['.ppt', '.pptx']:
            return self._process_presentation_immediate(file_path, file_metadata)
        else:
            return {
                'content': f"File type {file_extension} is supported but no immediate processing available.",
                'metadata': {},
                'features_available': [],
                'processing_time': 'immediate'
            }
    
    def _process_pdf_immediate(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """Quick PDF text extraction using PyMuPDF."""
        try:
            doc = fitz.open(file_path)
            content = ""
            
            # Extract basic metadata
            pdf_metadata = {
                'page_count': doc.page_count,
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'creation_date': doc.metadata.get('creationDate', ''),
                'modification_date': doc.metadata.get('modDate', ''),
            }
            
            # Extract text from all pages
            for page_num in range(doc.page_count):
                page = doc[page_num]
                content += f"\n=== Page {page_num + 1} ===\n"
                page_text = page.get_text()
                content += page_text
            
            doc.close()
            
            # Check if content extraction was successful
            if not content.strip():
                content = f"PDF document '{file_metadata['filename']}' appears to be image-based or empty. Text extraction may require OCR processing."
            
            return {
                'content': content,
                'metadata': pdf_metadata,
                'features_available': ['advanced_pdf_extraction', 'figure_extraction', 'table_extraction'],
                'processing_time': 'immediate'
            }
            
        except Exception as e:
            raise Exception(f"PDF processing failed: {str(e)}")
    
    def _process_audio_immediate(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """Quick audio transcription using Whisper."""
        try:
            if not self.whisper_model:
                return {
                    'content': f"Audio file '{file_metadata['filename']}' uploaded successfully. Transcription requires Whisper installation.",
                    'metadata': self._get_audio_metadata(file_path),
                    'features_available': ['audio_transcription', 'speaker_diarization'],
                    'processing_time': 'immediate'
                }
            
            # Transcribe audio
            result = self.whisper_model.transcribe(file_path, language="auto")
            
            # Get basic audio info
            audio_metadata = self._get_audio_metadata(file_path)
            audio_metadata.update({
                'language': result.get("language", "unknown"),
                'segments_count': len(result.get("segments", [])),
            })
            
            return {
                'content': result["text"],
                'metadata': audio_metadata,
                'features_available': ['speaker_diarization', 'sentiment_analysis', 'advanced_audio_analysis'],
                'processing_time': 'immediate'
            }
            
        except Exception as e:
            raise Exception(f"Audio processing failed: {str(e)}")
    
    def _process_video_immediate(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """Quick video processing - extract audio and transcribe."""
        try:
            # Extract audio from video
            audio_path = tempfile.mktemp(suffix='.wav')
            
            cmd = [
                'ffmpeg', '-i', file_path, '-vn', '-acodec', 'pcm_s16le', 
                '-ar', '16000', '-ac', '1', '-y', audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                # If audio extraction fails, just return metadata
                video_metadata = self._get_video_metadata(file_path)
                return {
                    'content': f"Video file '{file_metadata['filename']}' uploaded successfully. No audio track found or audio extraction failed.",
                    'metadata': video_metadata,
                    'features_available': ['frame_extraction', 'scene_analysis', 'video_transcription'],
                    'processing_time': 'immediate'
                }
            
            try:
                # Transcribe extracted audio if whisper is available
                if self.whisper_model and os.path.exists(audio_path):
                    transcription_result = self.whisper_model.transcribe(audio_path, language="auto")
                    transcript = transcription_result["text"]
                    language = transcription_result.get("language", "unknown")
                else:
                    transcript = f"Video file '{file_metadata['filename']}' uploaded successfully. Audio transcription requires Whisper installation."
                    language = "unknown"
                
                # Get video metadata
                video_metadata = self._get_video_metadata(file_path)
                video_metadata.update({
                    'language': language,
                    'has_audio': True,
                })
                
                return {
                    'content': transcript,
                    'metadata': video_metadata,
                    'features_available': ['frame_extraction', 'scene_analysis', 'speaker_diarization', 'video_analysis'],
                    'processing_time': 'immediate'
                }
                
            finally:
                # Clean up extracted audio
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
                    
        except Exception as e:
            raise Exception(f"Video processing failed: {str(e)}")
    
    def _process_text_immediate(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """Process text files immediately."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            text_metadata = {
                'word_count': len(content.split()),
                'char_count': len(content),
                'line_count': len(content.splitlines()),
                'encoding': 'utf-8'
            }
            
            return {
                'content': content,
                'metadata': text_metadata,
                'features_available': ['content_analysis', 'summarization'],
                'processing_time': 'immediate'
            }
            
        except UnicodeDecodeError:
            # Try different encodings
            for encoding in ['latin-1', 'cp1252']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    
                    text_metadata = {
                        'word_count': len(content.split()),
                        'char_count': len(content),
                        'line_count': len(content.splitlines()),
                        'encoding': encoding
                    }
                    
                    return {
                        'content': content,
                        'metadata': text_metadata,
                        'features_available': ['content_analysis', 'summarization'],
                        'processing_time': 'immediate'
                    }
                except UnicodeDecodeError:
                    continue
            
            raise Exception(f"Could not decode text file with any supported encoding")
        except Exception as e:
            raise Exception(f"Text processing failed: {str(e)}")
    
    def _process_presentation_immediate(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """Process presentation files."""
        try:
            # For now, return placeholder - would need python-pptx for full implementation
            ppt_metadata = {
                'file_type': 'presentation',
                'supported_extraction': False
            }
            
            content = f"Presentation file '{file_metadata['filename']}' uploaded successfully. Content extraction requires additional processing."
            
            return {
                'content': content,
                'metadata': ppt_metadata,
                'features_available': ['slide_extraction', 'text_extraction', 'image_extraction'],
                'processing_time': 'immediate'
            }
            
        except Exception as e:
            raise Exception(f"Presentation processing failed: {str(e)}")
    
    def _get_audio_metadata(self, file_path: str) -> Dict:
        """Extract audio metadata using ffprobe."""
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            import json
            data = json.loads(result.stdout)
            format_info = data.get('format', {})
            
            return {
                'duration': float(format_info.get('duration', 0)),
                'bitrate': int(format_info.get('bit_rate', 0)),
                'size': int(format_info.get('size', 0)),
                'format_name': format_info.get('format_name', 'unknown')
            }
        except Exception:
            return {'error': 'Could not extract audio metadata'}
    
    def _get_video_metadata(self, file_path: str) -> Dict:
        """Extract video metadata using ffprobe."""
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', '-show_format', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            import json
            data = json.loads(result.stdout)
            
            # Get video stream info
            video_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), {})
            format_info = data.get('format', {})
            
            return {
                'duration': float(format_info.get('duration', 0)),
                'resolution': f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}",
                'fps': video_stream.get('r_frame_rate', '0/0'),
                'codec': video_stream.get('codec_name', 'unknown'),
                'format_name': format_info.get('format_name', 'unknown'),
                'size': int(format_info.get('size', 0))
            }
        except Exception:
            return {'error': 'Could not extract video metadata'} 