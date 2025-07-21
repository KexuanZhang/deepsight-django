"""
Common utilities for formatting HTML image tags, captions, and content.
Includes all patterns and constants for image processing.
"""

import re
import logging
from typing import Optional

# =============================================================================
# PATTERNS AND CONSTANTS
# =============================================================================

# UUID Pattern for figure IDs (8-4-4-4-12 hexadecimal characters)
UUID_PATTERN = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'

# Compiled regex patterns for better performance
UUID_REGEX = re.compile(UUID_PATTERN)
UUID_BRACKET_PATTERN = rf'<({UUID_PATTERN})>'
UUID_BRACKET_REGEX = re.compile(UUID_BRACKET_PATTERN)

# Standalone placeholder pattern for figure replacements
PLACEHOLDER_PATTERN = rf"^\s*<({UUID_PATTERN})>\s*$"
PLACEHOLDER_REGEX = re.compile(PLACEHOLDER_PATTERN, re.MULTILINE)

# Pattern for checking existing img tags
EXISTING_IMG_PATTERN = r'<img\s+[^>]*src="[^"]*{figure_id}[^"]*"[^>]*>'

# Image style constants
MAX_IMAGE_HEIGHT = "500px"
DEFAULT_IMAGE_STYLE = f"max-height: {MAX_IMAGE_HEIGHT};"

# Caption and figure patterns
FIGURE_LINE_PATTERN = r"^(?:<[^>]+>\s*)*\*{0,2}(?:Figure|Fig\.?|图)\s+(\d+)\.?[\s:|]+(.+?)(?:\*{0,2})?$"
FIGURE_LINE_REGEX = re.compile(FIGURE_LINE_PATTERN, re.IGNORECASE)

# Markdown image patterns
MD_IMAGE_PATTERN = r"^(?:<[^>]+>\s*)*!\[\]\((.*?)\)\s*(?:<[^>]+>)*$"
MD_IMAGE_REGEX = re.compile(MD_IMAGE_PATTERN, re.IGNORECASE)

# HTML image patterns
HTML_IMG_PATTERN = r'^<img\s+[^>]*?src=["\'](.*?)["\'][^>]*?>$'
HTML_IMG_REGEX = re.compile(HTML_IMG_PATTERN, re.IGNORECASE)

# HTML figure formatting patterns
HTML_FIGURE_PATTERN = (
    r"(<img\s+[^>]*?(?:src|alt)=[\"'][^>]*?>)"  # HTML img tag
    r"\s*(?:\r?\n)*\s*"  # any whitespace/newlines
    r"((?:Figure|图)\s*\d+[:：].+?)[ \t]*\r?\n"  # caption line
)
HTML_FIGURE_REGEX = re.compile(HTML_FIGURE_PATTERN, re.DOTALL)

# Caption pattern for proper spacing
CAPTION_PATTERN = r"^((?:Figure|图)\s*\d+[:：].*?)(?:\r?\n)(?!\r?\n)"
CAPTION_REGEX = re.compile(CAPTION_PATTERN, re.MULTILINE)

# Title cleaning patterns
TITLE_HTML_TAGS_PATTERN = r"<(strong|em|b|i)>(.*?)</\1>"
TITLE_HTML_TAGS_REGEX = re.compile(TITLE_HTML_TAGS_PATTERN)

TITLE_SPAN_PATTERN = r"<span[^>]*?>(.*?)</span>"
TITLE_SPAN_REGEX = re.compile(TITLE_SPAN_PATTERN)

TITLE_REMAINING_HTML_PATTERN = r"<[^>]*?>"
TITLE_REMAINING_HTML_REGEX = re.compile(TITLE_REMAINING_HTML_PATTERN)

TITLE_WHITESPACE_PATTERN = r"\s+"
TITLE_WHITESPACE_REGEX = re.compile(TITLE_WHITESPACE_PATTERN)

# =============================================================================
# FORMATTING FUNCTIONS
# =============================================================================

logger = logging.getLogger(__name__)


def create_img_tag(src: str, figure_id: Optional[str] = None, style: Optional[str] = None) -> str:
    """
    Create an HTML img tag with consistent formatting.
    
    Args:
        src: Image source URL
        figure_id: Optional figure ID for identification
        style: Optional CSS style, defaults to DEFAULT_IMAGE_STYLE
        
    Returns:
        HTML img tag string
    """
    if not src:
        logger.warning("No source URL provided for image tag")
        return ""
    
    if style is None:
        style = DEFAULT_IMAGE_STYLE
    
    return f'<img src="{src}" style="{style}">'


