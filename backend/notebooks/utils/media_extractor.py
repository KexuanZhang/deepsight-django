"""
Media extraction service for video image processing with deduplication and captioning.
"""

import os
import json
import tempfile
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Import the actual image processing functions
from .image_processing import (
    extract_frames,
    prepare_work_dir,
    global_pixel_dedupe,
    sequential_deep_dedupe,
    global_deep_dedupe,
    text_ocr_filter_dedupe,
    load_clip_model_and_preprocessing,
    generate_captions_for_directory,
    clean_title
)

logger = logging.getLogger(__name__)


class MediaFeatureExtractor:
    """
    Media feature extraction service for processing videos to extract images with deduplication and captioning.
    """

    def __init__(self):
        self.service_name = "media_extractor"
        self._clip_model = None
        self._clip_preprocess = None
        self._device = None

    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log service operations with consistent formatting."""
        message = f"[{self.service_name}] {operation}"
        if details:
            message += f": {details}"
        getattr(logger, level)(message)

    async def _load_clip_model(self, device: Optional[str] = None):
        """Lazy load CLIP model for image deduplication."""
        if self._clip_model and self._clip_preprocess:
            return

        try:
            self._clip_model, self._clip_preprocess, self._device = load_clip_model_and_preprocessing(device)
            logger.info(f"CLIP model loaded successfully for image deduplication on device: {self._device}")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
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
        logger.info(f"Starting image extraction with dedup and captions for: {file_path}")

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
            logger.info(f"Extracting frames from {file_path} to {temp_images_dir}")
            extract_frames(file_path, options["extract_interval"], temp_images_dir)

            initial_frame_count = len([f for f in os.listdir(temp_images_dir) if f.lower().endswith('.png')])
            logger.info(f"Extracted {initial_frame_count} frames")

            # Step 2: Prepare dedup directory
            prepare_work_dir(temp_images_dir, temp_dedup_dir)

            # Step 3: Load CLIP model for deduplication
            await self._load_clip_model(options["device"])

            if not self._clip_model or not self._clip_preprocess:
                raise Exception("CLIP model failed to load - required for image deduplication")

            # Step 4: Run deduplication pipeline
            logger.info("Running image deduplication pipeline...")

            # Initialize logs and removed counts
            logs_pix_global, logs_deep_seq, logs_deep_global, logs_text_ocr = [], [], [], []
            removed_pix_global, removed_deep_seq, removed_deep_global, removed_text_ocr = 0, 0, 0, 0

            # Step 4a: Global pixel deduplication
            logger.info("Running global pixel-based deduplication...")
            removed_pix_global, logs_pix_global = global_pixel_dedupe(temp_dedup_dir, options["pixel_threshold"])

            # Step 4b: Sequential deep deduplication
            logger.info("Running sequential deep deduplication...")
            removed_deep_seq, logs_deep_seq = sequential_deep_dedupe(
                temp_dedup_dir, options["sequential_deep_threshold"], self._device, self._clip_model, self._clip_preprocess
            )

            # Step 4c: Global deep deduplication
            logger.info("Running global deep deduplication...")
            removed_deep_global, logs_deep_global = global_deep_dedupe(
                temp_dedup_dir, options["global_deep_threshold"], self._device, self._clip_model, self._clip_preprocess
            )

            # Step 4d: Text-based filtering
            logger.info("Running OCR text filtering...")
            removed_text_ocr, logs_text_ocr = text_ocr_filter_dedupe(
                temp_dedup_dir, options["min_words"], options["ocr_lang"], options["ocr_gpu"]
            )

            final_frame_count = len([f for f in os.listdir(temp_dedup_dir) if f.lower().endswith('.png')])

            # Step 5: Move processed images to final directory
            logger.info(f"Moving processed images to final directory: {final_images_dir}")
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
            logger.info("Generating AI captions...")
            captions = generate_captions_for_directory(
                images_dir=final_images_dir, 
                output_file=captions_file, 
                prompt=options["caption_prompt"]
            )

            # Step 7: Clean up temporary directories
            logger.info("Cleaning up temporary directories...")
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

            logger.info(f"Image extraction completed successfully. Final frames: {final_frame_count}")
            logger.info(f"Images stored in: {final_images_dir}")
            logger.info(f"Captions stored in: {captions_file}")
            
            return results

        except Exception as e:
            logger.error(f"Image extraction failed: {str(e)}")
            results["errors"].append(str(e))
            return results

    async def process_video_for_images(
        self,
        file_path: str,
        output_dir: str = ".",
        video_title: Optional[str] = None,
        url: Optional[str] = None,
        file_id: Optional[str] = None,
        extraction_options: Optional[Dict[str, Any]] = None,
        final_images_dir_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main method to process a video file and generate deduplicated images with captions.
        """
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
                "extract_interval": 8,
                "pixel_threshold": 3,
                "sequential_deep_threshold": 0.8,
                "global_deep_threshold": 0.85,
                "min_words": 5,
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
            logger.error(f"Video processing for images failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path,
                "output_dir": output_dir
            } 