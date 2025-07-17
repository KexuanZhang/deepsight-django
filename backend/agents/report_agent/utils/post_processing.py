import re
import argparse
import os
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def remove_citations(content, post_processing=True):
    """
    Remove all citation markers in brackets except for pure numeric citations.
    
    Keeps: [1], [11], [[1]], [2][5][19] (pure numeric citations)
    Removes: [transcript x], [paper x], [somewords], [somewords with numbers], [transcript x][00:00:00], etc.

    Args:
        content (str): The markdown content to process
        post_processing (bool): Whether to remove citation markers

    Returns:
        str: The processed content
    """
    if not post_processing:
        return content

    def replacer(match):
        # If the content within the brackets is purely numeric, keep the original citation.
        # Otherwise, replace it with a space.
        if match.group(1).isdigit():
            return match.group(0)
        return " "

    # Process level-1 nested citations first, e.g., [[...]]
    # This pattern specifically looks for content that does not contain brackets itself.
    content = re.sub(r"\[\[([^\[\]]+)\]\]", replacer, content)

    # Process level-0 citations, e.g., [...]
    content = re.sub(r"\[([^\[\]]+)\]", replacer, content)
    
    # Clean up any multiple spaces that resulted from removals
    content = re.sub(r"[ \t]+", " ", content)
    
    # Clean up spaces at line boundaries (but preserve line breaks)
    content = re.sub(r"^ +", "", content, flags=re.MULTILINE)  # spaces at start of lines
    content = re.sub(r" +$", "", content, flags=re.MULTILINE)  # spaces at end of lines
    
    # Remove any empty lines that resulted from citations being on their own line
    # But be careful to preserve intentional double line breaks (paragraph breaks)
    # First normalize multiple newlines
    content = re.sub(r"\n{3,}", "\n\n", content)  # reduce 3+ newlines to 2
    
    return content


def remove_captions(content, remove_figure_captions=True):
    """
    Remove figure captions like "图 xx：xxx" (Chinese) or "Figure x: xxx" (English) from content.

    Args:
        content (str): The markdown content to process
        remove_figure_captions (bool): Whether to remove figure captions

    Returns:
        str: The processed content
    """
    if not remove_figure_captions:
        return content

    # Pattern to match Chinese captions: lines starting with "图" followed by digits, then "：", then any text until newline
    chinese_pattern = r"^图\s*\d+：.*\n"

    # Pattern to match English captions: lines starting with "Figure" or "figure" followed by digits, then ":", then any text until newline
    english_pattern = r"^[Ff]igure\s*\d+\s*:.*\n"

    # Remove Chinese figure captions
    content = re.sub(chinese_pattern, "", content, flags=re.MULTILINE)

    # Remove English figure captions
    content = re.sub(english_pattern, "", content, flags=re.MULTILINE)

    return content


