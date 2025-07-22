"""
Unified image utilities package for reports.

This package provides the unified image insertion service and supporting utilities.
"""

from .formatters import (
    UUID_PATTERN, MAX_IMAGE_HEIGHT, DEFAULT_IMAGE_STYLE,
    UUID_REGEX, UUID_BRACKET_REGEX, PLACEHOLDER_REGEX
)
from .extractors import (
    extract_figure_ids_from_content, find_figure_placeholders,
    find_already_inserted_figures, extract_figure_data_from_markdown,
    get_insertion_points, find_placeholder_end
)
from .formatters import (
    create_img_tag, create_image_placeholder, create_figure_insertion,
    clean_title_text, preserve_figure_formatting, normalize_content_spacing
)
from .validators import (
    is_valid_uuid, is_valid_figure_id, validate_figure_ids,
    convert_to_uuid_objects, validate_image_url, validate_caption
)
from .url_providers import ImageUrlProvider, DatabaseUrlProvider
from .insertion_service import ImageInsertionService

__all__ = [
    # Main service (primary interface) - single universal service
    'ImageInsertionService', 'DatabaseUrlProvider',
    
    # Patterns & Constants (from formatters.py)
    'UUID_PATTERN', 'MAX_IMAGE_HEIGHT', 'DEFAULT_IMAGE_STYLE',
    'UUID_REGEX', 'UUID_BRACKET_REGEX', 'PLACEHOLDER_REGEX',
    
    # Extractors
    'extract_figure_ids_from_content', 'find_figure_placeholders',
    'find_already_inserted_figures', 'extract_figure_data_from_markdown',
    'get_insertion_points', 'find_placeholder_end',
    
    # Formatters
    'create_img_tag', 'create_image_placeholder', 'create_figure_insertion',
    'clean_title_text', 'preserve_figure_formatting', 'normalize_content_spacing',
    
    # Validators
    'is_valid_uuid', 'is_valid_figure_id', 'validate_figure_ids',
    'convert_to_uuid_objects', 'validate_image_url', 'validate_caption',
]