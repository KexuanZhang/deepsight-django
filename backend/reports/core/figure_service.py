import json
import os
import glob
from pathlib import Path
from typing import List, Dict, Optional
from django.conf import settings
from datetime import datetime
import logging

# Import extract_figure_data_from_markdown from image_utils
from reports.image_utils import extract_figure_data_from_markdown

logger = logging.getLogger(__name__)


class FigureDataService:
    """Service for managing figure data using database storage instead of JSON files."""
    
    @staticmethod
    def create_knowledge_base_figure_data(user_id: int, file_id: str, figure_data: List[Dict]) -> Optional[str]:
        """
        Store figure data in database for a knowledge base item.
        This replaces the old figure_data.json file approach.
        
        Args:
            user_id: User ID
            file_id: Knowledge base file ID (without f_ prefix)
            figure_data: List of figure dictionaries
            
        Returns:
            str: Success message or None if failed
        """
        try:
            from notebooks.services.knowledge_base_image_service import KnowledgeBaseImageService
            
            image_service = KnowledgeBaseImageService()
            
            # Update images from figure data
            success = image_service.update_images_from_figure_data(
                kb_item_id=int(file_id),
                figure_data=figure_data,
                user_id=user_id
            )
            
            if success:
                logger.info(f"Stored figure data in database for kb_item {file_id}")
                return f"database_storage_kb_{file_id}"  # Return a success indicator
            else:
                logger.warning(f"Failed to store figure data in database for kb_item {file_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error storing figure data in database for kb_item {file_id}: {e}")
            return None
    
    @staticmethod
    def create_combined_figure_data(report, selected_file_ids: List[str]) -> Optional[str]:
        """
        Get combined figure data from database for a report.
        This replaces creating combined figure_data.json files.
        
        Args:
            report: Report instance
            selected_file_ids: List of knowledge base file IDs (with f_ prefix)
            
        Returns:
            str: Success indicator or None if no figure data found
        """
        try:
            from notebooks.services.knowledge_base_image_service import KnowledgeBaseImageService
            
            image_service = KnowledgeBaseImageService()
            
            # Get combined figure data from database
            combined_figure_data = image_service.get_combined_figure_data_for_files(
                file_ids=selected_file_ids,
                user_id=report.user.pk
            )
            
            if not combined_figure_data:
                logger.info("No figure data found in database for selected files")
                return None
            
            # Generate AI captions for empty captions before passing to report agent
            if report.include_image:
                combined_figure_data = FigureDataService._enhance_figure_data_with_ai_captions(
                    combined_figure_data, report.user.pk
                )
            
            # Store the figure data directly in the report instance for immediate use
            # This avoids the need to create temporary files
            report._cached_figure_data = combined_figure_data
            
            logger.info(f"Retrieved combined figure data from database: {len(combined_figure_data)} figures")
            return f"database_combined_{report.id}"  # Return success indicator
            
        except Exception as e:
            logger.error(f"Error creating combined figure data from database: {e}")
            return None
    
    @staticmethod
    def load_combined_figure_data(figure_data_reference: str) -> List[Dict]:
        """
        Load figure data from KnowledgeBaseImage table using database references.
        No longer uses JSON files - everything comes from database.
        """
        if not figure_data_reference:
            return []
            
        try:
            # Check if this is a database reference
            if figure_data_reference.startswith('database_'):
                # Extract identifiers from the reference
                if 'combined_' in figure_data_reference:
                    # This is a combined figure data request for a report
                    report_id = figure_data_reference.split('_')[-1]
                    
                    # Try to get from cached data first
                    from reports.models import Report
                    try:
                        report = Report.objects.get(id=report_id)
                        if hasattr(report, '_cached_figure_data'):
                            return report._cached_figure_data
                    except Exception:
                        pass
                    
                    # If no cached data, return empty list
                    logger.warning(f"No cached figure data found for report {report_id}")
                    return []
                    
                elif 'kb_' in figure_data_reference:
                    # This is a single knowledge base item request
                    kb_item_id = figure_data_reference.split('_')[-1]
                    return FigureDataService._load_kb_item_figure_data(int(kb_item_id))
                
            # Direct knowledge base item ID (new approach)
            elif figure_data_reference.isdigit():
                kb_item_id = int(figure_data_reference)
                return FigureDataService._load_kb_item_figure_data(kb_item_id)
                
        except Exception as e:
            logger.error(f"Error loading figure data from reference {figure_data_reference}: {e}")
            
        return []
    
    @staticmethod
    def _load_kb_item_figure_data(kb_item_id: int) -> List[Dict]:
        """Load figure data directly from KnowledgeBaseImage table"""
        try:
            from notebooks.models import KnowledgeBaseImage
            
            # Get all images for this knowledge base item
            images = KnowledgeBaseImage.objects.filter(
                knowledge_base_item_id=kb_item_id
            ).order_by('created_at')
            
            figure_data = []
            for image in images:
                # Use to_figure_data_dict method for consistency
                figure_dict = image.to_figure_data_dict()
                # Add additional metadata for backwards compatibility if needed
                figure_dict.update({
                    'content_type': image.content_type,
                    'file_size': image.file_size,
                    'minio_object_key': image.minio_object_key,
                    'kb_item_id': kb_item_id,
                    # Remove original_figure_name as field no longer exists
                })
                figure_data.append(figure_dict)
                
            logger.info(f"Loaded {len(figure_data)} figures for KB item {kb_item_id}")
            return figure_data
            
        except Exception as e:
            logger.error(f"Error loading figure data for KB item {kb_item_id}: {e}")
            return []
    
    @staticmethod
    def get_figure_data_for_knowledge_base_item(user_id: int, file_id: str) -> List[Dict]:
        """
        Get figure data for a single knowledge base item from database.
        This is a new method that directly queries the database.
        
        Args:
            user_id: User ID
            file_id: Knowledge base file ID (without f_ prefix)
            
        Returns:
            List of figure data dictionaries
        """
        try:
            from notebooks.services.knowledge_base_image_service import KnowledgeBaseImageService
            
            image_service = KnowledgeBaseImageService()
            
            return image_service.get_images_for_knowledge_base_item(
                kb_item_id=int(file_id),
                user_id=user_id
            )
            
        except Exception as e:
            logger.error(f"Error getting figure data for kb_item {file_id}: {e}")
            return []
    
    @staticmethod
    def get_cached_figure_data(user_id: int, cache_key: str) -> Optional[Dict]:
        """
        Get cached figure data using user_id and cache_key.
        This retrieves figure data from the database for prepare_report_images.
        
        Args:
            user_id: User ID
            cache_key: Cache key (direct_{report_id} or notebook_id)
            
        Returns:
            Dict with figures list or None if not found
        """
        try:
            logger.info(f"get_cached_figure_data called with user_id={user_id}, cache_key={cache_key}")
            
            # Extract relevant information from cache_key
            if cache_key.startswith("direct_"):
                # This is for direct report processing - try to get from report configuration
                report_id = cache_key.replace("direct_", "")
                try:
                    from reports.models import Report
                    report = Report.objects.get(id=report_id)
                    if hasattr(report, '_cached_figure_data'):
                        figures = report._cached_figure_data
                        logger.info(f"Found {len(figures)} cached figures for report {report_id}")
                        return {"figures": figures}
                except Exception:
                    pass
            
            # For notebook-based cache keys or if direct lookup failed
            # This is a fallback - the prepare step is optional anyway
            logger.info(f"No cached figure data found for cache_key={cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"Error in get_cached_figure_data: {e}")
            return None
    
    @staticmethod
    def _enhance_figure_data_with_ai_captions(figure_data: List[Dict], user_id: int) -> List[Dict]:
        """
        Enhance figure data by generating AI captions for images with empty captions.
        This ensures the report agent sees filled captions instead of empty ones.
        
        Args:
            figure_data: List of figure data dictionaries
            user_id: User ID for accessing images
            
        Returns:
            Enhanced figure data with AI-generated captions
        """
        try:
            enhanced_figure_data = []
            enhanced_count = 0
            
            for figure in figure_data:
                figure_id = figure.get('figure_id')
                caption = figure.get('caption', '')
                
                # If caption is empty, generate AI caption
                if not caption.strip() and figure_id:
                    try:
                        # Get the KnowledgeBaseImage to access the actual image
                        from notebooks.models import KnowledgeBaseImage
                        kb_image = KnowledgeBaseImage.objects.filter(
                            figure_id=figure_id,
                            knowledge_base_item__user_id=user_id
                        ).first()
                        
                        if kb_image:
                            # Generate AI caption using the same service
                            from notebooks.utils.image_processing.caption_generator import generate_caption_for_image
                            
                            # Download image temporarily for AI processing
                            temp_image_path = FigureDataService._download_kb_image_to_temp(kb_image)
                            
                            if temp_image_path:
                                try:
                                    ai_caption = generate_caption_for_image(temp_image_path)
                                    
                                    if ai_caption and not ai_caption.startswith("Caption generation failed"):
                                        # Update both the figure data and the database
                                        figure['caption'] = ai_caption
                                        kb_image.image_caption = ai_caption
                                        kb_image.save(update_fields=['image_caption', 'updated_at'])
                                        enhanced_count += 1
                                        
                                        logger.info(f"Generated AI caption for figure {figure_id}: {ai_caption[:50]}...")
                                    else:
                                        logger.warning(f"Failed to generate AI caption for figure {figure_id}")
                                
                                finally:
                                    # Clean up temp file
                                    import os
                                    if os.path.exists(temp_image_path):
                                        os.unlink(temp_image_path)
                        
                    except Exception as e:
                        logger.error(f"Error generating AI caption for figure {figure_id}: {e}")
                
                enhanced_figure_data.append(figure)
            
            if enhanced_count > 0:
                logger.info(f"Enhanced {enhanced_count} figures with AI-generated captions")
            
            return enhanced_figure_data
            
        except Exception as e:
            logger.error(f"Error enhancing figure data with AI captions: {e}")
            return figure_data  # Return original data if enhancement fails
    
    @staticmethod
    def _download_kb_image_to_temp(kb_image) -> Optional[str]:
        """
        Download KnowledgeBaseImage from MinIO to a temporary file for AI processing.
        
        Args:
            kb_image: KnowledgeBaseImage instance
            
        Returns:
            str: Path to temporary file or None if failed
        """
        try:
            import tempfile
            import os
            
            # Get image content from MinIO
            image_content = kb_image.get_image_content()
            
            if not image_content:
                return None
            
            # Determine file extension from content type or object key
            file_extension = '.png'  # default
            if kb_image.content_type:
                if 'jpeg' in kb_image.content_type or 'jpg' in kb_image.content_type:
                    file_extension = '.jpg'
                elif 'png' in kb_image.content_type:
                    file_extension = '.png'
                elif 'gif' in kb_image.content_type:
                    file_extension = '.gif'
                elif 'webp' in kb_image.content_type:
                    file_extension = '.webp'
            elif kb_image.minio_object_key:
                # Try to get extension from object key
                object_key_lower = kb_image.minio_object_key.lower()
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
                prefix=f"kb_image_{kb_image.id}_"
            ) as temp_file:
                temp_file.write(image_content)
                temp_file_path = temp_file.name
            
            return temp_file_path
            
        except Exception as e:
            logger.error(f"Error downloading KB image {kb_image.id} to temp file: {e}")
            return None
    
    @staticmethod
    def migrate_existing_figure_data_to_database(user_id: int, file_id: str) -> bool:
        """
        DEPRECATED: No longer needed as we use KnowledgeBaseImage table directly.
        This method is kept for compatibility but always returns True.
        """
        logger.info(f"Migration not needed - using KnowledgeBaseImage table directly for file {file_id}")
        return True
    
    @staticmethod
    def _create_figure_data_from_images_in_database(user_id: int, file_id: str) -> bool:
        """
        Create figure data in database by extracting from markdown content.
        This replaces the old _create_figure_data_from_images method.
        """
        try:
            # Get the content folder path
            content_folder_path = FigureDataService._get_knowledge_base_content_path(user_id, file_id)
            
            if not content_folder_path or not os.path.exists(content_folder_path):
                logger.info(f"Content folder doesn't exist for kb_item {file_id}")
                return False
            
            # Find markdown file in content folder
            md_files = glob.glob(os.path.join(content_folder_path, "*.md"))
            if not md_files:
                logger.info(f"No markdown files found in content folder for kb_item {file_id}")
                return False
            
            # Use the first markdown file found
            md_file_path = md_files[0]
            logger.info(f"Extracting figure data from {md_file_path}")
            
            # Extract figure data using image_utils function
            figure_data = extract_figure_data_from_markdown(md_file_path)
            
            if figure_data:
                from notebooks.services.knowledge_base_image_service import KnowledgeBaseImageService
                
                image_service = KnowledgeBaseImageService()
                success = image_service.update_images_from_figure_data(
                    kb_item_id=int(file_id),
                    figure_data=figure_data,
                    user_id=user_id
                )
                
                if success:
                    logger.info(f"Created figure data in database from markdown for kb_item {file_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error creating figure data from images for kb_item {file_id}: {e}")
            return False
    
    @staticmethod
    def _get_knowledge_base_images_path(user_id: int, file_id: str) -> str:
        """
        Generate absolute path to knowledge base item images folder.
        Uses the actual creation date of the KnowledgeBaseItem with fallback logic.
        """
        try:
            # Import here to avoid circular imports
            from notebooks.models import KnowledgeBaseItem
            
            # Get the knowledge base item to find its actual creation date
            kb_item = KnowledgeBaseItem.objects.filter(id=file_id, user=user_id).first()
            
            if kb_item:
                # Use the actual creation date
                creation_date = kb_item.created_at
                year_month = creation_date.strftime("%Y-%m")
                
                data_root = getattr(settings, 'DEEPSIGHT_DATA_ROOT', '/tmp/deepsight_data')
                images_path = os.path.join(
                    data_root,
                    f"Users/u_{user_id}/knowledge_base_item/{year_month}/f_{file_id}/images"
                )
                
                # Check if the path exists
                if os.path.exists(images_path):
                    return images_path
                else:
                    logger.info(f"Images path doesn't exist at {images_path}, trying fallback")
            
            # With MinIO storage, we can't use local file paths for images
            logger.info(f"Using MinIO storage - cannot resolve local image paths for file {file_id}")
            return None
            
            # With MinIO storage, we can't use local file paths for images
            logger.warning(f"Using MinIO storage - cannot resolve local image paths for file {file_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error in _get_knowledge_base_images_path: {e}")
            # With MinIO storage, we can't use local file paths for images
            logger.warning(f"Using MinIO storage - cannot resolve local image paths for file {file_id}")
            return None
    
    @staticmethod
    def _get_report_figure_data_path(report) -> str:
        """DEPRECATED: No longer creates JSON files. Always returns None."""
        logger.info(f"Using KnowledgeBaseImage table directly - no figure data path needed for report {report.id}")
        return None
        
        user_id = report.user.pk
        current_date = datetime.now()
        year_month = current_date.strftime("%Y-%m")
        report_id = report.pk
        
        notebook_id = None
        if hasattr(report, 'notebooks') and report.notebooks:
            notebook_id = report.notebooks.pk
        # This method is disabled for MinIO storage
        return None
    
    @staticmethod
    def _load_knowledge_base_figure_data(user_id: int, file_id: str) -> List[Dict]:
        """DEPRECATED: Use _load_kb_item_figure_data instead."""
        logger.info(f"Using KnowledgeBaseImage table directly for file {file_id}")
        return FigureDataService._load_kb_item_figure_data(int(file_id))
    
    @staticmethod
    def _validate_and_clean_figure_data(figure_data: List[Dict]) -> List[Dict]:
        """Validate figure data and ensure all image paths are absolute."""
        cleaned_data = []
        
        for i, figure in enumerate(figure_data):
            # Validate required fields
            required_fields = ['image_path', 'caption']
            if not all(field in figure for field in required_fields):
                logger.warning(f"Figure {i} missing required fields: {required_fields}, skipping")
                continue
            
            # Ensure image path is absolute
            image_path = figure['image_path']
            if not os.path.isabs(image_path):
                # Convert relative path to absolute using DEEPSIGHT_DATA_ROOT
                data_root = getattr(settings, 'DEEPSIGHT_DATA_ROOT', '/tmp/deepsight_data')
                image_path = os.path.join(data_root, image_path)
            
            cleaned_figure = {
                'image_path': image_path,
                'caption': figure['caption']
            }
            cleaned_data.append(cleaned_figure)
        
        return cleaned_data
    
    @staticmethod
    def _create_figure_data_from_images(user_id: int, file_id: str) -> List[Dict]:
        """
        DEPRECATED: No longer creates JSON files. Use KnowledgeBaseImage table directly.
        """
        logger.info(f"Using KnowledgeBaseImage table directly for file {file_id} - no JSON creation needed")
        return FigureDataService._load_kb_item_figure_data(int(file_id))
    
    @staticmethod
    def _get_knowledge_base_content_path(user_id: int, file_id: str) -> str:
        """
        Generate absolute path to knowledge base item content folder.
        Uses the actual creation date of the KnowledgeBaseItem with fallback logic.
        """
        try:
            # Import here to avoid circular imports
            from notebooks.models import KnowledgeBaseItem
            
            # Get the knowledge base item to find its actual creation date
            kb_item = KnowledgeBaseItem.objects.filter(id=file_id, user=user_id).first()
            
            if kb_item:
                # Use the actual creation date
                creation_date = kb_item.created_at
                year_month = creation_date.strftime("%Y-%m")
                
                data_root = getattr(settings, 'DEEPSIGHT_DATA_ROOT', '/tmp/deepsight_data')
                content_path = os.path.join(
                    data_root,
                    f"Users/u_{user_id}/knowledge_base_item/{year_month}/f_{file_id}/content"
                )
                
                # Check if the path exists
                if os.path.exists(content_path):
                    return content_path
                else:
                    logger.info(f"Content path doesn't exist at {content_path}, trying fallback")
            
            # With MinIO storage, we can't use local file paths for content
            logger.info(f"Using MinIO storage - cannot resolve local content paths for file {file_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error in _get_knowledge_base_content_path: {e}")
            # With MinIO storage, we can't use local file paths for content
            logger.warning(f"Using MinIO storage - cannot resolve local content paths for file {file_id}")
            return None