"""
Media Processors - Handle video and audio specific processing logic
"""
import os
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MediaProcessor:
    """
    Media feature extraction service for processing videos to extract images with deduplication and captioning.
    """

    def __init__(self):
        self.service_name = "media_extractor"
        self.logger = logging.getLogger(f"{__name__}.media_extractor")
        self.supported_video_formats = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.3gp', '.ogv', '.m4v'}
        self.supported_audio_formats = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg'}
        self._clip_model = None
        self._clip_preprocess = None
        self._device = None
        self._whisper_model = None

    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log service operations with consistent formatting."""
        message = f"[{self.service_name}] {operation}"
        if details:
            message += f": {details}"
        getattr(self.logger, level)(message)

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from media file using ffprobe."""
        try:
            import subprocess
            import json
            
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            metadata = {
                'format': data.get('format', {}),
                'streams': data.get('streams', []),
                'duration': float(data.get('format', {}).get('duration', 0)),
                'size': int(data.get('format', {}).get('size', 0)),
                'bitrate': int(data.get('format', {}).get('bit_rate', 0))
            }
            
            # Extract video/audio specific info
            for stream in metadata['streams']:
                if stream.get('codec_type') == 'video':
                    metadata['has_video'] = True
                    metadata['video_codec'] = stream.get('codec_name')
                    metadata['width'] = stream.get('width')
                    metadata['height'] = stream.get('height')
                elif stream.get('codec_type') == 'audio':
                    metadata['has_audio'] = True
                    metadata['audio_codec'] = stream.get('codec_name')
                    metadata['sample_rate'] = stream.get('sample_rate')
                    metadata['channels'] = stream.get('channels')
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata from {file_path}: {e}")
            return {'error': str(e)}

    def is_media_file(self, filename: str) -> bool:
        """Check if file is a supported media file."""
        ext = Path(filename).suffix.lower()
        return ext in self.supported_video_formats or ext in self.supported_audio_formats

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

    async def extract_audio_from_video(self, video_path: str, output_format: str = 'wav') -> str:
        """Extract audio from video file using ffmpeg."""
        try:
            temp_audio_file = tempfile.mktemp(suffix=f'.{output_format}')
            
            cmd = [
                'ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1', temp_audio_file, '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"FFmpeg failed: {result.stderr}")

            return temp_audio_file

        except Exception as e:
            self.logger.error(f"Audio extraction failed: {e}")
            raise

    async def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio file using Whisper."""
        try:
            whisper_model = self.whisper_model
            if not whisper_model:
                return {
                    'transcript': '',
                    'segments': [],
                    'metadata': {'error': 'Whisper model not available'}
                }

            # Transcribe using faster-whisper
            segments, info = whisper_model.transcribe(audio_path)
            
            transcript = ""
            segment_list = []
            
            for segment in segments:
                timestamp_text = f"[{segment.start:.2f}s] {segment.text}"
                transcript += timestamp_text + "\n"
                
                segment_list.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text.strip(),
                    'probability': getattr(segment, 'avg_logprob', 0)
                })

            return {
                'transcript': transcript.strip(),
                'segments': segment_list,
                'metadata': {
                    'duration': info.duration,
                    'language': info.language,
                    'language_probability': info.language_probability,
                    'processing_method': 'faster_whisper',
                    'model': 'base'
                }
            }

        except Exception as e:
            self.logger.error(f"Audio transcription failed: {e}")
            raise

    async def extract_video_frames(self, video_path: str, interval: int = 30, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Extract frames from video at specified intervals."""
        try:
            if not output_dir:
                output_dir = tempfile.mkdtemp(suffix='_video_frames')
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Extract frames using ffmpeg
            cmd = [
                'ffmpeg', '-i', video_path, '-vf', f'fps=1/{interval}',
                os.path.join(output_dir, 'frame_%04d.jpg'), '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"FFmpeg frame extraction failed: {result.stderr}")

            # List extracted frames
            frame_files = []
            for file in os.listdir(output_dir):
                if file.startswith('frame_') and file.endswith('.jpg'):
                    frame_files.append(os.path.join(output_dir, file))
            
            frame_files.sort()

            return {
                'output_directory': output_dir,
                'frame_files': frame_files,
                'frame_count': len(frame_files),
                'interval_seconds': interval,
                'metadata': {
                    'processing_method': 'ffmpeg_frame_extraction',
                    'output_format': 'jpg'
                }
            }

        except Exception as e:
            self.logger.error(f"Frame extraction failed: {e}")
            raise

    def cleanup_temp_files(self, *file_paths):
        """Clean up temporary files."""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        import shutil
                        shutil.rmtree(file_path)
                    self.logger.info(f"Cleaned up temporary file/directory: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup {file_path}: {e}")

    async def _load_clip_model(self, device: Optional[str] = None):
        """Lazy load CLIP model for image deduplication."""
        if self._clip_model and self._clip_preprocess:
            return

        try:
            # Import the image processing functions
            from ..utils.image_processing import load_clip_model_and_preprocessing
            
            self._clip_model, self._clip_preprocess, self._device = load_clip_model_and_preprocessing(device)
            self.logger.info(f"CLIP model loaded successfully for image deduplication on device: {self._device}")
        except Exception as e:
            self.logger.error(f"Failed to load CLIP model: {e}")
            self._clip_model = None
            self._clip_preprocess = None
            self._device = "cpu"

    def _build_image_extraction_options(
        self,
        extract_interval: Optional[int] = None,
        pixel_threshold: Optional[int] = None,
        sequential_deep_threshold: Optional[float] = None,
        global_deep_threshold: Optional[float] = None,
        min_words: Optional[int] = None
    ) -> Dict[str, Any]:
        """Build extraction options dictionary from individual parameters with validation."""
        
        # Define the system defaults
        SYSTEM_DEFAULTS = {
            "extract_interval": 8,
            "pixel_threshold": 3,
            "sequential_deep_threshold": 0.8,
            "global_deep_threshold": 0.85,
            "min_words": 5
        }
        
        options = {}
        
        # Add parameters only if they are provided (not None) with validation
        if extract_interval is not None:
            if extract_interval < 1 or extract_interval > 300:
                raise ValueError("extract_interval must be between 1 and 300 seconds")
            if extract_interval != SYSTEM_DEFAULTS["extract_interval"]:
                options["extract_interval"] = extract_interval
        
        if pixel_threshold is not None:
            if pixel_threshold < 0 or pixel_threshold > 64:
                raise ValueError("pixel_threshold must be between 0 and 64")
            if pixel_threshold != SYSTEM_DEFAULTS["pixel_threshold"]:
                options["pixel_threshold"] = pixel_threshold
        
        if sequential_deep_threshold is not None:
            if sequential_deep_threshold < 0.0 or sequential_deep_threshold > 1.0:
                raise ValueError("sequential_deep_threshold must be between 0.0 and 1.0")
            if sequential_deep_threshold != SYSTEM_DEFAULTS["sequential_deep_threshold"]:
                options["sequential_deep_threshold"] = sequential_deep_threshold
        
        if global_deep_threshold is not None:
            if global_deep_threshold < 0.0 or global_deep_threshold > 1.0:
                raise ValueError("global_deep_threshold must be between 0.0 and 1.0")
            if global_deep_threshold != SYSTEM_DEFAULTS["global_deep_threshold"]:
                options["global_deep_threshold"] = global_deep_threshold
        
        if min_words is not None:
            if min_words < 0 or min_words > 100:
                raise ValueError("min_words must be between 0 and 100")
            if min_words != SYSTEM_DEFAULTS["min_words"]:
                options["min_words"] = min_words
        
        # If no custom options, return None to use system defaults
        return options if options else None

    async def extract_images_with_dedup_and_captions(
        self,
        file_path: str,
        output_dir: str = ".",
        video_title: Optional[str] = None,
        extraction_options: Optional[Dict[str, Any]] = None,
        final_images_dir_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract images from video with full deduplication and captioning pipeline.
        """
        from ..utils.image_processing import (
            extract_frames,
            prepare_work_dir,
            global_pixel_dedupe,
            sequential_deep_dedupe,
            global_deep_dedupe,
            text_ocr_filter_dedupe,
            generate_captions_for_directory
        )
        from ..utils.helpers import clean_title
        
        self.logger.info(f"Starting image extraction with dedup and captions for: {file_path}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found: {file_path}")

        # Default extraction options
        options = {
            "extract_interval": 8,
            "pixel_threshold": 3,
            "sequential_deep_threshold": 0.8,
            "global_deep_threshold": 0.85,
            "device": None,
            "caption_prompt": "Look at the image and do the following in one sentences: Focus more on important numbers or text shown in the image (such as signs, titles, or numbers), and briefly summarize the key points from the text. Give your answer in one clear sentences. Add a tag at the end if you find <chart> or <table> in the image.",
            "ocr_lang": "en",
            "ocr_gpu": True,
            "min_words": 5,
            **(extraction_options or {})
        }

        results = {
            "extraction_type": "image_dedup_captions",
            "file_path": file_path,
            "output_dir": output_dir,
            "options_used": options,
            "success": False,
            "output_files": {},
            "statistics": {},
            "errors": []
        }

        try:
            # Determine video title
            if not video_title:
                video_title = clean_title(Path(file_path).stem)

            # Set up output directories and files
            # Use temporary directories for processing
            temp_images_dir = os.path.join(output_dir, f"{video_title}_Images_temp")
            temp_dedup_dir = os.path.join(output_dir, f"{video_title}_Dedup_Images_temp")
            
            # Final directory name - use custom name if provided, otherwise use default
            if final_images_dir_name:
                final_dir_name = final_images_dir_name
            else:
                final_dir_name = f"{video_title}_Dedup_Images"
            
            final_images_dir = os.path.join(output_dir, final_dir_name)
            captions_file = os.path.join(final_images_dir, "figure_data.json")

            results["output_files"] = {
                "images_dir": temp_images_dir,
                "dedup_dir": temp_dedup_dir,
                "final_images_dir": final_images_dir,
                "captions_file": captions_file
            }

            # Step 1: Extract frames to temp directory
            self.logger.info(f"Extracting frames from {file_path} to {temp_images_dir}")
            extract_frames(file_path, options["extract_interval"], temp_images_dir)

            initial_frame_count = len([f for f in os.listdir(temp_images_dir) if f.lower().endswith('.png')])
            self.logger.info(f"Extracted {initial_frame_count} frames")

            # Step 2: Prepare dedup directory
            prepare_work_dir(temp_images_dir, temp_dedup_dir)

            # Step 3: Load CLIP model for deduplication
            await self._load_clip_model(options["device"])

            if not self._clip_model or not self._clip_preprocess:
                raise Exception("CLIP model failed to load - required for image deduplication")

            # Step 4: Run deduplication pipeline
            self.logger.info("Running image deduplication pipeline...")

            # Initialize logs and removed counts
            logs_pix_global, logs_deep_seq, logs_deep_global, logs_text_ocr = [], [], [], []
            removed_pix_global, removed_deep_seq, removed_deep_global, removed_text_ocr = 0, 0, 0, 0

            # Step 4a: Global pixel deduplication
            self.logger.info("Running global pixel-based deduplication...")
            removed_pix_global, logs_pix_global = global_pixel_dedupe(temp_dedup_dir, options["pixel_threshold"])

            # Step 4b: Sequential deep deduplication
            self.logger.info("Running sequential deep deduplication...")
            removed_deep_seq, logs_deep_seq = sequential_deep_dedupe(
                temp_dedup_dir, options["sequential_deep_threshold"], self._device, self._clip_model, self._clip_preprocess
            )

            # Step 4c: Global deep deduplication
            self.logger.info("Running global deep deduplication...")
            removed_deep_global, logs_deep_global = global_deep_dedupe(
                temp_dedup_dir, options["global_deep_threshold"], self._device, self._clip_model, self._clip_preprocess
            )

            # Step 4d: Text-based filtering
            self.logger.info("Running OCR text filtering...")
            removed_text_ocr, logs_text_ocr = text_ocr_filter_dedupe(
                temp_dedup_dir, options["min_words"], options["ocr_lang"], options["ocr_gpu"]
            )

            final_frame_count = len([f for f in os.listdir(temp_dedup_dir) if f.lower().endswith('.png')])

            # Step 5: Move processed images to final directory
            self.logger.info(f"Moving processed images to final directory: {final_images_dir}")
            if os.path.exists(final_images_dir):
                import shutil
                shutil.rmtree(final_images_dir)
            
            # Create final directory and move images
            os.makedirs(final_images_dir, exist_ok=True)
            
            # Move all processed images to final directory
            import shutil
            for file in os.listdir(temp_dedup_dir):
                if file.lower().endswith('.png'):
                    src_path = os.path.join(temp_dedup_dir, file)
                    dst_path = os.path.join(final_images_dir, file)
                    shutil.move(src_path, dst_path)

            # Step 6: Generate captions
            self.logger.info("Generating AI captions...")
            captions = generate_captions_for_directory(
                images_dir=final_images_dir, 
                output_file=captions_file, 
                prompt=options["caption_prompt"]
            )

            # Step 7: Clean up temporary directories
            self.logger.info("Cleaning up temporary directories...")
            import shutil
            if os.path.exists(temp_images_dir):
                shutil.rmtree(temp_images_dir)
            if os.path.exists(temp_dedup_dir):
                shutil.rmtree(temp_dedup_dir)

            # Compile results
            results.update({
                "success": True,
                "statistics": {
                    "initial_frames": initial_frame_count,
                    "final_frames": final_frame_count,
                    "removed_pixel_global": removed_pix_global,
                    "removed_deep_sequential": removed_deep_seq,
                    "removed_deep_global": removed_deep_global,
                    "removed_text_ocr": removed_text_ocr,
                    "total_removed": initial_frame_count - final_frame_count,
                    "captions_generated": len(captions)
                },
                "deduplication_logs": {
                    "pixel_global": logs_pix_global,
                    "deep_sequential": logs_deep_seq,
                    "deep_global": logs_deep_global,
                    "text_ocr": logs_text_ocr
                }
            })

            self.logger.info(f"Image extraction completed successfully. Final frames: {final_frame_count}")
            self.logger.info(f"Images stored in: {final_images_dir}")
            self.logger.info(f"Captions stored in: {captions_file}")
            
            return results

        except Exception as e:
            self.logger.error(f"Image extraction failed: {str(e)}")
            results["errors"].append(str(e))
            return results

    async def process_video_for_images(
        self,
        file_path: str,
        output_dir: str = ".",
        video_title: Optional[str] = None,
        url: Optional[str] = None,
        extraction_options: Optional[Dict[str, Any]] = None,
        final_images_dir_name: Optional[str] = None,
        **options
    ) -> Dict[str, Any]:
        """
        Main method to process a video file and generate deduplicated images with captions.
        """
        from ..utils.helpers import clean_title
        
        try:
            # Determine video title
            if not video_title:
                if url:
                    video_title = clean_title(Path(file_path).stem)
                else:
                    # Clean the filename to remove temp prefixes
                    filename = Path(file_path).stem
                    if filename.startswith('deepsight_'):
                        parts = filename.split('_', 1)
                        if len(parts) > 1:
                            filename = parts[1]
                    video_title = clean_title(filename)

            # Set up default extraction options
            default_options = {
                "extract_interval": options.get('extract_interval', 8),
                "pixel_threshold": options.get('pixel_threshold', 3),
                "sequential_deep_threshold": options.get('sequential_deep_threshold', 0.8),
                "global_deep_threshold": options.get('global_deep_threshold', 0.85),
                "min_words": options.get('min_words', 5),
                "enable_ocr_filter": options.get('enable_ocr_filter', True),
                "enable_global_pixel_dedupe": options.get('enable_global_pixel_dedupe', True),
                "enable_sequential_deep_dedupe": options.get('enable_sequential_deep_dedupe', True),
                "enable_global_deep_dedupe": options.get('enable_global_deep_dedupe', True),
                "enable_captioning": options.get('enable_captioning', True),
                "output_dir": output_dir,
                "video_title": video_title
            }
            
            # Merge with custom extraction options (custom options override defaults)
            final_extraction_options = {**default_options, **(extraction_options or {})}

            # Run the full image extraction pipeline
            result = await self.extract_images_with_dedup_and_captions(
                file_path, output_dir, video_title, final_extraction_options, final_images_dir_name
            )

            # Add metadata about the processing
            result["processing_metadata"] = {
                "original_url": url,
                "video_title": video_title,
                "processing_type": "video_to_images_with_captions",
                "extraction_options_used": final_extraction_options
            }

            return result

        except Exception as e:
            self.logger.error(f"Video processing for images failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path,
                "output_dir": output_dir
            } 