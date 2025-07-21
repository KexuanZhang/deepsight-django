import logging
import os
from typing import List, Tuple

from django.db import transaction
from notebooks.models import KnowledgeBaseImage
from notebooks.utils.storage import get_minio_backend
from reports.models import Report, ReportImage
from reports.image_utils import (
    extract_figure_ids_from_content, 
    convert_to_uuid_objects,
    ImageInsertionService, 
    DatabaseUrlProvider
)

logger = logging.getLogger(__name__)


class ReportImageService:
    """Service for handling report image operations including copying and managing figures."""
    
    def __init__(self):
        self.minio_backend = get_minio_backend()
    
    
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
        
        # Convert strings to UUIDs using common utility
        uuid_figure_ids = convert_to_uuid_objects(figure_ids)
        
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
                    
                    # Create ReportImage record using get_or_create to respect unique constraint
                    report_image, created = ReportImage.objects.get_or_create(
                        figure_id=kb_image.figure_id,
                        report=report,
                        defaults={
                            'image_caption': kb_image.image_caption,
                            'report_figure_minio_object_key': dest_key,
                            'image_metadata': kb_image.image_metadata,
                            'content_type': kb_image.content_type,
                            'file_size': kb_image.file_size
                        }
                    )
                    
                    report_images.append(report_image)
                    logger.debug(f"{'Created' if created else 'Found existing'} ReportImage for figure_id: {kb_image.figure_id}")
                    
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
        figure_ids = extract_figure_ids_from_content(content)
        
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
        updated_content = self._insert_figure_images(content, report_images, report.id)
        
        return report_images, updated_content
    
    def _insert_figure_images(self, content: str, report_images: List[ReportImage], report_id=None) -> str:
        """
        Replace figure ID placeholders in content with proper HTML image tags.
        
        Args:
            content: Report content with figure ID placeholders
            report_images: List of ReportImage objects
            report_id: Optional report ID to use for image lookup
            
        Returns:
            Updated content with HTML image tags
        """
        if not report_images:
            return content
        
        # Convert ReportImage objects to standard format for unified service
        figures = [
            {
                "figure_id": str(img.figure_id),
                "caption": img.image_caption or f"Figure {img.figure_id}"
            }
            for img in report_images
        ]
        
        # Use unified service
        service = ImageInsertionService(DatabaseUrlProvider())
        
        # Django adapts: use passed report_id or get from first image
        if report_id is None:
            report_id = str(report_images[0].report_id) if report_images else None
        else:
            report_id = str(report_id)
        return service.insert_figure_images(content, figures, report_id=report_id)
    
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