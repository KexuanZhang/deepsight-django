"""
KnowledgeBase Image Service for managing images stored in the database.
Replaces the figure_data.json file-based approach with database storage.
"""

import json
import logging
import os
import tempfile
from typing import Dict, List, Optional, Any
from django.db import transaction

from ..utils.storage import get_minio_backend


class KnowledgeBaseImageService:
    """Service for managing knowledge base images stored in database instead of figure_data.json files."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.knowledge_base_image_service")
        self.minio_backend = get_minio_backend()
    
    def get_images_for_knowledge_base_item(self, kb_item_id: int, user_id: int = None) -> List[Dict[str, Any]]:
        """
        Get all images for a knowledge base item.
        
        Args:
            kb_item_id: Knowledge base item ID
            user_id: User ID for additional security check (optional)
            
        Returns:
            List of image dictionaries in figure_data.json compatible format
        """
        try:
            from ..models import KnowledgeBaseItem, KnowledgeBaseImage
            
            # Validate access to knowledge base item
            kb_item_query = KnowledgeBaseItem.objects.filter(id=kb_item_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                kb_item_query = kb_item_query.filter(notebook__user=user_id)
            
            kb_item = kb_item_query.first()
            if not kb_item:
                self.logger.warning(f"Knowledge base item {kb_item_id} not found or access denied")
                return []
            
            # Get all images for this knowledge base item
            images = KnowledgeBaseImage.objects.filter(
                knowledge_base_item=kb_item
            ).order_by('id')
            
            # Convert to figure_data.json compatible format
            figure_data = [image.to_figure_data_dict() for image in images]
            
            self.logger.info(f"Retrieved {len(figure_data)} images for knowledge base item {kb_item_id}")
            return figure_data
            
        except Exception as e:
            self.logger.error(f"Error retrieving images for kb_item {kb_item_id}: {e}")
            return []
    
    def get_combined_figure_data_for_files(self, file_ids: List[str], user_id: int = None) -> List[Dict[str, Any]]:
        """
        Get combined figure data for multiple knowledge base items.
        This replaces the functionality of creating combined figure_data.json files.
        
        Args:
            file_ids: List of knowledge base item IDs
            user_id: User ID for security checks
            
        Returns:
            Combined list of figure data dictionaries with renumbered figures
        """
        combined_figure_data = []
        
        try:
            for file_id in file_ids:
                # Remove 'f_' prefix if present
                clean_file_id = file_id.replace('f_', '') if file_id.startswith('f_') else file_id
                
                # Get images for this file
                file_images = self.get_images_for_knowledge_base_item(clean_file_id, user_id)
                combined_figure_data.extend(file_images)
            
            # No need to renumber figures since we're using UUIDs
                
            self.logger.info(f"Combined figure data from {len(file_ids)} files: {len(combined_figure_data)} total images")
            return combined_figure_data
            
        except Exception as e:
            self.logger.error(f"Error creating combined figure data: {e}")
            return []
    
    def update_image_caption(self, figure_id: str, caption: str, user_id: int = None) -> bool:
        """
        Update the caption for a specific image.
        
        Args:
            figure_id: KnowledgeBaseImage figure_id
            caption: New caption text
            user_id: User ID for security check
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from ..models import KnowledgeBaseImage
            
            image_query = KnowledgeBaseImage.objects.filter(figure_id=figure_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                image_query = image_query.filter(knowledge_base_item__notebook__user=user_id)
            
            image = image_query.first()
            if not image:
                self.logger.warning(f"Image {figure_id} not found or access denied")
                return False
            
            image.image_caption = caption
            image.save(update_fields=['image_caption', 'updated_at'])
            
            self.logger.info(f"Updated caption for image {figure_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating caption for image {figure_id}: {e}")
            return False
    
    def update_images_from_figure_data(self, kb_item_id: int, figure_data: List[Dict[str, Any]], user_id: int = None) -> bool:
        """
        Update image captions and metadata from figure_data format.
        This helps migrate or update data from existing figure_data.json files.
        
        Args:
            kb_item_id: Knowledge base item ID
            figure_data: List of figure data dictionaries
            user_id: User ID for security check
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from ..models import KnowledgeBaseItem, KnowledgeBaseImage
            
            # Validate access to knowledge base item
            kb_item_query = KnowledgeBaseItem.objects.filter(id=kb_item_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                kb_item_query = kb_item_query.filter(notebook__user=user_id)
            
            kb_item = kb_item_query.first()
            if not kb_item:
                self.logger.warning(f"Knowledge base item {kb_item_id} not found or access denied")
                return False
            
            updated_count = 0
            
            with transaction.atomic():
                for figure in figure_data:
                    # Try to match by image file name
                    image_file = figure.get('image_file', '')
                    caption = figure.get('caption', '')
                    
                    if not image_file and 'image_path' in figure:
                        image_file = os.path.basename(figure['image_path'])
                    
                    # Find matching image in database
                    matching_image = None
                    if image_file:
                        # Try to match by filename in object key
                        matching_image = KnowledgeBaseImage.objects.filter(
                            knowledge_base_item=kb_item,
                            minio_object_key__icontains=image_file
                        ).first()
                    
                    if matching_image:
                        # Update existing image
                        matching_image.image_caption = caption
                        
                        # Update metadata
                        matching_image.image_metadata.update({
                            'updated_from_figure_data': True,
                            'original_figure_data': figure
                        })
                        
                        matching_image.save()
                        updated_count += 1
                        
                        self.logger.debug(f"Updated image {matching_image.id} with caption from figure_data")
            
            self.logger.info(f"Updated {updated_count} images from figure_data for kb_item {kb_item_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating images from figure_data for kb_item {kb_item_id}: {e}")
            return False
    
    def migrate_figure_data_json_to_database(self, kb_item_id: int, figure_data_path: str, user_id: int = None) -> bool:
        """
        Migrate from figure_data.json file to database records.
        This method helps transition from the old file-based system.
        
        Args:
            kb_item_id: Knowledge base item ID
            figure_data_path: Path to existing figure_data.json file
            user_id: User ID for security check
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(figure_data_path):
                self.logger.info(f"Figure data file doesn't exist: {figure_data_path}")
                return False
            
            # Load figure data from JSON file
            with open(figure_data_path, 'r', encoding='utf-8') as f:
                figure_data = json.load(f)
            
            if not figure_data:
                self.logger.info(f"No figure data found in {figure_data_path}")
                return False
            
            # Update images using the figure data
            success = self.update_images_from_figure_data(kb_item_id, figure_data, user_id)
            
            if success:
                self.logger.info(f"Successfully migrated figure_data.json to database for kb_item {kb_item_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error migrating figure_data.json to database: {e}")
            return False
    
    def delete_image(self, figure_id: str, user_id: int = None, delete_from_minio: bool = True) -> bool:
        """
        Delete an image record and optionally its file from MinIO.
        
        Args:
            figure_id: KnowledgeBaseImage figure_id
            user_id: User ID for security check
            delete_from_minio: Whether to also delete the file from MinIO
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from ..models import KnowledgeBaseImage
            
            image_query = KnowledgeBaseImage.objects.filter(figure_id=figure_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                image_query = image_query.filter(knowledge_base_item__notebook__user=user_id)
            
            image = image_query.first()
            if not image:
                self.logger.warning(f"Image {figure_id} not found or access denied")
                return False
            
            object_key = image.minio_object_key
            
            # Delete from database
            image.delete()
            
            # Delete from MinIO if requested
            if delete_from_minio and object_key:
                try:
                    self.minio_backend.delete_file(object_key)
                    self.logger.info(f"Deleted image file from MinIO: {object_key}")
                except Exception as e:
                    self.logger.warning(f"Failed to delete image file from MinIO {object_key}: {e}")
            
            self.logger.info(f"Deleted image record {figure_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting image {figure_id}: {e}")
            return False
    
    
    def get_image_url(self, figure_id: str, user_id: int = None, expires: int = 3600) -> Optional[str]:
        """
        Get pre-signed URL for image access.
        
        Args:
            figure_id: KnowledgeBaseImage figure_id
            user_id: User ID for security check
            expires: URL expiration time in seconds
            
        Returns:
            Pre-signed URL or None if not found
        """
        try:
            from ..models import KnowledgeBaseImage
            
            image_query = KnowledgeBaseImage.objects.filter(figure_id=figure_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                image_query = image_query.filter(knowledge_base_item__notebook__user=user_id)
            
            image = image_query.first()
            if not image:
                return None
            
            return image.get_image_url(expires)
            
        except Exception as e:
            self.logger.error(f"Error getting image URL for {figure_id}: {e}")
            return None
    
    def get_stats_for_knowledge_base_item(self, kb_item_id: int, user_id: int = None) -> Dict[str, Any]:
        """
        Get statistics about images for a knowledge base item.
        
        Args:
            kb_item_id: Knowledge base item ID
            user_id: User ID for security check
            
        Returns:
            Dictionary with image statistics
        """
        try:
            from ..models import KnowledgeBaseItem, KnowledgeBaseImage
            
            # Validate access to knowledge base item
            kb_item_query = KnowledgeBaseItem.objects.filter(id=kb_item_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                kb_item_query = kb_item_query.filter(notebook__user=user_id)
            
            kb_item = kb_item_query.first()
            if not kb_item:
                return {}
            
            images = KnowledgeBaseImage.objects.filter(knowledge_base_item=kb_item)
            
            stats = {
                'total_images': images.count(),
                'images_with_captions': images.exclude(image_caption='').count(),
                'total_file_size': sum(img.file_size for img in images),
                'content_types': list(images.values_list('content_type', flat=True).distinct()),
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting stats for kb_item {kb_item_id}: {e}")
            return {}
    
    def auto_populate_captions_from_content(self, kb_item_id: int, user_id: int = None) -> bool:
        """
        Automatically populate image captions by extracting figure data from the knowledge base item's content.
        This method uses the extract_figure_data function from paper_processing.py.
        
        Args:
            kb_item_id: Knowledge base item ID
            user_id: User ID for security check
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from ..models import KnowledgeBaseItem, KnowledgeBaseImage
            from reports.image_utils import extract_figure_data_from_markdown
            
            # Validate access to knowledge base item
            kb_item_query = KnowledgeBaseItem.objects.filter(id=kb_item_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                kb_item_query = kb_item_query.filter(notebook__user=user_id)
            
            kb_item = kb_item_query.first()
            if not kb_item:
                self.logger.warning(f"Knowledge base item {kb_item_id} not found or access denied")
                return False
            
            # Get markdown content from the knowledge base item
            markdown_content = self._get_markdown_content(kb_item)
            if not markdown_content:
                self.logger.info(f"No markdown content found for KB item {kb_item_id}")
                return False
            
            # Extract figure data from markdown content
            figure_data = self._extract_figure_data_from_content(markdown_content)
            if not figure_data:
                self.logger.info(f"No figure data extracted from KB item {kb_item_id}")
                return False
            
            # Update images with extracted captions
            success = self.update_images_from_figure_data(kb_item_id, figure_data, user_id)
            
            if success:
                self.logger.info(f"Auto-populated captions for KB item {kb_item_id} from content")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error auto-populating captions for KB item {kb_item_id}: {e}")
            return False
    
    def _get_markdown_content(self, kb_item):
        """Get markdown content from knowledge base item using model manager."""
        try:
            from ..models import KnowledgeBaseItem
            
            # Use the model manager to get content
            content = KnowledgeBaseItem.objects.get_content(str(kb_item.id), kb_item.notebook.user.pk)
            return content
            
        except Exception as e:
            self.logger.error(f"Error getting markdown content for KB item {kb_item.id}: {e}")
            return None

    def _extract_figure_data_from_content(self, content):
        """Extract figure data from markdown content using a temporary file."""
        try:
            # Import here to avoid circular imports
            from reports.image_utils import extract_figure_data_from_markdown
            
            # Create a temporary markdown file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Extract figure data using the paper processing function
                figure_data = extract_figure_data_from_markdown(temp_file_path)
                return figure_data or []
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            self.logger.error(f"Error extracting figure data from content: {e}")
            return [] 