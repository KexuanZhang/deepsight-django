"""
Immediate file processing on upload - designed to be fast and synchronous.
"""

import os
import tempfile
import subprocess
import asyncio
import logging
import time
import re
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# Django imports for file handling
from django.core.files.uploadedfile import UploadedFile as UploadFile
from django.http import Http404
from django.core.exceptions import ValidationError

try:
    from .file_storage import FileStorageService
    from .content_index import ContentIndexingService
    from .file_validator import FileValidator
    from .config import config as settings
except ImportError:
    # Fallback classes to prevent import errors
    FileStorageService = None
    ContentIndexingService = None
    FileValidator = None
    settings = None

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
    """Handles immediate processing of uploaded files."""

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

        self.logger.info("Upload processor service initialized")

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
            cleaned_title = self._clean_title(base_title)
            suggested_filename = f"{cleaned_title}_transcript.md"
            
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
            return self.file_storage.delete_file_by_upload_id(upload_file_id, user_pk)
        except Exception as e:
            self.log_operation("delete_upload_error", str(e), "error")
            return False

    def _update_upload_status(self, upload_file_id: str, status: str, **kwargs):
        """Update the status of an upload."""
        if upload_file_id:
            current_status = self._upload_statuses.get(upload_file_id, {})
            current_status.update(
                {
                    "upload_file_id": upload_file_id,
                    "status": status,
                    "parsing_status": status,
                    "updated_at": datetime.now().isoformat(),
                    **kwargs,
                }
            )
            self._upload_statuses[upload_file_id] = current_status

    async def process_upload(
        self,
        file: UploadFile,
        upload_file_id: Optional[str] = None,
        user_pk: Optional[int] = None,
        notebook_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Main entry point for immediate file processing."""
        print("upload")
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

            # Prepare file metadata with original file information
            file_metadata = {
                "filename": file.name,
                "original_filename": file.name,  # Ensure original filename is preserved
                "file_extension": validation["file_extension"],
                "content_type": validation["content_type"],
                "file_size": file_size,
                "upload_file_id": upload_file_id,
                "upload_timestamp": datetime.now().isoformat(),
                "parsing_status": "processing",
            }

            # Process based on file type
            processing_result = await self._process_file_by_type(temp_path, file_metadata)

            # Update file metadata with parsing status
            file_metadata["parsing_status"] = "completed"

            # Store result with user isolation
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
            store_file_sync = sync_to_async(self.file_storage.store_processed_file, thread_sensitive=False)
            file_id = await store_file_sync(
                content=processing_result["content"],
                metadata=file_metadata,
                processing_result=processing_result_for_storage,
                user_id=user_pk,
                notebook_id=notebook_id,
                original_file_path=temp_path,
            )

            # Run synchronous content indexing in executor
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
                )

            # ------------------------------------------------------
            # Queue asynchronous transcript generation if requested
            # ------------------------------------------------------
            if processing_result.get("needs_async_transcript"):
                try:
                    from notebooks.tasks import generate_transcript_task
                    generate_transcript_task.delay(file_id)
                except Exception as e:
                    self.log_operation("queue_transcript_error", str(e), "error")

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
                delete=False, suffix=suffix, prefix="deepsight_"
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
        elif file_extension in [".txt", ".md"]:
            return self._process_text_immediate(file_path, file_metadata)
        elif file_extension in [".ppt", ".pptx"]:
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
            clean_pdf_title = self._clean_title(base_title)

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
                for root, dirs, files in os.walk(temp_marker_dir):
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
                'content_filename': f"{clean_pdf_title}_parsed.md",  # Prevent content.md creation
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

            # -----------------------------------------------
            # Asynchronous transcription placeholder
            # -----------------------------------------------

            base_title = Path(file_metadata['filename']).stem
            cleaned_title = self._clean_title(base_title)
            transcript_filename = f"{cleaned_title}_transcript.md"

            # Always include a placeholder; real transcript will be added by Celery task
            placeholder = (
                "Audio transcription will be processed asynchronously. "
                "Wait until the transcript appears here …"
            )

            content_parts.append(f"# Video: {file_metadata['filename']}\n\n{placeholder}")

            # Video metadata – mark that transcript is pending
            video_metadata = self._get_video_metadata(file_path)
            video_metadata.update({
                'transcript_filename': transcript_filename,
                'has_transcript': False,
                'has_audio': result.returncode == 0,
            })

            # Clean up extracted audio file to save disk space
            try:
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
            except Exception:
                pass

            final_content = "\n\n".join(content_parts)

            return {
                'content': final_content,
                'metadata': video_metadata,
                'features_available': ['frame_extraction', 'scene_analysis', 'speaker_diarization', 'video_analysis'],
                'processing_time': 'immediate',
                'transcript_filename': transcript_filename,
                'needs_async_transcript': True
            }

        except Exception as e:
            raise Exception(f"Video processing failed: {str(e)}")

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

    def _process_presentation_immediate(
        self, file_path: str, file_metadata: Dict
    ) -> Dict[str, Any]:
        """Process presentation files."""
        try:
            # For now, return placeholder - would need python-pptx for full implementation
            ppt_metadata = {"file_type": "presentation", "supported_extraction": False}

            content = f"Presentation file '{file_metadata['filename']}' uploaded successfully. Content extraction requires additional processing."

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

        except Exception as e:
            raise Exception(f"Presentation processing failed: {str(e)}")

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
    
    def _get_device_info(self):
        """Get information about available compute devices."""
        device_info = []
        
        # Check for CUDA
        try:
            import torch
            if torch.cuda.is_available():
                device_info.append(f"CUDA ({torch.cuda.get_device_name(0)})")
        except ImportError:
            pass
        
        # Check for MPS (Apple Silicon)
        try:
            import torch
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device_info.append("MPS (Apple Silicon)")
        except ImportError:
            pass
        
        if not device_info:
            device_info.append("CPU")
        
        return ", ".join(device_info)
    
    def _clean_title(self, title: str) -> str:
        """Clean the title by replacing non-alphanumeric characters with underscores."""
        # Replace all non-alphanumeric characters (except for underscores) with underscores
        cleaned = re.sub(r'[^\w\d]', '_', title)
        # Replace consecutive underscores with a single underscore
        cleaned = re.sub(r'_+', '_', cleaned)
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        return cleaned 
    
    def _update_image_links_in_markdown(self, markdown_content: str, image_mapping: Dict[str, str], base_images_path: str = "images") -> str:
        """
        Update image links in markdown content to point to the saved image locations.
        
        Args:
            markdown_content: Original markdown content
            image_mapping: Dictionary mapping original image names to saved paths
            base_images_path: Base path for images (default: "images")
            
        Returns:
            Updated markdown content with corrected image links
        """
        if not image_mapping:
            return markdown_content
        
        updated_content = markdown_content
        
        # Pattern to match markdown image syntax: ![alt text](image_path)
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        def replace_image_link(match):
            alt_text = match.group(1)
            original_path = match.group(2)
            
            # Extract filename from the original path
            original_filename = os.path.basename(original_path)
            
            # Check if we have a saved version of this image
            if original_filename in image_mapping:
                # If the mapping value starts with "../", use it as-is (for relative paths)
                if image_mapping[original_filename].startswith("../"):
                    new_path = image_mapping[original_filename]
                else:
                    # Use relative path for markdown
                    new_path = f"{base_images_path}/{os.path.basename(image_mapping[original_filename])}"
                return f"![{alt_text}]({new_path})"
            
            # If no mapping found, return original
            return match.group(0)
        
        updated_content = re.sub(image_pattern, replace_image_link, updated_content)
        
        self.log_operation("update_image_links", f"Updated {len(image_mapping)} image links in markdown")
        
        return updated_content

    def _update_markdown_image_paths(self, markdown_file_path: Path, image_files: list):
        """
        Update image paths in a markdown file to point to the new images directory.
        
        Args:
            markdown_file_path: Path to the markdown file to update
            image_files: List of image filenames that were moved to images/ directory
        """
        try:
            # Read the current markdown content
            with open(markdown_file_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Create a set of image filenames for quick lookup
            image_filename_set = set(image_files)
            
            # Pattern to match markdown image syntax: ![alt text](image_path)
            image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
            
            def replace_image_link(match):
                alt_text = match.group(1)
                original_path = match.group(2)
                
                # Extract filename from the original path
                original_filename = os.path.basename(original_path)
                
                # Check if this image was moved to the images directory
                if original_filename in image_filename_set:
                    # Update path to point to ../images/ (relative to content directory)
                    new_path = f"../images/{original_filename}"
                    return f"![{alt_text}]({new_path})"
                
                # If image not in our moved files, return original
                return match.group(0)
            
            # Apply the replacements
            updated_content = re.sub(image_pattern, replace_image_link, markdown_content)
            
            # Write the updated content back to the file
            with open(markdown_file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            # Count how many replacements were made
            original_matches = len(re.findall(image_pattern, markdown_content))
            updated_matches = len(re.findall(r'!\[([^\]]*)\]\(\.\./images/[^)]+\)', updated_content))
            
            self.log_operation("update_markdown_paths", 
                f"Updated image paths in {markdown_file_path.name}: {updated_matches} of {original_matches} images updated to ../images/ paths")
            
        except Exception as e:
            self.log_operation("update_markdown_paths_error", 
                f"Failed to update image paths in {markdown_file_path}: {e}", "error")

    def _post_process_marker_extraction(self, file_id: str, marker_extraction_result: Dict[str, Any]):
        """Move marker PDF extraction results to the correct directory structure."""
        try:
            if not marker_extraction_result.get("success"):
                return

            temp_marker_dir = marker_extraction_result.get("temp_marker_dir")

            if not temp_marker_dir or not os.path.exists(temp_marker_dir):
                return

            # Get the file storage base path and organize files correctly
            if self.file_storage:
                try:
                    # Import here to avoid circular imports
                    from ..models import KnowledgeBaseItem
                    
                    # Get the knowledge base item to find the file location
                    kb_item = KnowledgeBaseItem.objects.filter(id=file_id).first()
                    if not kb_item:
                        self.log_operation("marker_extraction_warning", f"Could not find knowledge base item for file_id: {file_id}", "warning")
                        return
                    
                    # Generate paths based on the knowledge base item
                    paths = self.file_storage._generate_knowledge_base_paths(
                        user_id=kb_item.user_id,
                        original_filename=kb_item.title + '.pdf',  # Reconstruct filename
                        kb_item_id=str(kb_item.id)
                    )
                    
                    # Create the directory structure
                    base_dir_path = self.file_storage.base_data_root / paths['base_dir']
                    content_dir = base_dir_path / "content"
                    images_dir = base_dir_path / "images"
                    
                    # Ensure directories exist
                    content_dir.mkdir(parents=True, exist_ok=True)
                    images_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Get clean title for renaming
                    clean_title = marker_extraction_result.get("clean_title", "document")
                    
                    # Move files to appropriate directories
                    content_files = []
                    image_files = []
                    
                    for root, dirs, files in os.walk(temp_marker_dir):
                        for file in files:
                            source_file = os.path.join(root, file)
                            
                            # Determine file type and target directory
                            if file.endswith(('.md', '.json')):
                                # Content files go to content/ directory
                                if file == "markdown.md":
                                    target_filename = f"{clean_title}_parsed.md"
                                else:
                                    target_filename = file
                                
                                target_file = content_dir / target_filename
                                target_dir_name = "content"
                                content_files.append(target_filename)
                                
                            elif file.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg')):
                                # Image files go to images/ directory
                                target_filename = file
                                target_file = images_dir / target_filename
                                target_dir_name = "images"
                                image_files.append(target_filename)
                                
                            else:
                                # Other files go to content/ directory by default
                                target_filename = file
                                target_file = content_dir / target_filename
                                target_dir_name = "content"
                                content_files.append(target_filename)
                            
                            # Handle file name conflicts by overwriting
                            if target_file.exists():
                                target_file.unlink()
                            
                            import shutil
                            shutil.move(source_file, str(target_file))
                            self.log_operation("marker_file_move", f"Moved {file} to {target_dir_name}/{target_filename}")
                    
                    # Log summary
                    total_files = len(content_files) + len(image_files)
                    self.log_operation("marker_extraction_summary", 
                        f"Moved {total_files} files: {len(content_files)} to content/, {len(image_files)} to images/")
                    
                    if content_files:
                        self.log_operation("marker_content_files", f"Content files: {content_files}")
                    if image_files:
                        self.log_operation("marker_image_files", f"Image files: {image_files}")
                    
                    # Update image paths in markdown files after moving files
                    if image_files and content_files:
                        for content_file in content_files:
                            if content_file.endswith('.md'):
                                self._update_markdown_image_paths(content_dir / content_file, image_files)
                    
                    # Clean up the now-empty temp directory
                    try:
                        import shutil
                        shutil.rmtree(temp_marker_dir)
                        self.log_operation("marker_cleanup", f"Cleaned up temporary directory: {temp_marker_dir}")
                    except Exception as cleanup_error:
                        self.log_operation("marker_cleanup_warning", f"Could not clean up temp marker directory: {cleanup_error}", "warning")
                        
                except Exception as e:
                    self.log_operation("marker_extraction_database_error", f"Database error while processing file_id {file_id}: {e}", "error")
            else:
                self.log_operation("marker_extraction_warning", "File storage service not available", "warning")

        except Exception as e:
            self.log_operation("post_process_marker_extraction_error", f"Failed to move marker extraction results: {e}", "error")
            # Clean up temp directory if it still exists
            temp_marker_dir = marker_extraction_result.get("temp_marker_dir")
            if temp_marker_dir and os.path.exists(temp_marker_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_marker_dir)
                except Exception as cleanup_error:
                    self.log_operation("marker_cleanup_warning", f"Could not clean up temp marker directory: {cleanup_error}", "warning")