def remove_figure_placeholders(content, remove_figure_placeholders=True):
    """
    Remove figure placeholders like <uuid>, <Figure 9>, <figure 9>, <图 9> from content and clean up resulting blank lines.

    Args:
        content (str): The markdown content to process
        remove_figure_placeholders (bool): Whether to remove figure placeholders

    Returns:
        str: The processed content
    """
    if not remove_figure_placeholders:
        return content

    # UUID pattern: 8-4-4-4-12 hexadecimal characters
    uuid_pattern = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    
    # Targeted patterns that include surrounding whitespace/newlines for better cleanup
    patterns = [
        # UUID placeholders that are on their own line (with optional surrounding whitespace)
        (rf"\n[ \t]*<\s*{uuid_pattern}\s*>[ \t]*\n", "\n"),  # \n<12f86924-df70-48a7-93e9-29f64855a4da>\n -> \n
        # UUID placeholders at the start of content
        (rf"^[ \t]*<\s*{uuid_pattern}\s*>[ \t]*\n", ""),  # ^<12f86924-df70-48a7-93e9-29f64855a4da>\n -> (empty)
        # UUID placeholders at the end of content
        (rf"\n[ \t]*<\s*{uuid_pattern}\s*>[ \t]*$", ""),  # \n<12f86924-df70-48a7-93e9-29f64855a4da>$ -> (empty)
        # Any remaining inline UUID placeholders
        (rf"<\s*{uuid_pattern}\s*>", ""),  # <12f86924-df70-48a7-93e9-29f64855a4da> -> (empty)
        
        # Bare UUID patterns (not in angle brackets)
        # UUID at the end of a sentence (preceded by space and followed by sentence end)
        (rf"\s+{uuid_pattern}(?=\s*[.!?])", ""),  # " 33e61969-bec2-4d93-ac39-175f1c1490e1." -> "."
        # UUID on its own line
        (rf"\n[ \t]*{uuid_pattern}[ \t]*\n", "\n"),  # \n33e61969-bec2-4d93-ac39-175f1c1490e1\n -> \n
        # UUID at start of content
        (rf"^[ \t]*{uuid_pattern}[ \t]*\n", ""),  # ^33e61969-bec2-4d93-ac39-175f1c1490e1\n -> (empty)
        # UUID at end of content
        (rf"\n[ \t]*{uuid_pattern}[ \t]*$", ""),  # \n33e61969-bec2-4d93-ac39-175f1c1490e1$ -> (empty)
        # Any remaining inline bare UUIDs (with surrounding whitespace)
        (rf"\s+{uuid_pattern}\s+", " "),  # " 33e61969-bec2-4d93-ac39-175f1c1490e1 " -> " "
        
        # Figure placeholders that are on their own line (with optional surrounding whitespace)
        (r"\n[ \t]*<\s*[Ff]igure\s*\d+\s*[^>]*>[ \t]*\n", "\n"),  # \n<Figure 9>\n -> \n
        (r"\n[ \t]*<\s*图\s*\d+\s*[^>]*>[ \t]*\n", "\n"),  # \n<图 9>\n -> \n
        (r"\n[ \t]*<\s*[Cc]hart\s*>[ \t]*\n", "\n"),  # \n<chart>\n -> \n
        # Figure placeholders at the start of content
        (
            r"^[ \t]*<\s*[Ff]igure\s*\d+\s*[^>]*>[ \t]*\n",
            "",
        ),  # ^<Figure 9>\n -> (empty)
        (r"^[ \t]*<\s*图\s*\d+\s*[^>]*>[ \t]*\n", ""),  # ^<图 9>\n -> (empty)
        (r"^[ \t]*<\s*[Cc]hart\s*>[ \t]*\n", ""),  # ^<chart>\n -> (empty)
        # Figure placeholders at the end of content
        (
            r"\n[ \t]*<\s*[Ff]igure\s*\d+\s*[^>]*>[ \t]*$",
            "",
        ),  # \n<Figure 9>$ -> (empty)
        (r"\n[ \t]*<\s*图\s*\d+\s*[^>]*>[ \t]*$", ""),  # \n<图 9>$ -> (empty)
        (r"\n[ \t]*<\s*[Cc]hart\s*>[ \t]*$", ""),  # \n<chart>$ -> (empty)
        # Any remaining inline figure placeholders
        (r"<\s*[Ff]igure\s*\d+\s*[^>]*>", ""),  # <Figure 9> -> (empty)
        (r"<\s*图\s*\d+\s*[^>]*>", ""),  # <图 9> -> (empty)
        (r"<\s*[Cc]hart\s*>", ""),  # <chart> -> (empty)
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    # Final cleanup: reduce multiple consecutive newlines to maximum of 2
    # This preserves intentional paragraph breaks (double spacing) while cleaning up excess
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content


def process_file(
    input_file,
    output_file=None,
    post_processing=True,
    remove_figure_captions=True,
    remove_placeholders=True,
):
    """
    Process a markdown file to remove citation markers, figure captions, and figure placeholders.

    Args:
        input_file (str): Path to the input markdown file
        output_file (str, optional): Path to save the processed file. If None, will use input_file with "_processed" suffix
        post_processing (bool): Whether to remove citation markers
        remove_figure_captions (bool): Whether to remove figure captions like "图 xx：xxx"
        remove_placeholders (bool): Whether to remove figure placeholders like <Figure 9>

    Returns:
        str: Path to the processed file
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Default output file if not specified
    if output_file is None:
        input_path = Path(input_file)
        stem = input_path.stem
        output_file = str(input_path.with_name(f"{stem}_processed{input_path.suffix}"))

    # Read the input file
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Process the content
    processed_content = remove_citations(content, post_processing)
    processed_content = remove_captions(processed_content, remove_figure_captions)
    processed_content = remove_figure_placeholders(
        processed_content, remove_placeholders
    )

    # Write the processed content
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(processed_content)

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Post-process polished articles to remove citation markers, figure captions, and figure placeholders"
    )
    parser.add_argument("input_file", help="Path to the input markdown file")
    parser.add_argument("--output-file", "-o", help="Path to save the processed file")
    parser.add_argument(
        "--no-post-processing",
        action="store_true",
        help="Skip removing citation markers like [transcript x] and [paper x]",
    )
    parser.add_argument(
        "--no-remove-captions",
        action="store_true",
        help="Skip removing figure captions",
    )
    parser.add_argument(
        "--no-remove-placeholders",
        action="store_true",
        help="Skip removing figure placeholders like <Figure 9>",
    )

    args = parser.parse_args()

    try:
        output_file = process_file(
            args.input_file,
            args.output_file,
            not args.no_post_processing,  # post_processing is True by default unless --no-post-processing is used
            not args.no_remove_captions,  # remove_figure_captions is True by default unless --no-remove-captions is used
            not args.no_remove_placeholders,  # remove_figure_placeholders is True by default unless --no-remove-placeholders is used
        )
        print(f"Processed file saved to: {output_file}")
    except Exception as e:
        print(f"Error processing file: {e}")
        return 1

    return 0


def fix_image_paths(
    content: str,
    knowledge_base_items: List[str],
    user_id: str,
    figure_data: Optional[List[dict]] = None,
) -> str:
    """
    Fix image paths in generated report content by replacing broken image src paths
    with correct MinIO URLs. Since the system uses UUID-based image references,
    this function handles any remaining filename-based references that may exist.

    Args:
        content (str): The markdown content containing image references
        knowledge_base_items (List[str]): List of knowledge base item IDs
        user_id (str): User ID for MinIO permission checks
        figure_data (Optional[List[dict]]): Figure data with MinIO URLs

    Returns:
        str: The content with fixed image paths using MinIO URLs
    """
    if not knowledge_base_items:
        logger.warning("No knowledge base items provided, skipping image path fixing")
        return content
    
    if not user_id:
        logger.warning("No user ID provided, skipping image path fixing")
        return content
    
    # Pattern to match img tags with problematic src paths
    # Matches images with underscores and common extensions (legacy filename-based references)
    # Skip images that have data-figure-id attribute (already processed by insert_figure_images)
    img_pattern = r'<img\s+src="([^"]*_[^"]*\.(?:jpeg|jpg|png|gif))"(?![^>]*data-figure-id)([^>]*)>'
    
    try:
        # Import here to avoid circular imports
        from notebooks.utils.knowledge_base_image_service import KnowledgeBaseImageService
        
        service = KnowledgeBaseImageService()
        image_mapping = {}
        
        # Get all images from knowledge base items and create filename -> URL mapping
        for kb_item_id in knowledge_base_items:
            try:
                images = service.get_images_for_knowledge_base_item(kb_item_id, user_id)
                
                for image_data in images:
                    # Extract filename from minio_object_key
                    object_key = image_data.get('minio_object_key', '')
                    if not object_key:
                        continue
                        
                    filename = os.path.basename(object_key)
                    if not filename:
                        continue
                    
                    # Get MinIO URL for the image (using UUID-based ID)
                    image_url = service.get_image_url(image_data['id'], user_id, expires=3600)
                    
                    # Simple mapping without conflict resolution since UUIDs are unique
                    # If multiple files have the same filename, use the last one found
                    image_mapping[filename] = image_url
                        
            except Exception as e:
                logger.warning(f"Error processing knowledge base item {kb_item_id}: {e}")
                continue
        
        # Add figure_data images to mapping if provided (MinIO URLs only)
        if figure_data:
            logger.info(f"Adding {len(figure_data)} figures from figure_data to image mapping")
            for figure in figure_data:
                if 'image_path' in figure:
                    image_path = figure['image_path']
                    # Only accept MinIO URLs
                    if image_path.startswith('http') or 'localhost:9000' in image_path:
                        filename = os.path.basename(image_path)
                        image_mapping[filename] = image_path
                    else:
                        logger.warning(f"Figure image not found or not a MinIO URL: {figure.get('image_path', 'No path')}")
        
        if not image_mapping:
            logger.warning("No images found in MinIO storage")
            return content

        def replace_image_path(match):
            original_src = match.group(1)
            other_attributes = match.group(2)
            image_filename = os.path.basename(original_src)

            if image_filename in image_mapping:
                # Use MinIO URL directly
                minio_url = image_mapping[image_filename]
                return f'<img src="{minio_url}"{other_attributes}>'
            else:
                # Image not found, remove the img tag
                logger.warning(f"Image {image_filename} not found in MinIO storage, removing img tag")
                return ""

        # Apply the replacement
        fixed_content = re.sub(
            img_pattern, replace_image_path, content, flags=re.IGNORECASE
        )

        logger.info(f"Image path fixing completed. Found {len(image_mapping)} images in MinIO storage.")
        return fixed_content
        
    except ImportError as e:
        logger.warning(f"Could not import MinIO services: {e}")
        return content
    except Exception as e:
        logger.warning(f"Error fixing image paths: {e}")
        return content


if __name__ == "__main__":
    exit(main())
