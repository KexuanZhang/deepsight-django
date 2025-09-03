"""
Shared utility functions for the DeepSight application.
"""

import hashlib
import mimetypes
import uuid
from typing import Any, Dict, List, Optional
from pathlib import Path
from django.core.files.storage import default_storage


def generate_unique_filename(original_filename: str, user_id: str = None) -> str:
    """
    Generate a unique filename based on original filename and optional user ID.
    
    Args:
        original_filename: The original filename
        user_id: Optional user ID to include in the path
        
    Returns:
        Unique filename with path
    """
    file_ext = Path(original_filename).suffix
    unique_name = f"{uuid.uuid4()}{file_ext}"
    
    if user_id:
        return f"users/{user_id}/{unique_name}"
    else:
        return f"shared/{unique_name}"


def calculate_file_hash(file_content: bytes) -> str:
    """
    Calculate SHA-256 hash of file content.
    
    Args:
        file_content: Bytes content of the file
        
    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(file_content).hexdigest()


def get_content_type(filename: str) -> str:
    """
    Get MIME content type for a filename.
    
    Args:
        filename: Name of the file
        
    Returns:
        MIME content type
    """
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or 'application/octet-stream'


def safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing/replacing problematic characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    import re
    # Remove or replace problematic characters
    safe_name = re.sub(r'[^\w\s.-]', '', filename)
    # Replace multiple spaces with single space
    safe_name = re.sub(r'\s+', ' ', safe_name)
    # Remove leading/trailing spaces and dots
    safe_name = safe_name.strip(' .')
    
    return safe_name if safe_name else 'unnamed_file'


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def paginate_queryset(queryset, page: int = 1, page_size: int = 20):
    """
    Simple pagination helper for querysets.
    
    Args:
        queryset: Django queryset to paginate
        page: Page number (1-based)
        page_size: Number of items per page
        
    Returns:
        Dict with paginated results and metadata
    """
    from django.core.paginator import Paginator, EmptyPage
    
    paginator = Paginator(queryset, page_size)
    
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    return {
        'results': list(page_obj),
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'page_size': page_size,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    }


def validate_json_structure(data: Any, required_fields: List[str]) -> bool:
    """
    Validate that a JSON object has required fields.
    
    Args:
        data: Data to validate
        required_fields: List of required field names
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(data, dict):
        return False
    
    return all(field in data for field in required_fields)


def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """
    Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (values will override dict1)
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if (key in result 
            and isinstance(result[key], dict) 
            and isinstance(value, dict)):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def clean_html_tags(text: str) -> str:
    """
    Remove HTML tags from text while preserving content.
    
    Args:
        text: Text that may contain HTML tags
        
    Returns:
        Clean text without HTML tags
    """
    import re
    
    # Remove HTML tags
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length with optional suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length of result
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix