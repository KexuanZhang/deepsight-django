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
    """Service for managing figure data JSON files across knowledge base items and reports."""
    
    @staticmethod
    def create_knowledge_base_figure_data(user_id: int, file_id: str, figure_data: List[Dict]) -> Optional[str]:
        """
        Creates individual figure_data.json file for a knowledge base item.
        Only creates if images folder exists.
        
        Args:
            user_id: User ID
            file_id: Knowledge base file ID (without f_ prefix)
            figure_data: List of figure dictionaries
            
        Returns:
            str: Absolute path to created figure_data.json file, or None if images folder doesn't exist
        """
        # Generate path to images folder
        images_folder_path = FigureDataService._get_knowledge_base_images_path(user_id, file_id)
        
        # Check if images folder exists
        if not os.path.exists(images_folder_path):
            logger.info(f"Images folder doesn't exist at {images_folder_path}, skipping figure_data.json creation")
            return None
        
        # Generate figure_data.json path
        figure_data_path = os.path.join(images_folder_path, "figure_data.json")
        
        # Validate and clean figure data
        cleaned_data = FigureDataService._validate_and_clean_figure_data(figure_data)
        
        # Write JSON file
        with open(figure_data_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Created figure_data.json at {figure_data_path}")
        return figure_data_path
    
    @staticmethod
    def create_combined_figure_data(report, selected_file_ids: List[str]) -> Optional[str]:
        """
        Creates combined figure_data.json file for a report by merging individual figure_data.json files.
        
        Args:
            report: Report instance
            selected_file_ids: List of knowledge base file IDs (with f_ prefix)
            
        Returns:
            str: Absolute path to combined figure_data.json file, or None if no figure data found
        """
        combined_figure_data = []
        
        # Collect figure data from all selected files
        for file_id_with_prefix in selected_file_ids:
            # Remove f_ prefix if present
            file_id = file_id_with_prefix.replace('f_', '') if file_id_with_prefix.startswith('f_') else file_id_with_prefix
            
            # Check if individual figure_data.json exists, if not try to create it
            individual_data = FigureDataService._load_knowledge_base_figure_data(report.user.pk, file_id)
            if not individual_data:
                # Try to create figure_data.json from existing images and captions
                individual_data = FigureDataService._create_figure_data_from_images(report.user.pk, file_id)
            
            if individual_data:
                combined_figure_data.extend(individual_data)
        
        # If no figure data found, return None
        if not combined_figure_data:
            logger.info("No figure data found in selected files")
            return None
        
        # Renumber figures sequentially
        combined_figure_data = FigureDataService._renumber_figures(combined_figure_data)
        
        # Generate combined figure_data.json path
        combined_path = FigureDataService._get_report_figure_data_path(report)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(combined_path), exist_ok=True)
        
        # Write combined JSON file
        with open(combined_path, 'w', encoding='utf-8') as f:
            json.dump(combined_figure_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Created combined figure_data.json at {combined_path} with {len(combined_figure_data)} figures")
        return combined_path
    
    @staticmethod
    def load_combined_figure_data(figure_data_path: str) -> List[Dict]:
        """Load combined figure data from JSON file."""
        if not figure_data_path or not os.path.exists(figure_data_path):
            return []
        
        try:
            with open(figure_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading figure data from {figure_data_path}: {e}")
            return []
    
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
            
            # Fallback: try different month combinations if the exact date doesn't work
            # This handles cases where there might be slight date mismatches
            data_root = getattr(settings, 'DEEPSIGHT_DATA_ROOT', '/tmp/deepsight_data')
            base_pattern = f"Users/u_{user_id}/knowledge_base_item/*/f_{file_id}/images"
            full_pattern = os.path.join(data_root, base_pattern)
            
            matching_paths = glob.glob(full_pattern)
            if matching_paths:
                # Use the first matching path found
                fallback_path = matching_paths[0]
                logger.info(f"Found images folder via fallback: {fallback_path}")
                return fallback_path
            
            # Final fallback: use current date (original behavior)
            current_date = datetime.now()
            year_month = current_date.strftime("%Y-%m")
            fallback_path = os.path.join(
                data_root,
                f"Users/u_{user_id}/knowledge_base_item/{year_month}/f_{file_id}/images"
            )
            logger.warning(f"No images folder found, using current date fallback: {fallback_path}")
            return fallback_path
            
        except Exception as e:
            logger.error(f"Error in _get_knowledge_base_images_path: {e}")
            # Final fallback: use current date
            data_root = getattr(settings, 'DEEPSIGHT_DATA_ROOT', '/tmp/deepsight_data')
            current_date = datetime.now()
            year_month = current_date.strftime("%Y-%m")
            return os.path.join(
                data_root,
                f"Users/u_{user_id}/knowledge_base_item/{year_month}/f_{file_id}/images"
            )
    
    @staticmethod
    def _get_report_figure_data_path(report) -> str:
        """Generate absolute path for combined report figure_data.json."""
        data_root = getattr(settings, 'DEEPSIGHT_DATA_ROOT', '/tmp/deepsight_data')
        
        user_id = report.user.pk
        current_date = datetime.now()
        year_month = current_date.strftime("%Y-%m")
        report_id = report.pk
        
        notebook_id = None
        if hasattr(report, 'notebooks') and report.notebooks:
            notebook_id = report.notebooks.pk
        
        if notebook_id:
            relative_path = f"Users/u_{user_id}/n_{notebook_id}/report/{year_month}/r_{report_id}/figure_data.json"
        else:
            relative_path = f"Users/u_{user_id}/report/{year_month}/r_{report_id}/figure_data.json"
        
        return os.path.join(data_root, relative_path)
    
    @staticmethod
    def _load_knowledge_base_figure_data(user_id: int, file_id: str) -> List[Dict]:
        """Load individual figure_data.json from knowledge base item."""
        images_folder_path = FigureDataService._get_knowledge_base_images_path(user_id, file_id)
        figure_data_path = os.path.join(images_folder_path, "figure_data.json")
        
        if not os.path.exists(figure_data_path):
            return []
        
        try:
            with open(figure_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading figure data from {figure_data_path}: {e}")
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
            
            # Fallback: try different month combinations if the exact date doesn't work
            data_root = getattr(settings, 'DEEPSIGHT_DATA_ROOT', '/tmp/deepsight_data')
            base_pattern = f"Users/u_{user_id}/knowledge_base_item/*/f_{file_id}/content"
            full_pattern = os.path.join(data_root, base_pattern)
            
            matching_paths = glob.glob(full_pattern)
            if matching_paths:
                # Use the first matching path found
                fallback_path = matching_paths[0]
                logger.info(f"Found content folder via fallback: {fallback_path}")
                return fallback_path
            
            # Final fallback: use current date (original behavior)
            current_date = datetime.now()
            year_month = current_date.strftime("%Y-%m")
            fallback_path = os.path.join(
                data_root,
                f"Users/u_{user_id}/knowledge_base_item/{year_month}/f_{file_id}/content"
            )
            logger.warning(f"No content folder found, using current date fallback: {fallback_path}")
            return fallback_path
            
        except Exception as e:
            logger.error(f"Error in _get_knowledge_base_content_path: {e}")
            # Final fallback: use current date
            data_root = getattr(settings, 'DEEPSIGHT_DATA_ROOT', '/tmp/deepsight_data')
            current_date = datetime.now()
            year_month = current_date.strftime("%Y-%m")
            return os.path.join(
                data_root,
                f"Users/u_{user_id}/knowledge_base_item/{year_month}/f_{file_id}/content"
            )