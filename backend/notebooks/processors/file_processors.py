"""
File Processors - Handle file type specific processing logic
"""
import os
import tempfile
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# Lazy import for marker dependencies
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

logger = logging.getLogger(__name__)


class FileProcessor:
    """Handle file type specific processing"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.file_processor")
        
        # Initialize whisper model lazily
        self._whisper_model = None
        self._pdf_processor = None
    
    @property 
    def whisper_model(self):
        """Lazy load whisper model."""
        if self._whisper_model is None:
            try:
                import faster_whisper
                device = self._detect_device()
                self._whisper_model = faster_whisper.WhisperModel("large-v3-turbo", device=device)
                self.logger.info(f"Loaded Whisper model on {device}")
            except ImportError:
                self.logger.warning("faster-whisper not available")
                self._whisper_model = False
        return self._whisper_model

    @property
    def pdf_processor(self):
        """Lazy load PDF processor."""
        if self._pdf_processor is None:
            try:
                marker_imports = get_marker_imports()
                if marker_imports.get('available'):
                    device = self._detect_device()
                    models = marker_imports['create_model_dict']()
                    config = marker_imports['ConfigParser']({})
                    self._pdf_processor = marker_imports['PdfConverter'](
                        artifact_dict=models,
                        processor_list=config.get_processors(),
                        renderer=config.get_renderer(),
                        extract_images=True
                    )
                    self.logger.info(f"Loaded marker PDF processor on {device}")
                else:
                    self._pdf_processor = False
            except Exception as e:
                self.logger.warning(f"Failed to load PDF processor: {e}")
                self._pdf_processor = False
        return self._pdf_processor

    def _detect_device(self):
        """Detect best available device."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    async def process_file_by_type(self, file_path: str, file_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process file based on its type."""
        file_extension = file_metadata.get('file_extension', '').lower()
        
        if file_extension == '.pdf':
            return self.process_pdf_marker(file_path, file_metadata)
        elif file_extension in ['.mp3', '.wav', '.m4a']:
            return await self.process_audio_immediate(file_path, file_metadata)
        elif file_extension in [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".3gp", ".ogv", ".m4v"]:
            return await self.process_video_immediate(file_path, file_metadata)
        elif file_extension == ".md":
            return self.process_markdown_direct(file_path, file_metadata)
        elif file_extension == ".txt":
            return self.process_text_immediate(file_path, file_metadata)
        elif file_extension in [".ppt", ".pptx"]:
            return self.process_presentation_immediate(file_path, file_metadata)
        else:
            return {
                'content': f"File type {file_extension} is supported but no immediate processing available.",
                'metadata': {},
                'features_available': [],
                'processing_time': 'immediate'
            }

    def process_pdf_marker(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """PDF text extraction using marker package with native image output."""
        try:
            marker_imports = get_marker_imports()
            if not marker_imports.get('available'):
                # Fallback to PyMuPDF if marker is not available
                return self.process_pdf_pymupdf_fallback(file_path, file_metadata)

            self.logger.info(f"Starting marker processing of {file_path}")
            start_time = time.time()

            # Get the marker PDF processor
            pdf_processor = self.pdf_processor
            if not pdf_processor:
                # Fallback to PyMuPDF if marker processor failed to load
                return self.process_pdf_pymupdf_fallback(file_path, file_metadata)

            # Generate clean filename for PDF
            original_filename = file_metadata.get('filename', 'document')
            base_title = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
            
            # Import clean_title function
            try:
                from ..utils.helpers import clean_title
                clean_pdf_title = clean_title(base_title)
            except ImportError:
                clean_pdf_title = base_title

            # Convert the PDF to markdown using marker
            rendered = pdf_processor(str(file_path))

            # Extract the markdown content for display
            content = rendered.text_content if hasattr(rendered, 'text_content') else str(rendered)

            # Save the original marker output to temporary directory for later processing
            temp_marker_dir = None
            try:
                temp_marker_dir = tempfile.mkdtemp(suffix='_marker_output')
                from marker.output import save_output
                save_output(rendered, temp_marker_dir, "markdown")
                self.logger.info(f"Saved marker output to temporary directory: {temp_marker_dir}")
                
            except Exception as e:
                self.logger.warning(f"Could not save marker output: {e}")
                # Fallback: save the text content manually
                try:
                    temp_marker_dir = tempfile.mkdtemp(suffix='_marker_fallback')
                    fallback_md_file = os.path.join(temp_marker_dir, "markdown.md")
                    with open(fallback_md_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.logger.info(f"Saved marker text content to: {fallback_md_file}")
                except Exception as save_error:
                    self.logger.error(f"Failed to save marker output: {save_error}")
                    temp_marker_dir = None

            # Get basic PDF metadata using PyMuPDF
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
                self.logger.warning(f"Could not extract PDF metadata: {e}")
                pdf_metadata = {
                    'processing_method': 'marker',
                    'metadata_error': str(e),
                    'has_marker_extraction': temp_marker_dir is not None
                }

            end_time = time.time()
            duration = end_time - start_time
            self.logger.info(f"Marker processing completed in {duration:.2f} seconds")

            result = {
                'content': "",  # Empty for marker since it provides better content
                'content_filename': f"{clean_pdf_title}.md", 
                'metadata': pdf_metadata,
                'features_available': ['advanced_pdf_extraction', 'figure_extraction', 'table_extraction', 'formula_extraction', 'layout_analysis'],
                'processing_time': f'{duration:.2f}s',
                'skip_content_file': True
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
            self.logger.warning(f"Marker processing failed: {e}")
            # Fallback to PyMuPDF if marker fails
            return self.process_pdf_pymupdf_fallback(file_path, file_metadata)

    def process_pdf_pymupdf_fallback(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """Fallback PDF text extraction using PyMuPDF when marker is not available."""
        try:
            self.logger.info(f"Using PyMuPDF fallback for {file_path}")

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

    async def process_audio_immediate(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """Quick audio transcription using faster-whisper."""
        try:
            self.logger.info(f"Processing audio file: {file_path}")
            start_time = time.time()

            whisper_model = self.whisper_model
            if not whisper_model:
                return {
                    'content': f"Audio file '{file_metadata['filename']}' uploaded successfully. Transcription not available (faster-whisper not installed).",
                    'metadata': {'processing_method': 'audio_upload_only'},
                    'features_available': [],
                    'processing_time': 'immediate'
                }

            # Transcribe using faster-whisper
            segments, info = whisper_model.transcribe(file_path)
            
            transcript = ""
            for segment in segments:
                transcript += f"[{segment.start:.2f}s] {segment.text}\n"

            end_time = time.time()
            duration = end_time - start_time

            return {
                'content': transcript,
                'metadata': {
                    'duration': info.duration,
                    'language': info.language,
                    'language_probability': info.language_probability,
                    'processing_method': 'faster_whisper',
                    'model': 'base'
                },
                'features_available': ['audio_transcription', 'timestamped_segments'],
                'processing_time': f'{duration:.2f}s'
            }

        except Exception as e:
            raise Exception(f"Audio processing failed: {str(e)}")

    async def process_video_immediate(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """Process video by extracting audio and transcribing."""
        try:
            self.logger.info(f"Processing video file: {file_path}")
            start_time = time.time()

            # Extract audio from video using ffmpeg
            temp_audio_file = None
            try:
                import subprocess
                temp_audio_file = tempfile.mktemp(suffix='.wav')
                
                cmd = [
                    'ffmpeg', '-i', file_path, '-vn', '-acodec', 'pcm_s16le',
                    '-ar', '16000', '-ac', '1', temp_audio_file, '-y'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"FFmpeg failed: {result.stderr}")

                # Transcribe the extracted audio
                audio_result = await self.process_audio_immediate(temp_audio_file, file_metadata)
                
                end_time = time.time()
                duration = end_time - start_time

                return {
                    'content': audio_result['content'],
                    'metadata': {
                        **audio_result['metadata'],
                        'original_type': 'video',
                        'video_processing_method': 'ffmpeg_audio_extraction'
                    },
                    'features_available': audio_result['features_available'] + ['video_to_audio_conversion'],
                    'processing_time': f'{duration:.2f}s'
                }

            finally:
                # Clean up temporary audio file
                if temp_audio_file and os.path.exists(temp_audio_file):
                    os.unlink(temp_audio_file)

        except Exception as e:
            raise Exception(f"Video processing failed: {str(e)}")

    def process_markdown_direct(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """Process markdown files directly."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                'content': content,
                'metadata': {
                    'processing_method': 'markdown_direct',
                    'character_count': len(content),
                    'line_count': len(content.splitlines())
                },
                'features_available': ['markdown_parsing', 'direct_content'],
                'processing_time': 'immediate'
            }

        except Exception as e:
            raise Exception(f"Markdown processing failed: {str(e)}")

    def process_text_immediate(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """Process plain text files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                'content': content,
                'metadata': {
                    'processing_method': 'text_direct',
                    'character_count': len(content),
                    'line_count': len(content.splitlines()),
                    'word_count': len(content.split())
                },
                'features_available': ['text_parsing', 'direct_content'],
                'processing_time': 'immediate'
            }

        except Exception as e:
            raise Exception(f"Text processing failed: {str(e)}")

    def process_presentation_immediate(self, file_path: str, file_metadata: Dict) -> Dict[str, Any]:
        """Process PowerPoint presentations."""
        try:
            content = ""
            
            try:
                from pptx import Presentation
                prs = Presentation(file_path)
                
                for i, slide in enumerate(prs.slides):
                    content += f"\n=== Slide {i + 1} ===\n"
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            content += shape.text + "\n"

                return {
                    'content': content,
                    'metadata': {
                        'processing_method': 'python_pptx',
                        'slide_count': len(prs.slides)
                    },
                    'features_available': ['text_extraction', 'slide_structure'],
                    'processing_time': 'immediate'
                }

            except ImportError:
                # Fallback message if python-pptx is not available
                return {
                    'content': f"PowerPoint file '{file_metadata['filename']}' uploaded successfully. Text extraction not available (python-pptx not installed).",
                    'metadata': {'processing_method': 'presentation_upload_only'},
                    'features_available': [],
                    'processing_time': 'immediate'
                }

        except Exception as e:
            raise Exception(f"Presentation processing failed: {str(e)}") 