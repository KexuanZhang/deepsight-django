"""
MinIO-based upload processor for immediate file processing.
Handles immediate processing of uploaded files with MinIO object storage only.
"""

import os
import sys
import tempfile
import subprocess
import asyncio
import logging
import time
import re
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# Django imports for file handling
from django.core.files.uploadedfile import UploadedFile as UploadFile
from django.http import Http404
from django.core.exceptions import ValidationError

try:
    from ..utils.storage import FileStorageService
    from ..utils.helpers import ContentIndexingService, config as settings, clean_title
    from ..utils.validators import FileValidator
    # Import caption generation dependencies
    from reports.image_utils import extract_figure_data_from_markdown
    from notebooks.utils.image_processing.caption_generator import generate_caption_for_image
except ImportError:
    # Fallback classes to prevent import errors
    FileStorageService = None
    ContentIndexingService = None
    FileValidator = None
    settings = None
    clean_title = None
    extract_figure_data_from_markdown = None
    generate_caption_for_image = None

# Marker imports with lazy loading
marker_imports = {}

def get_marker_imports():
    """Lazy import marker dependencies."""
    global marker_imports
    if not marker_imports:
        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.output import text_from_rendered, save_output
            from marker.config.parser import ConfigParser
            
            marker_imports = {
                'PdfConverter': PdfConverter,
                'create_model_dict': create_model_dict,
                'text_from_rendered': text_from_rendered,
                'save_output': save_output,
                'ConfigParser': ConfigParser,
                'available': True
            }
        except ImportError as e:
            logging.getLogger(__name__).warning(f"Marker not available: {e}")
            marker_imports = {'available': False}
    return marker_imports


