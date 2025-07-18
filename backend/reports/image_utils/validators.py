"""
Common utilities for validating figure IDs and image data.
"""

import logging
from uuid import UUID
from typing import List, Optional
from .formatters import UUID_REGEX

logger = logging.getLogger(__name__)


def is_valid_uuid(uuid_string: str) -> bool:
    """
    Check if a string is a valid UUID format.
    
    Args:
        uuid_string: String to validate
        
    Returns:
        True if valid UUID format, False otherwise
    """
    if not uuid_string or not isinstance(uuid_string, str):
        return False
    
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False


def is_valid_figure_id(figure_id: str) -> bool:
    """
    Check if a figure ID matches the expected UUID pattern.
    
    Args:
        figure_id: Figure ID to validate
        
    Returns:
        True if valid figure ID, False otherwise
    """
    if not figure_id or not isinstance(figure_id, str):
        return False
    
    return bool(UUID_REGEX.fullmatch(figure_id))


def validate_figure_ids(figure_ids: List[str]) -> List[str]:
    """
    Validate a list of figure IDs and return only valid ones.
    
    Args:
        figure_ids: List of figure ID strings to validate
        
    Returns:
        List of valid figure ID strings
    """
    if not figure_ids:
        return []
    
    valid_ids = []
    for fig_id in figure_ids:
        if is_valid_figure_id(fig_id):
            valid_ids.append(fig_id)
        else:
            logger.warning(f"Invalid figure ID format: {fig_id}")
    
    return valid_ids


def convert_to_uuid_objects(figure_ids: List[str]) -> List[UUID]:
    """
    Convert string figure IDs to UUID objects, filtering out invalid ones.
    
    Args:
        figure_ids: List of figure ID strings
        
    Returns:
        List of UUID objects
    """
    uuid_objects = []
    for fig_id in figure_ids:
        try:
            uuid_objects.append(UUID(fig_id))
        except ValueError:
            logger.warning(f"Invalid UUID format for figure_id: {fig_id}")
            continue
    
    return uuid_objects


def validate_image_url(url: Optional[str]) -> bool:
    """
    Basic validation for image URLs.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL appears valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL validation - should start with http/https or be a data URL
    url = url.strip()
    return (
        url.startswith(('http://', 'https://', 'data:image/', '/')) and
        len(url) > 10
    )


def validate_caption(caption: Optional[str]) -> bool:
    """
    Basic validation for figure captions.
    
    Args:
        caption: Caption to validate
        
    Returns:
        True if caption appears valid, False otherwise
    """
    if not caption or not isinstance(caption, str):
        return False
    
    # Caption should be non-empty after stripping
    return len(caption.strip()) > 0