"""
Common utilities for extracting figure IDs and image information from content.
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from .formatters import (
    UUID_PATTERN, PLACEHOLDER_REGEX, EXISTING_IMG_PATTERN,
    MD_IMAGE_REGEX, HTML_IMG_REGEX, FIGURE_LINE_REGEX
)

logger = logging.getLogger(__name__)


def extract_figure_ids_from_content(content: str) -> List[str]:
    """
    Extract all figure IDs from content.
    Looks for UUID patterns that represent figure IDs.
    
    Args:
        content: Content with figure ID placeholders
        
    Returns:
        List of figure ID strings (UUIDs)
    """
    if not content:
        return []
    
    # Find all UUIDs in the content (these should be figure IDs)
    figure_ids = re.findall(UUID_PATTERN, content)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_figure_ids = []
    for fig_id in figure_ids:
        if fig_id not in seen:
            seen.add(fig_id)
            unique_figure_ids.append(fig_id)
    
    logger.info(f"Extracted {len(unique_figure_ids)} unique figure IDs from content")
    return unique_figure_ids


def find_figure_placeholders(content: str, figure_dict: Dict[str, str]) -> Dict[str, int]:
    """
    Find first occurrences of figure placeholders in content.
    
    Args:
        content: Content to search
        figure_dict: Dictionary mapping figure_id to caption
        
    Returns:
        Dictionary mapping figure_id to position in content
    """
    if not content or not figure_dict:
        return {}
    
    # Look for figure placeholders in format <figure uuid> on standalone lines
    matches = list(PLACEHOLDER_REGEX.finditer(content))
    
    first_occurrences = {}
    for match in matches:
        figure_id = match.group(1).strip()
        
        # Only include if we have this figure in our figure_dict
        if figure_id in figure_dict:
            if figure_id not in first_occurrences:
                first_occurrences[figure_id] = match.start()
    
    return first_occurrences


def find_already_inserted_figures(content: str, figure_ids: List[str]) -> Set[str]:
    """
    Check which figures have already been inserted by looking for existing img tags.
    
    Args:
        content: Content to check
        figure_ids: List of figure IDs to check for
        
    Returns:
        Set of figure IDs that are already inserted
    """
    already_inserted = set()
    
    for figure_id in figure_ids:
        # Check if there's already an img tag with this figure_id
        existing_img_pattern = EXISTING_IMG_PATTERN.format(figure_id=re.escape(str(figure_id)))
        if re.search(existing_img_pattern, content, re.IGNORECASE):
            already_inserted.add(figure_id)
            logger.info(f"Figure ID '{figure_id}' already inserted, skipping.")
    
    return already_inserted


def extract_figure_data_from_markdown(file_path: str) -> List[Dict[str, str]]:
    """
    Extract figure information (image path, caption) from a Markdown file.
    
    Args:
        file_path: Path to the Markdown file
        
    Returns:
        List of dictionaries with 'image_path' and 'caption' keys
    """
    if not file_path:
        return []

    figures = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        raise ValueError(f"Error reading file {file_path}: {e}")

    # First pass: collect all images
    image_locations = []
    for i, line in enumerate(lines):
        line_cleaned = line.strip()
        image_match = MD_IMAGE_REGEX.match(line_cleaned)
        html_img_match = None if image_match else HTML_IMG_REGEX.match(line_cleaned)

        if image_match or html_img_match:
            image_path = (
                image_match.group(1) if image_match else html_img_match.group(1)
            )
            image_locations.append((i, image_path))

    # Second pass: look for captions and associate with the nearest preceding image
    for i, line in enumerate(lines):
        caption_candidate_line = line.lstrip("\ufeff").strip()
        figure_match = FIGURE_LINE_REGEX.match(caption_candidate_line)

        if figure_match:
            figure_number = figure_match.group(1)
            caption = figure_match.group(2).strip()
            
            # Clean up markdown formatting in caption
            caption = re.sub(r'\*{2,}', '', caption)  # Remove ** markdown bold
            caption = caption.strip()

            # Find the nearest preceding image
            preceding_images = [
                (img_idx, img_path)
                for img_idx, img_path in image_locations
                if img_idx < i
            ]
            if preceding_images:
                # Get the closest image above this caption
                closest_img_idx, image_path = max(preceding_images, key=lambda x: x[0])

                # Check if the distance between image and caption is reasonable (within 10 lines)
                if i - closest_img_idx <= 10:
                    figures.append(
                        {
                            "image_path": image_path,
                            "caption": caption,
                        }
                    )

    # Remove duplicates while preserving order (based on image_path)
    unique_figures = []
    seen = set()
    for fig in figures:
        if fig["image_path"] not in seen:
            seen.add(fig["image_path"])
            unique_figures.append(fig)

    return unique_figures


def get_insertion_points(content: str, valid_occurrences: Dict[str, int]) -> List[Tuple[int, str]]:
    """
    Get sorted insertion points for figure replacements.
    
    Args:
        content: Content to process
        valid_occurrences: Dictionary of figure_id to position mappings
        
    Returns:
        List of (position, figure_id) tuples sorted by position
    """
    insertion_points = [
        (pos, figure_id) for figure_id, pos in valid_occurrences.items()
    ]
    insertion_points.sort(key=lambda x: x[0])
    return insertion_points


def find_placeholder_end(content: str, pos: int, figure_id: str) -> Optional[int]:
    """
    Find the end position of a placeholder in content.
    
    Args:
        content: Content to search
        pos: Starting position
        figure_id: Figure ID to search for
        
    Returns:
        End position of placeholder or None if not found
    """
    placeholder_match = re.search(
        r"^\s*<" + re.escape(figure_id) + r">\s*$",
        content[pos:],
        re.MULTILINE,
    )
    if placeholder_match:
        return pos + placeholder_match.end()
    return None