class UploadProcessor:
    """Handles immediate processing of uploaded files with MinIO storage only."""

    def __init__(self):
        self.service_name = "upload_processor"
        self.logger = logging.getLogger(f"{__name__}.upload_processor")

        # Initialize services with fallbacks
        self.file_storage = FileStorageService() if FileStorageService else None
        self.content_indexing = (
            ContentIndexingService() if ContentIndexingService else None
        )
        self.validator = FileValidator() if FileValidator else None

        # Initialize whisper model lazily
        self._whisper_model = None
        self._marker_models = None
        
        # Track upload statuses in memory (in production, use Redis or database)
        self._upload_statuses = {}

    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log service operations with consistent formatting."""
        message = f"[{self.service_name}] {operation}"
        if details:
            message += f": {details}"

        getattr(self.logger, level)(message)
    
    def _detect_device(self):
        """
        Detect the best available device for acceleration.

        Returns:
            str: Device string ('cuda', 'mps', or 'cpu')
        """
        try:
            import torch
            if torch.cuda.is_available():
                return 'cuda'
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return 'mps'
            else:
                return 'cpu'
        except ImportError:
            return 'cpu'

    def _get_device_info_detailed(self):
        """
        Get detailed information about available devices.

        Returns:
            dict: Device information including type, count, and memory
        """
        device_info = {
            'device_type': 'cpu',
            'device_count': 0,
            'memory_info': None,
            'device_name': None
        }

        try:
            import torch
            if torch.cuda.is_available():
                device_info['device_type'] = 'cuda'
                device_info['device_count'] = torch.cuda.device_count()
                device_info['device_name'] = torch.cuda.get_device_name(0)
                if torch.cuda.device_count() > 0:
                    device_info['memory_info'] = {
                        'total': torch.cuda.get_device_properties(0).total_memory,
                        'allocated': torch.cuda.memory_allocated(0),
                        'cached': torch.cuda.memory_reserved(0)
                    }
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device_info['device_type'] = 'mps'
                device_info['device_count'] = 1  # MPS typically has one device
                device_info['device_name'] = 'Apple Silicon GPU'
                # MPS doesn't have memory info API like CUDA
                device_info['memory_info'] = {'note': 'MPS memory info not available via PyTorch API'}
        except ImportError:
            pass

        return device_info

    def _setup_device_environment(self, device_type: str, gpu_id: Optional[int] = None):
        """
        Set up environment variables and configurations for the specified device.

        Args:
            device_type: Type of device ('cuda', 'mps', or 'cpu')
            gpu_id: Specific GPU ID for CUDA (ignored for MPS)
        """
        if device_type == 'cuda':
            if gpu_id is not None:
                os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
                self.log_operation("cuda_device_setup", f"Set CUDA_VISIBLE_DEVICES to {gpu_id}")
            # Set TORCH_DEVICE for marker
            os.environ["TORCH_DEVICE"] = "cuda"
        elif device_type == 'mps':
            # Set TORCH_DEVICE for marker to use MPS
            os.environ["TORCH_DEVICE"] = "mps"
            self.log_operation("mps_device_setup", "Configured environment for MPS acceleration")
        else:
            # CPU mode
            os.environ["TORCH_DEVICE"] = "cpu"
            self.log_operation("cpu_device_setup", "Configured environment for CPU processing")

    @property
    def pdf_processor(self):
        """Lazy load marker PDF processor with proper device configuration."""
        if self._marker_models is None:
            try:
                marker_imports = get_marker_imports()
                if not marker_imports.get('available'):
                    return None

                # Auto-detect device
                device_type = self._detect_device()
                use_gpu = device_type in ['cuda', 'mps']

                # Log device information
                device_info = self._get_device_info_detailed()
                self.log_operation("pdf_device_detection", f"Device detection: {device_info}")
                self.log_operation("pdf_device_selection", f"Using device: {device_type}")

                # Set up device environment
                self._setup_device_environment(device_type)

                # Configure marker with markdown output format
                ConfigParser = marker_imports['ConfigParser']
                config = {
                    "output_format": "markdown",
                    "use_gpu": use_gpu,
                }

                # Filter out None values
                config = {k: v for k, v in config.items() if v is not None}

                config_parser = ConfigParser(config)

                # Use marker Python API with configuration
                try:
                    self._marker_models = marker_imports['PdfConverter'](
                        config=config_parser.generate_config_dict(),
                        processor_list=config_parser.get_processors(),
                        renderer=config_parser.get_renderer(),
                        artifact_dict=marker_imports['create_model_dict'](),
                    )
                    self.log_operation("pdf_processor_init", f"Initialized PDF converter with device={device_type}, format=markdown")
                except Exception as e:
                    self.log_operation("pdf_processor_init_warning", 
                        f"Error initializing converter with device={device_type}, trying with CPU: {str(e)}", "warning")
                    # Try with CPU if acceleration fails
                    config["use_gpu"] = False
                    self._setup_device_environment('cpu')
                    config_parser = ConfigParser(config)
                    self._marker_models = marker_imports['PdfConverter'](
                        config=config_parser.generate_config_dict(),
                        processor_list=config_parser.get_processors(),
                        renderer=config_parser.get_renderer(),
                        artifact_dict=marker_imports['create_model_dict'](),
                    )
                    self.log_operation("pdf_processor_init", "Initialized PDF converter with CPU fallback, format=markdown")

            except ImportError as e:
                self.log_operation("pdf_processor_import_error", f"marker package not available: {e}", "warning")
                self._marker_models = None
        return self._marker_models
    
    @property
    def whisper_model(self):
        """Lazy load faster-whisper model."""
        if self._whisper_model is None:
            try:
                # Suppress known semaphore tracker warnings on macOS
                import sys
                import warnings
                if sys.platform == "darwin":  # macOS
                    warnings.filterwarnings("ignore", message=".*semaphore_tracker.*", category=UserWarning)
                
                import torch
                from faster_whisper import WhisperModel, BatchedInferencePipeline
                
                device = self._get_device()
                compute_type = "float16" if device == "cuda" else "int8"  # Use int8 for CPU to save memory
                
                self.log_operation("faster_whisper_device_selected", f"Selected device: {device} (faster-whisper only supports CUDA and CPU)")
                
                self._whisper_model = WhisperModel("large-v3-turbo", device=device, compute_type=compute_type)
                # Create batched model for better performance
                self._batched_model = BatchedInferencePipeline(model=self._whisper_model)
                
                self.log_operation("faster_whisper_model_loaded", f"Loaded faster-whisper model on {device} with {compute_type} precision")
                
            except ImportError as e:
                self.log_operation("faster_whisper_import_error", f"faster-whisper not available: {e}", "warning")
                self._whisper_model = None
                self._batched_model = None
        return getattr(self, '_batched_model', None)
    
    def _get_device(self) -> str:
        """Detect and return the appropriate device for model inference.
        Note: faster-whisper only supports CUDA and CPU, not MPS."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            # Skip MPS for faster-whisper as it's not supported
            # elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            #     return "mps"  # Not supported by faster-whisper
        except:
            pass
        return "cpu"

    def _hh_mm_ss(self, s: float) -> str:
        """Convert seconds to HH:MM:SS format."""
        import datetime as dt
        return str(dt.timedelta(seconds=int(s)))

    async def transcribe_audio_video(self, file_path: str, filename: str) -> tuple[str, str]:
        """Transcribe audio/video file using faster-whisper. Returns (transcript_content, suggested_filename)."""
        try:
            self.log_operation("transcription_start", f"Starting transcription of {file_path}")
            start_time = time.time()

            batched_model = self.whisper_model
            if not batched_model:
                raise Exception("Speech-to-text not available. Please install faster-whisper and torch.")
            
            # Run transcription in executor to avoid blocking the event loop
            import asyncio
            loop = asyncio.get_event_loop()
            
            def _transcribe_sync():
                return batched_model.transcribe(file_path, vad_filter=True, batch_size=16)
            
            # Execute the CPU-intensive transcription in a thread pool
            segments, _ = await loop.run_in_executor(None, _transcribe_sync)
            
            # Clean the title for filename
            base_title = Path(filename).stem  # Remove file extension
            cleaned_title = clean_title(base_title)
            suggested_filename = f"{cleaned_title}.md"
            
            # Build the transcript
            transcript_lines = []
   
            for segment in segments:
                timestamp = self._hh_mm_ss(segment.start)
                transcript_lines.append(f"**{timestamp}** {segment.text}\n")
            
            transcript_content = "\n".join(transcript_lines)
            
            end_time = time.time()
            duration = end_time - start_time
            self.log_operation("transcription_completed", f"Transcription completed in {duration:.2f} seconds ({duration/60:.2f} minutes)")
            
            return transcript_content, suggested_filename
            
        except Exception as e:
            self.log_operation("transcription_error", f"Transcription failed: {e}", "error")
            raise Exception(f"Transcription failed: {str(e)}")

    def get_upload_status(
        self, upload_file_id: str, user_pk: int = None
    ) -> Optional[Dict[str, Any]]:
        """Get the current status of an upload by upload_file_id."""
        try:
            # Check in-memory status first
            if upload_file_id in self._upload_statuses:
                return self._upload_statuses[upload_file_id]

            # Check if file is already processed and stored
            if self.file_storage:
                file_metadata = self.file_storage.get_file_by_upload_id(
                    upload_file_id, user_pk
                )
                if file_metadata:
                    status = {
                        "upload_file_id": upload_file_id,
                        "file_id": file_metadata.get("file_id"),
                        "status": "completed",
                        "parsing_status": "completed",
                        "filename": file_metadata.get("original_filename"),
                        "metadata": file_metadata,
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
            if self.file_storage:
                return self.file_storage.delete_file_by_upload_id(upload_file_id, user_pk)
            return False
        except Exception as e:
            self.log_operation("delete_upload_error", str(e), "error")
            return False

    def _update_upload_status(self, upload_file_id: str, status: str, **kwargs):
        """Update the status of an upload."""
        if upload_file_id:
            current_status = self._upload_statuses.get(upload_file_id, {})
            
            # Convert UUID objects to strings for JSON serialization
            json_safe_kwargs = {}
            for key, value in kwargs.items():
                if hasattr(value, '__str__') and hasattr(value, 'hex'):  # UUID check
                    json_safe_kwargs[key] = str(value)
                else:
                    json_safe_kwargs[key] = value
            
            current_status.update(
                {
                    "upload_file_id": upload_file_id,
                    "status": status,
                    "parsing_status": status,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    **json_safe_kwargs,
                }
            )
            self._upload_statuses[upload_file_id] = current_status

    async def process_upload(
        self,
        file: UploadFile,
        upload_file_id: Optional[str] = None,
        user_pk: Optional[int] = None,
        notebook_id: Optional[int] = None,
        kb_item_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Main entry point for immediate file processing with MinIO storage."""
        temp_path = None
        try:
            # Initialize status tracking
            if upload_file_id:
                self._update_upload_status(
                    upload_file_id, "pending", filename=file.name
                )

            # Validate file
            validation = self.validator.validate_file(file)
            if not validation["valid"]:
                if upload_file_id:
                    self._update_upload_status(
                        upload_file_id,
                        "error",
                        error=f"File validation failed: {'; '.join(validation['errors'])}",
                    )
                raise ValidationError(
                    f"File validation failed: {'; '.join(validation['errors'])}"
                )

            # Update status to processing
            if upload_file_id:
                self._update_upload_status(
                    upload_file_id, "processing", filename=file.name
                )

            # Save file temporarily
            temp_path = self._save_uploaded_file(file)

            # Additional content validation
            content_validation = self.validator.validate_file_content(temp_path)
            if not content_validation["valid"]:
                if upload_file_id:
                    self._update_upload_status(
                        upload_file_id,
                        "error",
                        error=f"File content validation failed: {'; '.join(content_validation['errors'])}",
                    )
                raise ValidationError(
                    f"File content validation failed: {'; '.join(content_validation['errors'])}"
                )

            # Get file size
            file_size = os.path.getsize(temp_path)

            # Clean the original filename using clean_title function
            file_path = Path(file.name)
            base_name = file_path.stem
            extension = file_path.suffix
            clean_base_name = clean_title(base_name)
            clean_filename = f"{clean_base_name}{extension}"
            
            
            # Prepare file metadata with cleaned file information
            file_metadata = {
                "filename": clean_filename,
                "original_filename": clean_filename,  # Store cleaned filename
                "file_extension": validation["file_extension"],
                "content_type": validation["content_type"],
                "file_size": file_size,
                "upload_file_id": upload_file_id,
                "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                "parsing_status": "processing",
                "storage_backend": "minio",  # Mark as MinIO storage
            }
            
            # Add source URL to metadata if available (for duplicate detection)
            if hasattr(file, '_source_url') and file._source_url:
                file_metadata["source_url"] = file._source_url

            # Process based on file type
            processing_result = await self._process_file_by_type(temp_path, file_metadata)

            # Update file metadata with parsing status
            file_metadata["parsing_status"] = "completed"

            # Store result with user isolation using MinIO storage
            if user_pk is None:
                raise ValueError("user_pk is required for file storage")
            if notebook_id is None:
                raise ValueError("notebook_id is required for file storage")

            # For media files, use transcript filename instead of default extracted_content.md
            processing_result_for_storage = processing_result.copy()
            if processing_result.get('transcript_filename'):
                processing_result_for_storage['content_filename'] = processing_result['transcript_filename']

            # Run synchronous file storage in executor
            # Use thread_sensitive=False to run in thread pool where sync ORM calls are allowed
            from asgiref.sync import sync_to_async
            
            if not self.file_storage:
                raise Exception("MinIO file storage service not available")
                
            # Use source URL as identifier for duplicate detection if available, otherwise use filename
            source_identifier = getattr(file, '_source_url', None) or file.name
            
            store_file_sync = sync_to_async(self.file_storage.store_processed_file, thread_sensitive=False)
            file_id = await store_file_sync(
                content=processing_result["content"],
                metadata=file_metadata,
                processing_result=processing_result_for_storage,
                user_id=user_pk,
                notebook_id=notebook_id,
                original_file_path=temp_path,
                source_identifier=source_identifier,  # Use URL for duplicate detection if available
                kb_item_id=kb_item_id,  # Pass the pre-created KB item ID
            )

            # Run synchronous content indexing in executor
            if self.content_indexing:
                index_content_sync = sync_to_async(self.content_indexing.index_content, thread_sensitive=False)
                await index_content_sync(
                    file_id=file_id,
                    content=processing_result["content"],
                    metadata=file_metadata,
                    processing_stage="immediate",
                )
            
            # Handle marker extraction post-processing if needed
            if 'marker_extraction_result' in processing_result:
                post_process_sync = sync_to_async(self._post_process_marker_extraction, thread_sensitive=False)
                await post_process_sync(file_id, processing_result['marker_extraction_result'])
            
            # Update final status
            if upload_file_id:
                self._update_upload_status(
                    upload_file_id,
                    "completed",
                    file_id=file_id,
                    filename=file.name,
                    file_size=file_size,
                    metadata=file_metadata,
                    storage_backend="minio",
                )

            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

            return {
                "file_id": file_id,
                "status": "completed",
                "parsing_status": "completed",
                "content_preview": processing_result["content"][:500] + "..."
                if len(processing_result["content"]) > 500
                else processing_result["content"],
                "processing_type": "immediate",
                "features_available": processing_result.get("features_available", []),
                "metadata": processing_result.get("metadata", {}),
                "filename": file.name,
                "file_size": file_size,
                "upload_file_id": upload_file_id,
                "storage_backend": "minio",
            }

        except ValidationError:
            # Clean up and re-raise validation errors
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
        except Exception as e:
            # Handle unexpected errors
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

            if upload_file_id:
                self._update_upload_status(upload_file_id, "error", error=str(e))

            self.log_operation("process_upload_error", str(e), "error")
            raise Exception(f"Processing failed: {str(e)}")

    def _save_uploaded_file(self, file: UploadFile) -> str:
        """Save uploaded file to temporary directory."""
        try:
            suffix = Path(file.name).suffix.lower()
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix, prefix="deepsight_minio_"
            ) as tmp_file:
                content = file.read()

                # Reset file pointer for potential future reads
                file.seek(0)

                # Additional size check
                if len(content) > self.validator.max_file_size:
                    os.unlink(tmp_file.name)
                    raise ValueError(
                        f"File size {len(content) / (1024 * 1024):.1f}MB exceeds maximum allowed size"
                    )

                tmp_file.write(content)
                tmp_file.flush()

                self.log_operation("save_file", f"Saved {file.name} to {tmp_file.name}")
                return tmp_file.name

        except Exception as e:
            self.log_operation(
                "save_file_error", f"File: {file.name}, error: {str(e)}", "error"
            )
            raise

    async def _process_file_by_type(
        self, file_path: str, file_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process file based on its type."""
        file_extension = file_metadata.get('file_extension', '').lower()
        
        if file_extension == '.pdf':
            return self._process_pdf_marker(file_path, file_metadata)
        elif file_extension in ['.mp3', '.wav', '.m4a']:
            return await self._process_audio_immediate(file_path, file_metadata)
        elif file_extension in [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".3gp", ".ogv", ".m4v"]:
            return await self._process_video_immediate(file_path, file_metadata)
        elif file_extension == ".md":
            return self._process_markdown_direct(file_path, file_metadata)
        elif file_extension == ".txt":
            return self._process_text_immediate(file_path, file_metadata)
        elif file_extension in [".ppt", ".pptx", ".doc", ".docx"]:
            return self._process_presentation_immediate(file_path, file_metadata)
        else:
            return {
                'content': f"File type {file_extension} is supported but no immediate processing available.",
                'metadata': {},
                'features_available': [],
                'processing_time': 'immediate'
            }
    
    def _process_pdf_marker(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """PDF text extraction using marker package with native image output."""
        try:
            marker_imports = get_marker_imports()
            if not marker_imports.get('available'):
                # Fallback to PyMuPDF if marker is not available
                return self._process_pdf_pymupdf_fallback(file_path, file_metadata)

            self.log_operation("pdf_marker_start", f"Starting marker processing of {file_path}")
            start_time = time.time()

            # Get the marker PDF processor (already configured with GPU if available)
            pdf_processor = self.pdf_processor
            if not pdf_processor:
                # Fallback to PyMuPDF if marker processor failed to load
                return self._process_pdf_pymupdf_fallback(file_path, file_metadata)

            # Generate clean filename for PDF
            original_filename = file_metadata.get('filename', 'document')
            # Remove file extension
            base_title = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
            clean_pdf_title = clean_title(base_title)

            # Convert the PDF to markdown using marker (this generates images directly)
            rendered = pdf_processor(str(file_path))

            # Extract the markdown content for display
            content = rendered.text_content if hasattr(rendered, 'text_content') else str(rendered)

            # Save the original marker output to temporary directory for later processing
            temp_marker_dir = None
            try:
                temp_marker_dir = tempfile.mkdtemp(suffix='_marker_output')
                from marker.output import save_output
                save_output(rendered, temp_marker_dir, "markdown")
                self.log_operation("pdf_marker_save", f"Saved marker output to temporary directory: {temp_marker_dir}")
                
                # List what was created
                created_files = []
                for root, _, files in os.walk(temp_marker_dir):
                    for file in files:
                        created_files.append(os.path.join(root, file))
                self.log_operation("pdf_marker_files", f"Created {len(created_files)} files: {[os.path.basename(f) for f in created_files]}")
                
            except Exception as e:
                self.log_operation("pdf_marker_save_warning", f"Could not save marker output: {e}", "warning")
                # Fallback: save the text content manually
                try:
                    temp_marker_dir = tempfile.mkdtemp(suffix='_marker_fallback')
                    fallback_md_file = os.path.join(temp_marker_dir, "markdown.md")
                    with open(fallback_md_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.log_operation("pdf_marker_save_fallback", f"Saved marker text content to: {fallback_md_file}")
                except Exception as save_error:
                    self.log_operation("pdf_marker_save_error", f"Failed to save marker output: {save_error}", "error")
                    temp_marker_dir = None

            # Get basic PDF metadata using PyMuPDF for metadata extraction
            try:
                if fitz:
                    doc = fitz.open(file_path)
                    pdf_metadata = {
                        'page_count': doc.page_count,
                        'title': doc.metadata.get('title', ''),
                        'author': doc.metadata.get('author', ''),
                        'creation_date': doc.metadata.get('creationDate', ''),
                        'modification_date': doc.metadata.get('modDate', ''),
                        'processing_method': 'marker',
                        'has_marker_extraction': temp_marker_dir is not None
                    }
                    doc.close()
                else:
                    pdf_metadata = {
                        'processing_method': 'marker',
                        'has_marker_extraction': temp_marker_dir is not None
                    }
            except Exception as e:
                self.log_operation("pdf_metadata_warning", f"Could not extract PDF metadata: {e}", "warning")
                pdf_metadata = {
                    'processing_method': 'marker',
                    'metadata_error': str(e),
                    'has_marker_extraction': temp_marker_dir is not None
                }

            # For marker PDFs, we don't store content separately since marker files contain everything
            summary_content = ""

            end_time = time.time()
            duration = end_time - start_time
            self.log_operation("pdf_marker_completed", f"Marker processing completed in {duration:.2f} seconds")

            result = {
                'content': summary_content,
                'content_filename': f"{clean_pdf_title}.md", 
                'metadata': pdf_metadata,
                'features_available': ['advanced_pdf_extraction', 'figure_extraction', 'table_extraction', 'formula_extraction', 'layout_analysis'],
                'processing_time': f'{duration:.2f}s',
                'skip_content_file': True  # Flag to skip creating extracted_content.md since marker provides better content
            }

            # Add marker extraction result for post-processing
            if temp_marker_dir:
                result['marker_extraction_result'] = {
                    'success': True,
                    'temp_marker_dir': temp_marker_dir,
                    'clean_title': clean_pdf_title
                }

            return result

        except Exception as e:
            self.log_operation("pdf_marker_error", f"Marker processing failed: {e}", "warning")
            # Fallback to PyMuPDF if marker fails
            return self._process_pdf_pymupdf_fallback(file_path, file_metadata)

    def _process_pdf_pymupdf_fallback(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """Fallback PDF text extraction using PyMuPDF when marker is not available."""
        try:
            self.log_operation("pdf_pymupdf_fallback", f"Using PyMuPDF fallback for {file_path}")

            if not fitz:
                raise Exception("PyMuPDF (fitz) is not available")

            doc = fitz.open(file_path)
            content = ""

            # Extract basic metadata
            pdf_metadata = {
                'page_count': doc.page_count,
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'creation_date': doc.metadata.get('creationDate', ''),
                'modification_date': doc.metadata.get('modDate', ''),
                'processing_method': 'pymupdf_fallback'
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
                "content": content,
                "metadata": pdf_metadata,
                "features_available": [
                    "advanced_pdf_extraction",
                    "figure_extraction",
                    "table_extraction",
                ],
                "processing_time": "immediate",
            }

        except Exception as e:
            raise Exception(f"PDF processing failed: {str(e)}")

    async def _process_audio_immediate(
        self, file_path: str, file_metadata: Dict
    ) -> Dict[str, Any]:
        """Quick audio transcription using faster-whisper."""
        try:
            if not self.whisper_model:
                return {
                    "content": f"Audio file '{file_metadata['filename']}' uploaded successfully. Transcription requires faster-whisper installation.",
                    "metadata": self._get_audio_metadata(file_path),
                    "features_available": [
                        "audio_transcription",
                        "speaker_diarization",
                    ],
                    "processing_time": "immediate",
                }

            # Transcribe audio using the new async workflow
            transcript_content, transcript_filename = await self.transcribe_audio_video(
                file_path, file_metadata['filename']
            )

            # Get basic audio info
            audio_metadata = self._get_audio_metadata(file_path)
            audio_metadata.update({
                'transcript_filename': transcript_filename,
                'has_transcript': True,
            })

            return {
                "content": transcript_content,
                "metadata": audio_metadata,
                "features_available": [
                    "speaker_diarization",
                    "sentiment_analysis",
                    "advanced_audio_analysis",
                ],
                "processing_time": "immediate",
                "transcript_filename": transcript_filename
            }

        except Exception as e:
            raise Exception(f"Audio processing failed: {str(e)}")

    async def _process_video_immediate(
        self, file_path: str, file_metadata: Dict
    ) -> Dict[str, Any]:
        """Enhanced video processing with optional image extraction, deduplication, and captioning."""
        try:
            # Extract audio from video for transcription
            audio_path = tempfile.mktemp(suffix='.wav')

            cmd = [
                'ffmpeg', '-i', file_path, '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1', '-y', audio_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            # Initialize content parts
            content_parts = []

            # Process audio transcription if available
            transcript_filename = None
            has_transcript = False

            # Always generate a transcript filename based on the video name
            base_title = Path(file_metadata['filename']).stem
            cleaned_title = clean_title(base_title)
            transcript_filename = f"{cleaned_title}.md"

            if result.returncode == 0 and self.whisper_model and os.path.exists(audio_path):
                try:
                    transcript_content, _ = await self.transcribe_audio_video(
                        audio_path, file_metadata['filename']
                    )
                    content_parts.append(f"# Transcription\n\n{transcript_content}")
                    has_transcript = True
                except Exception as e:
                    self.log_operation("video_transcription_error", f"Transcription failed: {e}", "warning")
                finally:
                    # Clean up extracted audio
                    if os.path.exists(audio_path):
                        os.unlink(audio_path)
            else:
                # If no audio or transcription failed
                if result.returncode != 0:
                    content_parts.append(f"# Video: {file_metadata['filename']}\n\nNo audio track found or audio extraction failed.")
                else:
                    content_parts.append(f"# Video: {file_metadata['filename']}\n\nAudio transcription requires faster-whisper installation.")

            # Get video metadata and add transcript info
            video_metadata = self._get_video_metadata(file_path)
            video_metadata.update({
                'transcript_filename': transcript_filename,
                'has_transcript': has_transcript,
                'has_audio': result.returncode == 0,
            })

            # Combine content
            final_content = "\n\n".join(content_parts)

            return {
                'content': final_content,
                'metadata': video_metadata,
                'features_available': ['frame_extraction', 'scene_analysis', 'speaker_diarization', 'video_analysis'],
                'processing_time': 'immediate',
                'transcript_filename': transcript_filename if has_transcript else None
            }

        except Exception as e:
            raise Exception(f"Video processing failed: {str(e)}")

    def _process_markdown_direct(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """Process markdown files directly, returning the original file without additional processing."""
        try:
            self.log_operation("markdown_direct_processing", f"Processing markdown file directly: {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # For markdown files, we don't use the marker extraction logic.
            # We just return the content and use the original filename.
            # The content will be indexed directly without creating additional files.
            text_metadata = {
                "word_count": len(content.split()),
                "char_count": len(content),
                "line_count": len(content.splitlines()),
                "encoding": "utf-8",
                "processing_method": "direct_markdown",
                "is_markdown_file": True,
            }

            # Use the original filename directly - no processing needed for .md files
            original_filename = file_metadata['filename']

            return {
                "content": content,
                "metadata": text_metadata,
                "features_available": ["content_analysis", "summarization"],
                "processing_time": "immediate",
                "content_filename": original_filename,  # Use original filename
                "use_original_file": True   # Flag to indicate we should use the original uploaded file
            }
        except Exception as e:
            self.log_operation("markdown_direct_error", f"Error processing markdown file directly: {e}", "error")
            raise Exception(f"Markdown processing failed: {str(e)}")

    def _process_text_immediate(
        self, file_path: str, file_metadata: Dict
    ) -> Dict[str, Any]:
        """Process text files immediately."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            text_metadata = {
                "word_count": len(content.split()),
                "char_count": len(content),
                "line_count": len(content.splitlines()),
                "encoding": "utf-8",
            }

            # Check if this is a pasted text file
            is_pasted_text = file_metadata.get('source_type') == 'pasted_text' or file_metadata.get('original_filename') == 'pasted_text.md'
            
            result = {
                "content": content,
                "metadata": text_metadata,
                "features_available": ["content_analysis", "summarization"],
                "processing_time": "immediate",
            }

            # For pasted text, use specific filename to store in content folder
            if is_pasted_text:
                result["content_filename"] = "pasted_text.md"

            return result

        except UnicodeDecodeError:
            # Try different encodings
            for encoding in ["latin-1", "cp1252"]:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        content = f.read()

                    text_metadata = {
                        "word_count": len(content.split()),
                        "char_count": len(content),
                        "line_count": len(content.splitlines()),
                        "encoding": encoding,
                    }

                    return {
                        "content": content,
                        "metadata": text_metadata,
                        "features_available": ["content_analysis", "summarization"],
                        "processing_time": "immediate",
                    }
                except UnicodeDecodeError:
                    continue

            raise Exception(f"Could not decode text file with any supported encoding")
        except Exception as e:
            raise Exception(f"Text processing failed: {str(e)}")

    def parse_files(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """
        Parse various file types using marker_single CLI command.
        Supports PPTX, DOCX, and other document formats.
        Returns markdown content and extracted images.
        """
        try:
            self.log_operation("parse_files_start", f"Starting marker_single processing of {file_path}")
            start_time = time.time()

            # Generate clean filename for output
            original_filename = file_metadata.get('filename', 'document')
            base_title = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
            clean_title_name = clean_title(base_title)

            # Create temporary output directory
            temp_output_dir = tempfile.mkdtemp(suffix='_marker_single_output')
            
            try:
                # Set up environment for marker_single command
                env = os.environ.copy()
                
                # Add conda/pip bin directory to PATH if marker_single is installed there
                import shutil
                marker_path = shutil.which('marker_single')
                if marker_path:
                    marker_dir = os.path.dirname(marker_path)
                    if marker_dir not in env.get('PATH', ''):
                        env['PATH'] = f"{marker_dir}:{env.get('PATH', '')}"
                
                # Add library paths for macOS (for WeasyPrint dependencies)
                if sys.platform == "darwin":
                    # Add Homebrew library paths
                    homebrew_lib = "/opt/homebrew/lib"
                    if os.path.exists(homebrew_lib):
                        env['DYLD_LIBRARY_PATH'] = f"{homebrew_lib}:{env.get('DYLD_LIBRARY_PATH', '')}"
                
                # Run marker_single command
                cmd = [
                    'marker_single',
                    file_path,
                    '--output_format', 'markdown',
                    '--output_dir', temp_output_dir
                ]
                
                self.log_operation("parse_files_command", f"Running: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    env=env
                )
                
                if result.returncode != 0:
                    error_msg = f"marker_single failed with return code {result.returncode}"
                    if result.stderr:
                        error_msg += f": {result.stderr}"
                    raise Exception(error_msg)

                # Find generated markdown file
                markdown_content = ""
                generated_files = []
                image_files = []
                
                for root, _, files in os.walk(temp_output_dir):
                    for file in files:
                        file_path_full = os.path.join(root, file)
                        generated_files.append(file_path_full)
                        
                        if file.endswith('.md'):
                            with open(file_path_full, 'r', encoding='utf-8') as f:
                                markdown_content = f.read()
                        elif file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                            image_files.append(file_path_full)

                # Get file metadata
                processing_metadata = {
                    'processing_method': 'marker_single',
                    'file_type': file_metadata.get('file_extension', '').lower(),
                    'generated_files_count': len(generated_files),
                    'image_files_count': len(image_files),
                    'has_images': len(image_files) > 0,
                    'has_marker_extraction': temp_output_dir is not None
                }

                end_time = time.time()
                duration = end_time - start_time
                self.log_operation("parse_files_completed", 
                    f"marker_single processing completed in {duration:.2f} seconds, generated {len(generated_files)} files")

                # For marker_single files, we don't store content separately since marker files contain everything
                summary_content = ""

                result = {
                    'content': summary_content,
                    'content_filename': f"{clean_title_name}.md", 
                    'metadata': processing_metadata,
                    'features_available': ['text_extraction', 'image_extraction', 'document_parsing', 'advanced_document_extraction'],
                    'processing_time': f'{duration:.2f}s',
                    'skip_content_file': True  # Flag to skip creating extracted_content.md since marker provides better content
                }

                # Add marker extraction result for post-processing (preserve temp directory)
                if temp_output_dir and generated_files:
                    result['marker_extraction_result'] = {
                        'success': True,
                        'temp_marker_dir': temp_output_dir,
                        'clean_title': clean_title_name
                    }
                else:
                    # Clean up temp directory if no files were generated
                    if temp_output_dir and os.path.exists(temp_output_dir):
                        import shutil
                        shutil.rmtree(temp_output_dir, ignore_errors=True)
                    
                    # Fallback content if marker_single failed to generate files
                    if not markdown_content:
                        file_ext = file_metadata.get('file_extension', '').lower()
                        markdown_content = f"# {clean_title_name}\n\nProcessed {file_ext} document using marker_single.\n"
                    
                    result['content'] = markdown_content
                    result['skip_content_file'] = False

                return result

            except subprocess.TimeoutExpired:
                raise Exception("marker_single processing timed out after 5 minutes")
            except FileNotFoundError:
                raise Exception("marker_single command not found. Please ensure marker-pdf is installed.")
            except Exception as e:
                # Clean up temp directory on error
                if temp_output_dir and os.path.exists(temp_output_dir):
                    import shutil
                    shutil.rmtree(temp_output_dir, ignore_errors=True)
                raise Exception(f"marker_single processing failed: {str(e)}")

        except Exception as e:
            self.log_operation("parse_files_error", f"Parse files failed: {e}", "error")
            raise Exception(f"File parsing failed: {str(e)}")

    def _process_presentation_immediate(
        self, file_path: str, file_metadata: Dict
    ) -> Dict[str, Any]:
        """Process presentation files using marker_single."""
        try:
            # Use the new parse_files function for presentations
            return self.parse_files(file_path, file_metadata)

        except Exception as e:
            # Fallback to placeholder if marker_single fails
            self.log_operation("presentation_marker_fallback", f"marker_single failed, using fallback: {e}", "warning")
            
            ppt_metadata = {"file_type": "presentation", "supported_extraction": False}
            content = f"Presentation file '{file_metadata['filename']}' uploaded successfully. Content extraction requires marker_single installation."

            return {
                "content": content,
                "metadata": ppt_metadata,
                "features_available": [
                    "slide_extraction",
                    "text_extraction", 
                    "image_extraction",
                ],
                "processing_time": "immediate",
            }

    def _get_audio_metadata(self, file_path: str) -> Dict:
        """Extract audio metadata using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                file_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            import json

            data = json.loads(result.stdout)
            format_info = data.get("format", {})

            return {
                "duration": float(format_info.get("duration", 0)),
                "bitrate": int(format_info.get("bit_rate", 0)),
                "size": int(format_info.get("size", 0)),
                "format_name": format_info.get("format_name", "unknown"),
            }
        except Exception:
            return {"error": "Could not extract audio metadata"}

    def _get_video_metadata(self, file_path: str) -> Dict:
        """Extract video metadata using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                file_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            import json

            data = json.loads(result.stdout)

            # Get video stream info
            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                {},
            )
            format_info = data.get("format", {})

            return {
                "duration": float(format_info.get("duration", 0)),
                "resolution": f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}",
                "fps": video_stream.get("r_frame_rate", "0/0"),
                "codec": video_stream.get("codec_name", "unknown"),
                "format_name": format_info.get("format_name", "unknown"),
                "size": int(format_info.get("size", 0)),
            }
        except Exception:
            return {'error': 'Could not extract video metadata'}
    

    def _post_process_marker_extraction(self, file_id: str, marker_extraction_result: Dict[str, Any]):
        """
        Post-process marker PDF extraction results by storing them in MinIO.
        This replaces the file system organization with MinIO object storage.
        """
        try:
            if not marker_extraction_result.get("success"):
                return

            temp_marker_dir = marker_extraction_result.get("temp_marker_dir")

            if not temp_marker_dir or not os.path.exists(temp_marker_dir):
                return

            # Get the MinIO storage service
            if not self.file_storage:
                self.log_operation("marker_extraction_warning", "MinIO file storage service not available", "warning")
                return

            try:
                # Import here to avoid circular imports
                from ..models import KnowledgeBaseItem
                
                # Get the knowledge base item
                kb_item = KnowledgeBaseItem.objects.filter(id=file_id).first()
                if not kb_item:
                    self.log_operation("marker_extraction_warning", f"Could not find knowledge base item for file_id: {file_id}", "warning")
                    return
                
                # Get clean title for file organization
                clean_title = marker_extraction_result.get("clean_title", "document")
                
                # Process files from temp directory and store in MinIO
                content_files = []
                image_files = []
                markdown_content = None  # Store markdown content for figure name extraction
                
                for root, _, files in os.walk(temp_marker_dir):
                    for file in files:
                        source_file = os.path.join(root, file)
                        
                        # Skip all JSON metadata files generated by marker-pdf
                        if file.endswith('.json'):
                            continue
                        
                        # Read file content
                        with open(source_file, 'rb') as f:
                            file_content = f.read()
                        
                        # Determine file type and store in appropriate MinIO prefix
                        if file.endswith(('.md', '.json')):
                            # Content files go to 'kb' prefix
                            if file.endswith('.md'):
                                # For any markdown file (from marker_single or marker_pdf), use clean title
                                target_filename = f"{clean_title}.md"
                            else:
                                target_filename = file
                            
                            # Store in MinIO using file ID structure
                            object_key = self.file_storage.minio_backend.save_file_with_auto_key(
                                content=file_content,
                                filename=target_filename,
                                prefix="kb",
                                content_type="text/markdown" if file.endswith('.md') else "application/json",
                                metadata={
                                    'kb_item_id': str(kb_item.id),
                                    'user_id': str(kb_item.notebook.user.id),
                                    'file_type': 'marker_content',
                                    'marker_original_file': file,
                                },
                                user_id=str(kb_item.notebook.user.id),
                                file_id=str(kb_item.id)
                            )
                            
                            content_files.append({
                                'original_filename': file,
                                'target_filename': target_filename,
                                'object_key': object_key
                            })
                            
                            # Update the knowledge base item's file_object_key if this is a markdown file
                            if file.endswith('.md'):
                                kb_item.file_object_key = object_key
                                # Also store markdown content inline for RAG system compatibility
                                markdown_content = file_content.decode('utf-8', errors='ignore')
                                kb_item.content = markdown_content
                                
                        elif file.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg')):
                            # Image files go to kb folder with file ID structure in images subfolder
                            target_filename = file
                            
                            # Determine content type
                            import mimetypes
                            content_type, _ = mimetypes.guess_type(target_filename)
                            content_type = content_type or 'application/octet-stream'
                            
                            # Create KnowledgeBaseImage record first to get ID
                            from ..models import KnowledgeBaseImage
                            
                            # Process images without figure names
                            
                            # Create a temporary record to get the ID
                            kb_image = KnowledgeBaseImage(
                                knowledge_base_item=kb_item,
                                image_caption="",  # Will be filled later if caption data is available
                                content_type=content_type,
                                file_size=len(file_content),
                                image_metadata={
                                    'original_filename': target_filename,
                                    'file_size': len(file_content),
                                    'content_type': content_type,
                                    'kb_item_id': str(kb_item.id),
                                    'source': 'marker_extraction',
                                    'marker_original_file': file,
                                }
                            )
                            
                            # Store in MinIO using file ID structure with images subfolder and UUID
                            object_key = self.file_storage.minio_backend.save_file_with_auto_key(
                                content=file_content,
                                filename=target_filename,
                                prefix="kb",
                                content_type=content_type,
                                metadata={
                                    'kb_item_id': str(kb_item.id),
                                    'user_id': str(kb_item.notebook.user.id),
                                    'file_type': 'marker_image',
                                    'marker_original_file': file,
                                },
                                user_id=str(kb_item.notebook.user.id),
                                file_id=str(kb_item.id),
                                subfolder="images",
                                subfolder_uuid=str(kb_image.id)
                            )
                            
                            # Now set the object key and save the record
                            try:
                                kb_image.minio_object_key = object_key
                                kb_image.save()
                                
                                self.log_operation(
                                    "marker_image_db_created", 
                                    f"Created KnowledgeBaseImage record: id={kb_image.id}, object_key={object_key}"
                                )
                                
                            except Exception as e:
                                self.log_operation(
                                    "marker_image_db_error", 
                                    f"Failed to create KnowledgeBaseImage record for {target_filename}: {str(e)}", 
                                    "error"
                            )
                            
                            image_files.append({
                                'original_filename': file,
                                'target_filename': target_filename,
                                'object_key': object_key
                            })
                            
                        else:
                            # Other files go to 'kb' prefix as content
                            target_filename = file
                            
                            # Store in MinIO using file ID structure
                            object_key = self.file_storage.minio_backend.save_file_with_auto_key(
                                content=file_content,
                                filename=target_filename,
                                prefix="kb",
                                metadata={
                                    'kb_item_id': str(kb_item.id),
                                    'user_id': str(kb_item.notebook.user.id),
                                    'file_type': 'marker_other',
                                    'marker_original_file': file,
                                },
                                user_id=str(kb_item.notebook.user.id),
                                file_id=str(kb_item.id)
                            )
                            
                            content_files.append({
                                'original_filename': file,
                                'target_filename': target_filename,
                                'object_key': object_key
                            })
                
                # Update the knowledge base item's metadata with MinIO object keys
                if not kb_item.file_metadata:
                    kb_item.file_metadata = {}
                
                kb_item.file_metadata['marker_extraction'] = {
                    'success': True,
                    'content_files': content_files,
                    'image_files': image_files,
                    'total_files': len(content_files) + len(image_files),
                    'extraction_timestamp': datetime.now(timezone.utc).isoformat(),
                    'storage_backend': 'minio'
                }
                
                # Store image object keys for future reference
                if image_files:
                    kb_item.file_metadata['image_object_keys'] = [f['object_key'] for f in image_files]
                    kb_item.file_metadata['image_count'] = len(image_files)
                
                kb_item.save()
                
                # Schedule async caption generation if images were created
                if image_files:
                    try:
                        # Mark that caption generation is needed and schedule the task
                        kb_item.file_metadata['caption_generation_status'] = 'pending'
                        kb_item.file_metadata['images_requiring_captions'] = len(image_files)
                        kb_item.save()
                        
                        self.log_operation("marker_caption_preparing", 
                            f"Preparing to schedule caption generation for {len(image_files)} images in KB item {kb_item.id}")
                        
                        # Schedule caption generation as an async task
                        try:
                            from ..tasks import generate_image_captions_task
                            # Convert UUID to string for Celery serialization
                            kb_item_id_str = str(kb_item.id)
                            task_result = generate_image_captions_task.delay(kb_item_id_str)
                            
                            self.log_operation("marker_caption_scheduling", 
                                f"Scheduled caption generation task {task_result.id} for {len(image_files)} images in KB item {kb_item_id_str}")
                        except ImportError as import_error:
                            raise Exception(f"Failed to import caption generation task: {str(import_error)}")
                        except Exception as task_error:
                            raise Exception(f"Failed to schedule Celery task: {str(task_error)}")
                        
                    except Exception as caption_error:
                        # If task scheduling fails, mark caption generation as failed
                        kb_item.file_metadata['caption_generation_status'] = 'failed'
                        kb_item.file_metadata['caption_generation_error'] = str(caption_error)
                        kb_item.save()
                        
                        self.log_operation("marker_caption_scheduling_error", 
                            f"Failed to schedule caption generation for KB item {kb_item.id}: {str(caption_error)}", "error")
                
                # Log summary
                total_files = len(content_files) + len(image_files)
                self.log_operation("marker_extraction_minio_summary", 
                    f"Stored {total_files} marker files in MinIO: {len(content_files)} content files, {len(image_files)} image files")
                
                if content_files:
                    content_file_names = [f['target_filename'] for f in content_files]
                    self.log_operation("marker_content_files_minio", f"Content files stored: {content_file_names}")
                if image_files:
                    image_file_names = [f['target_filename'] for f in image_files]
                    self.log_operation("marker_image_files_minio", f"Image files stored: {image_file_names}")
                
                # Clean up the now-empty temp directory
                try:
                    import shutil
                    shutil.rmtree(temp_marker_dir)
                    self.log_operation("marker_cleanup", f"Cleaned up temporary directory: {temp_marker_dir}")
                except Exception as cleanup_error:
                    self.log_operation("marker_cleanup_warning", f"Could not clean up temp marker directory: {cleanup_error}", "warning")
                    
            except Exception as e:
                self.log_operation("marker_extraction_minio_error", f"MinIO storage error while processing file_id {file_id}: {e}", "error")

        except Exception as e:
            self.log_operation("post_process_marker_extraction_minio_error", f"Failed to store marker extraction results in MinIO: {e}", "error")
            # Clean up temp directory if it still exists
            temp_marker_dir = marker_extraction_result.get("temp_marker_dir")
            if temp_marker_dir and os.path.exists(temp_marker_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_marker_dir)
                except Exception as cleanup_error:
                    self.log_operation("marker_cleanup_warning", f"Could not clean up temp marker directory: {cleanup_error}", "warning")

    def _populate_image_captions_for_kb_item(self, kb_item, markdown_content=None):
        """
        Populate image captions for all images in a knowledge base item.
        Uses markdown extraction first, then AI generation as fallback.
        """
        try:
            # Get markdown content if not provided
            if not markdown_content:
                markdown_content = self._get_markdown_content_for_captions(kb_item)
            
            if not markdown_content:
                self.log_operation("caption_population_warning", 
                    f"No markdown content found for KB item {kb_item.id}, using AI-only captions", "warning")
            
            # Get all images for this knowledge base item that need captions
            from ..models import KnowledgeBaseImage
            images_needing_captions = KnowledgeBaseImage.objects.filter(
                knowledge_base_item=kb_item,
                image_caption__in=['', None]
            ).order_by('created_at')
            
            if not images_needing_captions.exists():
                return
                
            # Extract figure data from markdown if available
            figure_data = []
            if markdown_content and extract_figure_data_from_markdown:
                figure_data = self._extract_figure_data_from_content_for_captions(markdown_content)
            
            # Process each image
            updated_count = 0
            ai_generated_count = 0
            
            for image in images_needing_captions:
                try:
                    caption = None
                    caption_source = None
                    
                    # Try to find caption from markdown first
                    if figure_data:
                        caption = self._find_caption_for_image_in_upload(image, figure_data, images_needing_captions)
                        if caption:
                            caption_source = "markdown"
                    
                    # Use AI generation as fallback if no caption found from markdown
                    if not caption and generate_caption_for_image:
                        caption = self._generate_ai_caption_for_upload(image)
                        if caption and not caption.startswith("Caption generation failed"):
                            caption_source = "AI"
                            ai_generated_count += 1
                    
                    # Update the image with the caption
                    if caption:
                        image.image_caption = caption
                        image.save(update_fields=['image_caption', 'updated_at'])
                        updated_count += 1
                        self.log_operation("caption_updated", 
                            f"Updated image {image.id} with {caption_source} caption: {caption[:50]}...")
                    else:
                        self.log_operation("caption_not_found", 
                            f"No caption found for image {image.id}", "warning")
                
                except Exception as e:
                    self.log_operation("caption_image_error", 
                        f"Error processing image {image.id}: {e}", "error")
                        
            # Log summary
            self.log_operation("caption_population_summary", 
                f"Updated {updated_count} images with captions ({ai_generated_count} AI-generated)")
                
        except Exception as e:
            self.log_operation("caption_population_error", 
                f"Error populating captions for KB item {kb_item.id}: {e}", "error")

    def _get_markdown_content_for_captions(self, kb_item):
        """Get markdown content from knowledge base item using model manager."""
        try:
            from ..models import KnowledgeBaseItem
            
            # Use the model manager to get content
            content = KnowledgeBaseItem.objects.get_content(str(kb_item.id), kb_item.notebook.user.pk)
            return content
            
        except Exception as e:
            self.log_operation("get_markdown_content_error", 
                f"Error getting markdown content for KB item {kb_item.id}: {e}", "error")
            return None

    def _extract_figure_data_from_content_for_captions(self, content):
        """Extract figure data from markdown content using a temporary file."""
        try:
            # Create a temporary markdown file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Extract figure data using the image_utils function
                figure_data = extract_figure_data_from_markdown(temp_file_path)
                return figure_data or []
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            self.log_operation("extract_figure_data_error", 
                f"Error extracting figure data from content: {e}", "error")
            return []

    def _find_caption_for_image_in_upload(self, image, figure_data, all_images):
        """Find matching caption for an image from figure data."""
        try:
            # Try to match by image name from object key first
            if image.minio_object_key:
                image_basename = os.path.basename(image.minio_object_key).lower()
                for figure in figure_data:
                    figure_image_path = figure.get('image_path', '')
                    if figure_image_path:
                        figure_basename = figure_image_path.split('/')[-1].lower()
                        if figure_basename == image_basename:
                            return figure.get('caption', '')
            
            # Fallback: match by index in the figure data list
            # Use the creation order as an approximation
            if figure_data:
                try:
                    image_index = list(all_images).index(image)
                    if image_index < len(figure_data):
                        return figure_data[image_index].get('caption', '')
                except (ValueError, IndexError):
                    pass
            
            return None
            
        except Exception as e:
            self.log_operation("find_caption_error", 
                f"Error finding caption for image {image.id}: {e}", "error")
            return None
    
    def _generate_ai_caption_for_upload(self, image, api_key=None):
        """Generate AI caption for an image using OpenAI vision model."""
        try:
            # Download image from MinIO to a temporary file
            temp_image_path = self._download_image_to_temp_for_caption(image)
            
            if not temp_image_path:
                self.log_operation("ai_caption_download_error", 
                    f"Could not download image {image.id} from MinIO for AI captioning", "error")
                return None
            
            try:
                # Generate caption using AI
                caption = generate_caption_for_image(temp_image_path, api_key=api_key)
                return caption
            
            finally:
                # Clean up temporary file
                if os.path.exists(temp_image_path):
                    os.unlink(temp_image_path)
            
        except Exception as e:
            self.log_operation("ai_caption_generation_error", 
                f"Error generating AI caption for image {image.id}: {e}", "error")
            return None
    
    def _download_image_to_temp_for_caption(self, image):
        """Download image from MinIO to a temporary file for caption generation."""
        try:
            # Get image content from MinIO
            image_content = image.get_image_content()
            
            if not image_content:
                return None
            
            # Determine file extension from content type or object key
            file_extension = '.png'  # default
            if image.content_type:
                if 'jpeg' in image.content_type or 'jpg' in image.content_type:
                    file_extension = '.jpg'
                elif 'png' in image.content_type:
                    file_extension = '.png'
                elif 'gif' in image.content_type:
                    file_extension = '.gif'
                elif 'webp' in image.content_type:
                    file_extension = '.webp'
            elif image.minio_object_key:
                # Try to get extension from object key
                object_key_lower = image.minio_object_key.lower()
                if object_key_lower.endswith('.jpg') or object_key_lower.endswith('.jpeg'):
                    file_extension = '.jpg'
                elif object_key_lower.endswith('.png'):
                    file_extension = '.png'
                elif object_key_lower.endswith('.gif'):
                    file_extension = '.gif'
                elif object_key_lower.endswith('.webp'):
                    file_extension = '.webp'
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                suffix=file_extension, 
                delete=False
            ) as temp_file:
                temp_file.write(image_content)
                temp_file_path = temp_file.name
            
            return temp_file_path
            
        except Exception as e:
            self.log_operation("download_image_temp_error", 
                f"Error downloading image {image.id} to temp file: {e}", "error")
            return None


# Global singleton instance
upload_processor = UploadProcessor()