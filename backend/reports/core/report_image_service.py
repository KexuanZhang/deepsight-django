import logging
import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from uuid import UUID

from django.db import transaction
from notebooks.models import KnowledgeBaseImage
from notebooks.utils.minio_backend import get_minio_backend
from reports.models import Report, ReportImage

logger = logging.getLogger(__name__)


class ReportImageService:
    """Service for handling report image operations including copying and managing figures."""
    
    def __init__(self):
        self.minio_backend = get_minio_backend()
    
    def extract_figure_ids_from_content(self, content: str) -> List[str]:
        """
        Extract all figure IDs from report content.
        Looks for UUID patterns that represent figure IDs.
        
        Args:
            content: Report content with figure ID placeholders
            
        Returns:
            List of figure ID strings (UUIDs)
        """
        # UUID pattern: 8-4-4-4-12 hexadecimal characters
        uuid_pattern = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
        
        # Find all UUIDs in the content (these should be figure IDs)
        figure_ids = re.findall(uuid_pattern, content)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_figure_ids = []
        for fig_id in figure_ids:
            if fig_id not in seen:
                seen.add(fig_id)
                unique_figure_ids.append(fig_id)
        
        logger.info(f"Extracted {len(unique_figure_ids)} unique figure IDs from content")
        return unique_figure_ids
    
    def find_images_by_figure_ids(self, figure_ids: List[str], user_id: int) -> List[KnowledgeBaseImage]:
        """
        Find KnowledgeBaseImage records by figure_id field.
        
        Args:
            figure_ids: List of figure ID strings
            user_id: User ID for permission check
            
        Returns:
            List of KnowledgeBaseImage objects
        """
        if not figure_ids:
            return []
        
        # Convert strings to UUIDs
        uuid_figure_ids = []
        for fig_id in figure_ids:
            try:
                uuid_figure_ids.append(UUID(fig_id))
            except ValueError:
                logger.warning(f"Invalid UUID format for figure_id: {fig_id}")
                continue
        
        # Query images by figure_id field and ensure user owns them
        images = KnowledgeBaseImage.objects.filter(
            figure_id__in=uuid_figure_ids,
            knowledge_base_item__user_id=user_id
        ).select_related('knowledge_base_item')
        
        logger.info(f"Found {images.count()} images for {len(figure_ids)} figure IDs")
        return list(images)
    
    def copy_images_to_report(self, report: Report, kb_images: List[KnowledgeBaseImage]) -> List[ReportImage]:
        """
        Copy selected images from knowledge base to report folder and create ReportImage records.
        
        Args:
            report: Report instance
            kb_images: List of KnowledgeBaseImage objects to copy
            
        Returns:
            List of created ReportImage objects
        """
        if not kb_images:
            logger.info("No images to copy")
            return []
        
        report_images = []
        
        # Determine report image folder path in MinIO - same structure as report files
        notebook_part = report.notebooks.id if report.notebooks else 'standalone'
        report_image_folder = f"{report.user.id}/notebook/{notebook_part}/report/{report.id}/images"
        
        with transaction.atomic():
            for kb_image in kb_images:
                try:
                    # Copy image file in MinIO
                    source_key = kb_image.minio_object_key
                    
                    # Generate new object key for report
                    # Use figure_id as filename to maintain consistency
                    file_extension = os.path.splitext(source_key)[1] or '.jpg'
                    dest_key = f"{report_image_folder}/{kb_image.figure_id}{file_extension}"
                    
                    # Copy the object in MinIO
                    success = self.minio_backend.copy_file(source_key, dest_key)
                    
                    if not success:
                        logger.error(f"Failed to copy image {source_key} to {dest_key}")
                        continue
                    
                    # Create ReportImage record
                    report_image = ReportImage.objects.create(
                        figure_id=kb_image.figure_id,
                        report=report,
                        image_caption=kb_image.image_caption,
                        report_figure_minio_object_key=dest_key,
                        image_metadata=kb_image.image_metadata,
                        content_type=kb_image.content_type,
                        file_size=kb_image.file_size
                    )
                    
                    report_images.append(report_image)
                    logger.debug(f"Created ReportImage for figure_id: {kb_image.figure_id}")
                    
                except Exception as e:
                    logger.error(f"Error copying image {kb_image.figure_id}: {e}")
                    continue
        
        logger.info(f"Successfully copied {len(report_images)} images to report {report.id}")
        return report_images
    
    def process_report_images(self, report: Report, content: str) -> Tuple[List[ReportImage], str]:
        """
        Main method to process images for a report.
        Extracts figure IDs from content, copies images, and returns updated content.
        
        Args:
            report: Report instance
            content: Report content with figure ID placeholders
            
        Returns:
            Tuple of (list of ReportImage objects, updated content)
        """
        # Extract figure IDs from content
        figure_ids = self.extract_figure_ids_from_content(content)
        
        if not figure_ids:
            logger.info("No figure IDs found in report content")
            return [], content
        
        # Find corresponding images in knowledge base
        kb_images = self.find_images_by_figure_ids(figure_ids, report.user.id)
        
        if not kb_images:
            logger.warning(f"No images found for figure IDs: {figure_ids}")
            return [], content
        
        # Copy images to report folder and create ReportImage records
        report_images = self.copy_images_to_report(report, kb_images)
        
        # Update content with proper image tags
        updated_content = self.insert_figure_images(content, report_images)
        
        return report_images, updated_content
    
    def insert_figure_images(self, content: str, report_images: List[ReportImage]) -> str:
        """
        Replace figure ID placeholders in content with proper HTML image tags.
        
        Args:
            content: Report content with figure ID placeholders
            report_images: List of ReportImage objects
            
        Returns:
            Updated content with HTML image tags
        """
        if not report_images:
            return content
        
        # Create mapping of figure_id to ReportImage
        figure_map = {str(img.figure_id): img for img in report_images}
        
        # UUID pattern
        uuid_pattern = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
        
        def replace_figure_id(match):
            figure_id = match.group(0) if hasattr(match, 'group') else match
            
            if figure_id in figure_map:
                report_image = figure_map[figure_id]
                # Get MinIO URL for the image from ReportImage (not KnowledgeBaseImage)
                image_url = report_image.get_image_url(expires=86400)  # 24 hour expiry
                
                if image_url:
                    # Create simple HTML img tag without alt text, only with src, data-figure-id and style
                    img_tag = f'<img src="{image_url}" data-figure-id="{figure_id}" style="max-height: 500px;">'
                    return img_tag
                else:
                    logger.warning(f"Could not get URL for figure {figure_id}")
                    return f"[Figure {figure_id} - URL unavailable]"
            else:
                logger.warning(f"Figure {figure_id} not found in report images")
                return match.group(0) if hasattr(match, 'group') else match  # Keep original if not found
        
        # Replace all figure IDs with image tags (both standalone and in angle brackets)
        # First handle angle brackets <uuid>
        bracket_pattern = rf'<({uuid_pattern})>'
        
        def replace_bracket_figure_id(match):
            figure_id = match.group(1)
            return replace_figure_id(figure_id)
        
        updated_content = re.sub(bracket_pattern, replace_bracket_figure_id, content)
        
        # Then handle standalone UUIDs, but avoid replacing UUIDs that are already inside img tags
        # Use negative lookbehind to avoid matching UUIDs inside data-figure-id attributes
        standalone_pattern = rf'(?<!data-figure-id=")({uuid_pattern})(?![^<]*>)'
        
        def replace_standalone_figure_id(match):
            figure_id = match.group(1)
            return replace_figure_id(figure_id)
        
        updated_content = re.sub(standalone_pattern, replace_standalone_figure_id, updated_content)
        
        logger.info(f"Replaced {len(figure_map)} figure placeholders with image tags")
        return updated_content
    
    def cleanup_report_images(self, report: Report):
        """
        Clean up images for a report (used when report is deleted).
        
        Args:
            report: Report instance
        """
        try:
            # Get all report images
            report_images = ReportImage.objects.filter(report=report)
            
            # Delete files from MinIO
            for img in report_images:
                try:
                    self.minio_backend.delete_file(img.report_figure_minio_object_key)
                except Exception as e:
                    logger.error(f"Error deleting image {img.report_figure_minio_object_key}: {e}")
            
            # Delete database records
            count = report_images.count()
            report_images.delete()
            
            logger.info(f"Cleaned up {count} images for report {report.id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up report images: {e}")