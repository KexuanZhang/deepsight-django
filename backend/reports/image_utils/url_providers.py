"""
URL providers for getting image URLs from different sources.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class ImageUrlProvider(ABC):
    """Abstract base class for image URL providers."""
    
    @abstractmethod
    def get_image_url(self, figure_id: str, **kwargs) -> Optional[str]:
        """
        Get image URL for a given figure ID.
        
        Args:
            figure_id: The figure ID to get URL for
            **kwargs: Additional context (report_id, etc.)
            
        Returns:
            Image URL or None if not found
        """
        pass


class DatabaseUrlProvider(ImageUrlProvider):
    """
    Universal URL provider that gets image URLs from ReportImage database table.
    Used by all contexts (Django, agents, etc.) - single source of truth.
    """
    
    def get_image_url(self, figure_id: str, report_id: str = None, **kwargs) -> Optional[str]:
        """
        Get the MinIO URL for an image from the database using figure_id and report_id.
        
        Args:
            figure_id: The figure_id of the ReportImage
            report_id: The report_id to uniquely identify the image
            
        Returns:
            The MinIO URL for the image, or None if not found
        """
        try:
            # Import here to avoid circular imports and handle optional Django
            import django
            import os
            from django.conf import settings as django_settings
            
            # Initialize Django if not already done
            if not django_settings.configured:
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
                django.setup()
            
            from reports.models import ReportImage
            
            try:
                image = ReportImage.objects.get(figure_id=figure_id, report_id=report_id)
                url = image.get_image_url()
                logger.info(f"Successfully retrieved image URL for figure_id {figure_id} and report_id {report_id}")
                return url
            except ReportImage.DoesNotExist:
                logger.warning(f"Image with figure_id {figure_id} and report_id {report_id} not found in ReportImage database")
                return None
            except ValueError as ve:
                logger.warning(f"Invalid figure_id format {figure_id}: {ve}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting image URL for figure_id {figure_id} and report_id {report_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None