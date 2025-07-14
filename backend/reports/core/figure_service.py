import json
import os
import glob
from pathlib import Path
from typing import List, Dict, Optional
from django.conf import settings
from datetime import datetime
import logging

# Import extract_figure_data from paper_processing
from agents.report_agent.utils.paper_processing import extract_figure_data

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
            from notebooks.utils.knowledge_base_image_service import KnowledgeBaseImageService
            
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
            from notebooks.utils.knowledge_base_image_service import KnowledgeBaseImageService
            
            image_service = KnowledgeBaseImageService()
            
            # Get combined figure data from database
            combined_figure_data = image_service.get_combined_figure_data_for_files(
                file_ids=selected_file_ids,
                user_id=report.user.pk
            )
            
        if not combined_figure_data:
                logger.info("No figure data found in database for selected files")
            return None
        
            # Store the figure data directly in the report instance for immediate use
            # This avoids the need to create temporary files
            report._cached_figure_data = combined_figure_data
            
            logger.info(f"Retrieved combined figure data from database: {len(combined_figure_data)} figures")
            return f"database_combined_{report.id}"  # Return success indicator
            
        except Exception as e:
            logger.error(f"Error creating combined figure data from database: {e}")
            return None
    
    @staticmethod
    def load_combined_figure_data(figure_data_path: str) -> List[Dict]:
        """
        Load figure data from database or fallback to JSON file.
        This method maintains compatibility with existing code.
        """
        # Check if this is a database reference
        if figure_data_path and figure_data_path.startswith('database_'):
            try:
                # Extract identifiers from the path
                if 'combined_' in figure_data_path:
                    # This is a combined figure data request
                    report_id = figure_data_path.split('_')[-1]
                    
                    # Try to get from cached data first
                    from reports.models import Report
                    try:
                        report = Report.objects.get(id=int(report_id))
                        if hasattr(report, '_cached_figure_data'):
                            return report._cached_figure_data
                    except:
                        pass
                    
                    # If no cached data, return empty list (should be handled by caller)
                    logger.warning(f"No cached figure data found for report {report_id}")
                    return []
                    
                elif 'kb_' in figure_data_path:
                    # This is a single knowledge base item request
                    kb_item_id = figure_data_path.split('_')[-1]
                    
                    from notebooks.utils.knowledge_base_image_service import KnowledgeBaseImageService
                    image_service = KnowledgeBaseImageService()
                    
                    return image_service.get_images_for_knowledge_base_item(
                        kb_item_id=int(kb_item_id)
                    )
                
            except Exception as e:
                logger.error(f"Error loading figure data from database reference {figure_data_path}: {e}")
                return []
        
        # Fallback to original JSON file loading for backward compatibility
        if not figure_data_path or not os.path.exists(figure_data_path):
            return []
        
        try:
            with open(figure_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading figure data from {figure_data_path}: {e}")
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
            from notebooks.utils.knowledge_base_image_service import KnowledgeBaseImageService
            
            image_service = KnowledgeBaseImageService()
            
            return image_service.get_images_for_knowledge_base_item(
                kb_item_id=int(file_id),
                user_id=user_id
            )
            
        except Exception as e:
            logger.error(f"Error getting figure data for kb_item {file_id}: {e}")
            return []
    
    @staticmethod
    def migrate_existing_figure_data_to_database(user_id: int, file_id: str) -> bool:
        """
        Migrate existing figure_data.json files to database.
        This helps transition from the old file-based system.
        
        Args:
            user_id: User ID
            file_id: Knowledge base file ID (without f_ prefix)
            
        Returns:
            True if migration was successful, False otherwise
        """
        try:
            # Try to find existing figure_data.json file
            images_folder_path = FigureDataService._get_knowledge_base_images_path(user_id, file_id)
            
            if images_folder_path and os.path.exists(images_folder_path):
                figure_data_path = os.path.join(images_folder_path, "figure_data.json")
                
                if os.path.exists(figure_data_path):
                    from notebooks.utils.knowledge_base_image_service import KnowledgeBaseImageService
                    
                    image_service = KnowledgeBaseImageService()
                    success = image_service.migrate_figure_data_json_to_database(
                        kb_item_id=int(file_id),
                        figure_data_path=figure_data_path,
                        user_id=user_id
                    )
                    
                    if success:
                        logger.info(f"Successfully migrated figure_data.json to database for kb_item {file_id}")
                        return True
            
            # Also try to create figure data from existing images if no JSON file exists
            return FigureDataService._create_figure_data_from_images_in_database(user_id, file_id)
            
        except Exception as e:
            logger.error(f"Error migrating figure data to database for kb_item {file_id}: {e}")
            return False
    
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
            
            # Extract figure data using paper_processing function
            figure_data = extract_figure_data(md_file_path)
            
            if figure_data:
                from notebooks.utils.knowledge_base_image_service import KnowledgeBaseImageService
                
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
            kb_item = KnowledgeBaseItem.objects.filter(id=file_id, user_id=user_id).first()
            
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
        """Generate absolute path for combined report figure_data.json."""
        # With MinIO storage, we can't use local file paths
        logger.warning(f"Using MinIO storage - cannot resolve local figure data path for report {report.id}")
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
        """Load individual figure_data.json from knowledge base item."""
        # With MinIO storage, we can't load figure data from local files
        logger.info(f"Using MinIO storage - cannot load figure data for file {file_id}")
        return []
    
    @staticmethod
    def _validate_and_clean_figure_data(figure_data: List[Dict]) -> List[Dict]:
        """Validate figure data and ensure all image paths are absolute."""
        cleaned_data = []
        
        for i, figure in enumerate(figure_data):
            # Validate required fields
            required_fields = ['image_path', 'figure_name', 'caption']
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
                'figure_name': figure['figure_name'],
                'caption': figure['caption']
            }
            cleaned_data.append(cleaned_figure)
        
        return cleaned_data
    
    @staticmethod
    def _renumber_figures(figures: List[Dict]) -> List[Dict]:
        """Renumber all figures as Figure 1, Figure 2, etc."""
        for i, figure in enumerate(figures, 1):
            figure['figure_name'] = f"Figure {i}"
        return figures
    
    @staticmethod
    def _create_figure_data_from_images(user_id: int, file_id: str) -> List[Dict]:
        """
        Create figure data by extracting from markdown content in the content folder.
        Only creates if images folder exists and figure_data.json doesn't already exist.
        """
        images_folder_path = FigureDataService._get_knowledge_base_images_path(user_id, file_id)
        
        if not os.path.exists(images_folder_path):
            logger.info(f"Images folder doesn't exist at {images_folder_path}")
            return []
        
        # Check if figure_data.json already exists (should be created by media extractor)
        figure_data_path = os.path.join(images_folder_path, "figure_data.json")
        if os.path.exists(figure_data_path):
            logger.info(f"figure_data.json already exists at {figure_data_path}, not creating from markdown")
            return []
        
        # Get the content folder path
        content_folder_path = FigureDataService._get_knowledge_base_content_path(user_id, file_id)
        
        if not os.path.exists(content_folder_path):
            logger.info(f"Content folder doesn't exist at {content_folder_path}")
            # Create empty figure_data.json since images folder exists but no content
            with open(figure_data_path, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            logger.info(f"Created empty figure_data.json at {figure_data_path}")
            return []
        
        # Find markdown file in content folder
        md_files = glob.glob(os.path.join(content_folder_path, "*.md"))
        if not md_files:
            logger.info(f"No markdown files found in {content_folder_path}")
            # Create empty figure_data.json since images folder exists but no markdown file
            with open(figure_data_path, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            logger.info(f"Created empty figure_data.json at {figure_data_path}")
            return []
        
        # Use the first markdown file found
        md_file_path = md_files[0]
        logger.info(f"Extracting figure data from {md_file_path}")
        
        try:
            # Extract figure data using paper_processing function
            figure_data = extract_figure_data(md_file_path)
            
            # Update image paths to point to the images folder
            updated_figure_data = []
            for figure in figure_data:
                # Get just the filename from the original image path
                image_filename = os.path.basename(figure['image_path'])
                # Create absolute path to the image in the images folder
                absolute_image_path = os.path.join(images_folder_path, image_filename)
                
                # Only include if the image file actually exists in the images folder
                if os.path.exists(absolute_image_path):
                    updated_figure = {
                        'image_path': absolute_image_path,
                        'figure_name': figure['figure_name'],
                        'caption': figure['caption']
                    }
                    updated_figure_data.append(updated_figure)
                else:
                    logger.warning(f"Image file {absolute_image_path} referenced in markdown but not found in images folder")
            
            # Create figure_data.json file (even if empty)
            with open(figure_data_path, 'w', encoding='utf-8') as f:
                json.dump(updated_figure_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created figure_data.json at {figure_data_path} with {len(updated_figure_data)} figures")
            return updated_figure_data
            
        except Exception as e:
            logger.error(f"Error extracting figure data from {md_file_path}: {e}")
            # Create empty figure_data.json on error
            with open(figure_data_path, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            logger.info(f"Created empty figure_data.json at {figure_data_path} due to extraction error")
            return []
    
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
            kb_item = KnowledgeBaseItem.objects.filter(id=file_id, user_id=user_id).first()
            
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