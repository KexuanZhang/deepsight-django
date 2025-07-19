"""
AI Caption Service for Report Images

This service handles AI-powered caption generation for ReportImage records
during report generation when include_image=True is specified.
"""

import logging
import os
import tempfile
from typing import List, Optional

from reports.models import Report, ReportImage
from notebooks.utils.image_processing.caption_generator import generate_caption_for_image

logger = logging.getLogger(__name__)


class ReportAICaptionService:
    """Service for generating AI captions for report images during report generation."""
    
    def __init__(self):
        self.service_name = "report_ai_caption_service"
    
    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log service operations with consistent formatting."""
        message = f"[{self.service_name}] {operation}"
        if details:
            message += f": {details}"
        getattr(logger, level)(message)
    
    def enhance_report_image_captions(self, report: Report, api_key: Optional[str] = None) -> int:
        """
        Generate AI captions for ReportImage records with empty captions.
        Only processes images if report.include_image=True.
        
        Args:
            report: Report instance
            api_key: Optional OpenAI API key (uses environment/settings if not provided)
            
        Returns:
            int: Number of images that had captions generated
        """
        # Check if image processing is enabled for this report
        if not report.include_image:
            self.log_operation("enhancement_skipped", 
                f"Image processing disabled for report {report.id}")
            return 0
        
        # Get all ReportImage records for this report that need captions
        report_images = ReportImage.objects.filter(
            report=report,
            image_caption__in=['', None]
        ).order_by('created_at')
        
        if not report_images.exists():
            self.log_operation("no_images_need_captions", 
                f"No images need captions for report {report.id}")
            return 0
        
        self.log_operation("enhancement_start", 
            f"Generating AI captions for {report_images.count()} images in report {report.id}")
        
        enhanced_count = 0
        
        for report_image in report_images:
            try:
                # Generate AI caption for this image
                caption = self._generate_ai_caption_for_report_image(report_image, api_key)
                
                if caption and not caption.startswith("Caption generation failed"):
                    # Update the ReportImage with the generated caption
                    report_image.image_caption = caption
                    report_image.save(update_fields=['image_caption', 'updated_at'])
                    
                    enhanced_count += 1
                    self.log_operation("caption_generated", 
                        f"Generated AI caption for image {report_image.id}: {caption[:50]}...")
                else:
                    self.log_operation("caption_generation_failed", 
                        f"Failed to generate caption for image {report_image.id}", "warning")
                
            except Exception as e:
                self.log_operation("caption_error", 
                    f"Error processing image {report_image.id}: {e}", "error")
        
        self.log_operation("enhancement_complete", 
            f"Generated AI captions for {enhanced_count}/{report_images.count()} images in report {report.id}")
        
        return enhanced_count
    
    def _generate_ai_caption_for_report_image(self, report_image: ReportImage, api_key: Optional[str] = None) -> Optional[str]:
        """
        Generate AI caption for a single ReportImage.
        
        Args:
            report_image: ReportImage instance
            api_key: Optional OpenAI API key
            
        Returns:
            str: Generated caption or None if failed
        """
        try:
            # Download image from MinIO to a temporary file
            temp_image_path = self._download_report_image_to_temp(report_image)
            
            if not temp_image_path:
                self.log_operation("download_failed", 
                    f"Could not download image {report_image.id} from MinIO for AI captioning", "error")
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
            self.log_operation("ai_generation_error", 
                f"Error generating AI caption for report image {report_image.id}: {e}", "error")
            return None
    
    def _download_report_image_to_temp(self, report_image: ReportImage) -> Optional[str]:
        """
        Download ReportImage from MinIO to a temporary file for AI processing.
        
        Args:
            report_image: ReportImage instance
            
        Returns:
            str: Path to temporary file or None if failed
        """
        try:
            # Get image content from MinIO
            image_content = report_image.get_image_content()
            
            if not image_content:
                return None
            
            # Determine file extension from content type or object key
            file_extension = '.png'  # default
            if report_image.content_type:
                if 'jpeg' in report_image.content_type or 'jpg' in report_image.content_type:
                    file_extension = '.jpg'
                elif 'png' in report_image.content_type:
                    file_extension = '.png'
                elif 'gif' in report_image.content_type:
                    file_extension = '.gif'
                elif 'webp' in report_image.content_type:
                    file_extension = '.webp'
            elif report_image.report_figure_minio_object_key:
                # Try to get extension from object key
                object_key_lower = report_image.report_figure_minio_object_key.lower()
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
                delete=False,
                prefix=f"report_image_{report_image.id}_"
            ) as temp_file:
                temp_file.write(image_content)
                temp_file_path = temp_file.name
            
            return temp_file_path
            
        except Exception as e:
            self.log_operation("download_temp_error", 
                f"Error downloading report image {report_image.id} to temp file: {e}", "error")
            return None
    
    def get_images_needing_captions(self, report: Report) -> List[ReportImage]:
        """
        Get list of ReportImage records that need AI captions.
        
        Args:
            report: Report instance
            
        Returns:
            List of ReportImage objects with empty captions
        """
        if not report.include_image:
            return []
            
        return list(ReportImage.objects.filter(
            report=report,
            image_caption__in=['', None]
        ).order_by('created_at'))