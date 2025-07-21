"""
Unified image insertion service that handles all image insertion needs.
"""

import logging
from typing import List, Dict, Optional

from .extractors import (
    find_figure_placeholders, find_already_inserted_figures,
    get_insertion_points, find_placeholder_end
)
from .formatters import create_figure_insertion, normalize_content_spacing
from .url_providers import ImageUrlProvider

logger = logging.getLogger(__name__)


class ImageInsertionService:
    """
    Universal image insertion service.
    
    This is the ONLY image insertion service needed anywhere in the codebase.
    Handles both Django and agents contexts through URL provider strategy.
    """
    
    def __init__(self, url_provider: ImageUrlProvider):
        """
        Initialize the service with a URL provider strategy.
        
        Args:
            url_provider: Strategy for getting image URLs
        """
        self.url_provider = url_provider
    
    def insert_figure_images(self, 
                           content: str, 
                           figures: List[Dict[str, str]], 
                           **kwargs) -> str:
        """
        Insert image HTML tags into content at figure placeholders.
        
        This replaces ALL other insert_figure_images functions in the codebase.
        
        Args:
            content: Content with figure placeholders like <figure_id>
            figures: List of dicts with 'figure_id' and 'caption' keys
            **kwargs: Additional context passed to URL provider (report_id, etc.)
            
        Returns:
            Updated content with HTML image tags replacing placeholders
        """
        if not content or not figures:
            return content
        
        # Create mapping of figure_id to caption
        figure_dict = {
            fig["figure_id"]: fig["caption"] for fig in figures
        }
        
        # Check which figures have already been inserted
        figure_ids_list = list(figure_dict.keys())
        already_inserted = find_already_inserted_figures(content, figure_ids_list)
        
        # Filter out already inserted figures
        filtered_figure_dict = {
            k: v for k, v in figure_dict.items() 
            if k not in already_inserted
        }
        
        if not filtered_figure_dict:
            logger.info("No new figures to insert")
            return content
        
        # Find figure placeholders in content
        valid_occurrences = find_figure_placeholders(content, filtered_figure_dict)
        
        if not valid_occurrences:
            logger.info("No figure placeholders found in content")
            return content
        
        # Get sorted insertion points
        insertion_points = get_insertion_points(content, valid_occurrences)
        
        # Process insertions from end to beginning to maintain positions
        output_segments = []
        prev_end = 0
        
        for pos, figure_id in insertion_points:
            # Find the end of the placeholder line
            placeholder_end = find_placeholder_end(content, pos, figure_id)
            
            if placeholder_end:
                # Add content before placeholder
                output_segments.append(content[prev_end:pos])
                
                # Get image URL using the provider strategy
                caption = filtered_figure_dict[figure_id]
                image_url = self.url_provider.get_image_url(figure_id, **kwargs)
                
                # Create figure insertion (image + caption)
                insertion_text = create_figure_insertion(image_url, figure_id, caption)
                output_segments.append(insertion_text)
                
                prev_end = placeholder_end
        
        # Add remaining content
        output_segments.append(content[prev_end:])
        result = "".join(output_segments)
        
        # Normalize spacing
        result = normalize_content_spacing(result)
        
        logger.info(f"Successfully inserted {len(insertion_points)} figures into content")
        return result