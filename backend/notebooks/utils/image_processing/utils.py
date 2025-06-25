"""
Utility functions for image processing and video handling.
"""

import os
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def clean_title(title: str) -> str:
    """Clean the title by replacing non-alphanumeric characters with underscores."""
    # Replace all non-alphanumeric characters (except for underscores) with underscores
    cleaned = re.sub(r'[^\w\d]', '_', title)
    # Replace consecutive underscores with a single underscore
    cleaned = re.sub(r'_+', '_', cleaned)
    # Remove leading/trailing underscores
    cleaned = cleaned.strip('_')
    return cleaned

def get_video_title_from_url(url: str, cookies_browser: str = 'chrome') -> Optional[str]:
    """Extract the title of the video from the URL using yt-dlp and return a cleaned version."""
    try:
        from yt_dlp import YoutubeDL
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'nocheckcertificate': True,
            'cookiesfrombrowser': (cookies_browser,)
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            raw_title = info.get('title', None)
            if raw_title:
                return clean_title(raw_title)
            return None
            
    except Exception as e:
        logger.warning(f"Could not extract title from URL {url}: {e}")
        return None

def find_existing_path(video_title: str, suffix: str, is_dir: bool = True, parent_dir: str = ".") -> Optional[str]:
    """
    Find existing directories or files that match the video title pattern.
    
    Args:
        video_title: Base video title to search for
        suffix: Suffix to look for (e.g., "_Images", "_Dedup_Images", "_caption.json")
        is_dir: Whether to look for directories (True) or files (False)
        parent_dir: Parent directory to search in
        
    Returns:
        Full path if found, None otherwise
    """
    try:
        if not os.path.exists(parent_dir):
            return None
            
        # Look for exact match first
        exact_match = os.path.join(parent_dir, f"{video_title}{suffix}")
        if os.path.exists(exact_match):
            if (is_dir and os.path.isdir(exact_match)) or (not is_dir and os.path.isfile(exact_match)):
                return exact_match
        
        # Look for partial matches
        for item in os.listdir(parent_dir):
            item_path = os.path.join(parent_dir, item)
            if item.endswith(suffix) and video_title in item:
                if (is_dir and os.path.isdir(item_path)) or (not is_dir and os.path.isfile(item_path)):
                    return item_path
        
        return None
        
    except Exception as e:
        logger.warning(f"Error finding existing path for {video_title}{suffix}: {e}")
        return None