def create_image_placeholder(figure_id: str) -> str:
    """
    Create a placeholder for missing images.
    
    Args:
        figure_id: Figure ID for the placeholder
        
    Returns:
        HTML div placeholder
    """
    return f'<div style="padding: 20px; border: 1px dashed #ccc; text-align: center;">Image not found (ID: {figure_id})</div>'


def create_figure_insertion(image_url: Optional[str], figure_id: str, caption: str, style: Optional[str] = None) -> str:
    """
    Create complete figure insertion text with image and caption.
    
    Args:
        image_url: URL for the image, None if not available
        figure_id: Figure ID for fallback placeholder
        caption: Figure caption text
        style: Optional CSS style for the image
        
    Returns:
        Complete HTML insertion text
    """
    if image_url:
        img_tag = create_img_tag(image_url, figure_id, style)
        return f'{img_tag}\n\n{caption}\n\n'
    else:
        placeholder = create_image_placeholder(figure_id)
        return f'{placeholder}\n\n{caption}\n\n'


def clean_title_text(text: str) -> Optional[str]:
    """
    Clean title text by removing HTML tags and normalizing whitespace.
    
    Args:
        text: Raw title text that may contain HTML tags
        
    Returns:
        Cleaned title text, or None if no valid text remains
    """
    if not text:
        return None

    # First, extract text content from common HTML tags before removing them
    # Handle <strong>, <em>, <b>, <i> tags by keeping their content
    clean_title = TITLE_HTML_TAGS_REGEX.sub(r"\2", text)

    # Handle span tags that may contain useful text
    # Extract content from spans but remove the span tags themselves
    clean_title = TITLE_SPAN_REGEX.sub(r"\1", clean_title)

    # Remove any remaining HTML tags (including self-closing ones and those without content)
    clean_title = TITLE_REMAINING_HTML_REGEX.sub("", clean_title)

    # Normalize whitespace (collapse multiple spaces into one)
    clean_title = TITLE_WHITESPACE_REGEX.sub(" ", clean_title).strip()

    return clean_title if clean_title else None


def preserve_figure_formatting(content: str) -> str:
    """
    Ensure that all figure image embeds are in HTML format and properly formatted
    with consistent spacing around images and captions.
    
    Args:
        content: Content to format
        
    Returns:
        Formatted content with consistent figure spacing
    """
    if not content:
        return ""

    # First convert any Markdown images to HTML format
    def md_to_html(match):
        # Extract image path from ![...](...)
        md_img = match.group(0)
        path_match = re.search(r"\]\(([^)]+)\)", md_img)
        if path_match:
            path = path_match.group(1)
            alt_match = re.search(r"\!\[(.*?)\]", md_img)
            alt = alt_match.group(1) if alt_match else "Figure"
            # Convert to HTML format with max-height
            return f'<img src="{path}" alt="{alt}" style="{DEFAULT_IMAGE_STYLE}">'
        return md_img

    # Convert standalone Markdown images to HTML
    content = re.sub(r"\!\[(?:Figure|图)?\s*\d*\]\([^\)]+\)", md_to_html, content)

    # Match HTML image tag + caption (ASCII ':' or full-width '：')
    content = HTML_FIGURE_REGEX.sub(r"\n\n\1\n\n\2\n\n", content)

    # Wrap any standalone HTML images with proper spacing
    def wrap_html_img(m):
        return f"\n\n{m.group(1)}\n\n"

    content = re.sub(r"(<img\s+[^>]*?(?:src|alt)=[\"'][^>]*?>)", wrap_html_img, content)

    # Collapse more than two newlines into exactly two
    content = re.sub(r"\n{3,}", "\n\n", content)

    # Ensure each caption line is followed by exactly two newlines
    content = CAPTION_REGEX.sub(r"\1\n\n", content)

    return content


def normalize_content_spacing(content: str) -> str:
    """
    Normalize spacing in content by collapsing excessive newlines.
    
    Args:
        content: Content to normalize
        
    Returns:
        Content with normalized spacing
    """
    if not content:
        return ""
    
    # Collapse more than two newlines into exactly two
    return re.sub(r"\n{3,}", "\n\n", content)