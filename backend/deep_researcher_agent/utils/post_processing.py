import re
import argparse
import os
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def remove_citations(content, post_processing=True):
    """
    Remove citation markers like [transcript x], [paper x], [transcript x][00:00:00] from content.

    Args:
        content (str): The markdown content to process
        post_processing (bool): Whether to remove citation markers

    Returns:
        str: The processed content
    """
    if not post_processing:
        return content

    # Patterns to match citation markers with optional surrounding spaces
    # Pattern for [transcript x 00:00:00] (timestamp with space instead of bracket)
    pattern3 = r"\s*\[(transcript|paper)\s+\d+\s+\d{2}:\d{2}:\d{2}\]\s*"

    # Pattern for [transcript x][00:00:00] (timestamp format)
    pattern2 = r"\s*\[(transcript|paper)\s+\d+\]\[\d{2}:\d{2}:\d{2}\]\s*"

    # Pattern for standalone [transcript x] or [paper x]
    pattern1 = r"\s*\[(transcript|paper)\s+\d+\]\s*"

    # First remove the special cases
    content = re.sub(pattern3, "", content)

    # Then remove timestamp patterns
    content = re.sub(pattern2, "", content)

    # Finally remove the standalone citation patterns
    content = re.sub(pattern1, "", content)

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
    Remove figure placeholders like <Figure 9>, <figure 9>, <图 9> from content and clean up resulting blank lines.

    Args:
        content (str): The markdown content to process
        remove_figure_placeholders (bool): Whether to remove figure placeholders

    Returns:
        str: The processed content
    """
    if not remove_figure_placeholders:
        return content

    # Targeted patterns that include surrounding whitespace/newlines for better cleanup
    patterns = [
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
    selected_files_paths: List[str],
    report_output_dir: Optional[str] = None,
) -> str:
    """
    Fix image paths in generated report content by replacing broken image src paths
    with correct relative paths from selected_files_paths/images directories.

    Args:
        content (str): The markdown content containing image references
        selected_files_paths (List[str]): List of folder paths from knowledge base
        report_output_dir (Optional[str]): Path to the report output directory for calculating relative paths

    Returns:
        str: The content with fixed image paths (using relative paths)
    """
    if not selected_files_paths:
        logger.warning("No selected_files_paths provided, skipping image path fixing")
        return content

    # Pattern to match img tags with problematic src paths
    img_pattern = r'<img\s+src="([^"]*_page_\d+_[^"]*\.(?:jpeg|jpg|png|gif))"([^>]*)>'

    def replace_image_path(match):
        original_src = match.group(1)
        other_attributes = match.group(2)
        image_filename = os.path.basename(original_src)

        logger.debug(f"Looking for image: {image_filename}")

        # Search for the image in all selected_files_paths/images directories
        found_image_path = None
        for folder_path in selected_files_paths:
            try:
                folder_path_obj = Path(folder_path)
                if not folder_path_obj.exists() or not folder_path_obj.is_dir():
                    logger.debug(
                        f"Folder path does not exist or is not a directory: {folder_path}"
                    )
                    continue

                # Look for images directory
                images_dir = folder_path_obj / "images"
                if not images_dir.exists() or not images_dir.is_dir():
                    logger.debug(f"Images directory not found in: {folder_path}")
                    continue

                # Look for the specific image file
                image_file = images_dir / image_filename
                if image_file.exists() and image_file.is_file():
                    # Found the image!
                    found_image_path = str(image_file)
                    logger.info(f"Found image {image_filename} in {images_dir}")
                    break

            except Exception as e:
                logger.warning(f"Error processing folder path {folder_path}: {e}")
                continue

        if found_image_path:
            # Calculate relative path if report_output_dir is provided
            if report_output_dir:
                try:
                    # Convert to Path objects for easier manipulation
                    report_dir = Path(report_output_dir)
                    image_path = Path(found_image_path)

                    # Calculate relative path from report directory to image
                    relative_path = os.path.relpath(image_path, report_dir)
                    return f'<img src="{relative_path}"{other_attributes}>'
                except Exception as e:
                    logger.warning(
                        f"Could not calculate relative path for {image_filename}: {e}"
                    )
                    # Fall back to absolute path if relative calculation fails
                    return f'<img src="{found_image_path}"{other_attributes}>'
            else:
                # Use absolute path if no report directory provided
                return f'<img src="{found_image_path}"{other_attributes}>'
        else:
            # Image not found in any selected_files_paths/images directory
            # Skip figure insertion as requested
            logger.warning(
                f"Image {image_filename} not found in any images folder, removing img tag"
            )
            return ""  # Remove the img tag completely

    # Apply the replacement
    fixed_content = re.sub(
        img_pattern, replace_image_path, content, flags=re.IGNORECASE
    )

    return fixed_content


def resolve_image_conflicts(selected_files_paths: List[str]) -> Dict[str, str]:
    """
    Create a mapping of image filenames to their full paths, handling conflicts where
    multiple directories contain the same image filename but different actual images.

    Args:
        selected_files_paths (List[str]): List of folder paths from knowledge base

    Returns:
        Dict[str, str]: Mapping of image filename to the full path of the best candidate
    """
    image_mapping = {}
    conflicts = {}
    processed_files = set()  # Track processed files to avoid duplicates

    for folder_path in selected_files_paths:
        try:
            folder_path_obj = Path(folder_path)
            if not folder_path_obj.exists() or not folder_path_obj.is_dir():
                continue

            images_dir = folder_path_obj / "images"
            if not images_dir.exists() or not images_dir.is_dir():
                continue

            # Find all image files with common patterns
            image_patterns = [
                "*_page_*_Picture_*.jpeg",
                "*_page_*_Picture_*.jpg",
                "*_page_*_Picture_*.png",
                "*_page_*_Figure_*.jpeg",
                "*_page_*_Figure_*.jpg",
                "*_page_*_Figure_*.png",
                "*_page_*.jpeg",
                "*_page_*.jpg",
                "*_page_*.png",
            ]

            for pattern in image_patterns:
                for image_file in images_dir.glob(pattern):
                    filename = image_file.name
                    full_path = str(image_file)

                    # Skip if we've already processed this exact file
                    if full_path in processed_files:
                        continue
                    processed_files.add(full_path)

                    if filename in image_mapping:
                        # Conflict detected
                        if filename not in conflicts:
                            conflicts[filename] = [image_mapping[filename]]
                        conflicts[filename].append(full_path)

                        # Choose the most recent file (latest modification time) as the canonical one
                        existing_mtime = os.path.getmtime(image_mapping[filename])
                        new_mtime = os.path.getmtime(full_path)

                        if new_mtime > existing_mtime:
                            image_mapping[filename] = full_path
                            logger.info(
                                f"Image conflict for {filename}: choosing newer file {full_path}"
                            )
                        else:
                            logger.info(
                                f"Image conflict for {filename}: keeping existing file {image_mapping[filename]}"
                            )
                    else:
                        image_mapping[filename] = full_path

        except Exception as e:
            logger.warning(f"Error processing folder path {folder_path}: {e}")
            continue

    # Log conflicts for debugging
    for filename, paths in conflicts.items():
        logger.warning(f"Multiple images found with same name {filename}: {paths}")

    return image_mapping


def fix_image_paths_advanced(
    content: str,
    selected_files_paths: List[str],
    report_output_dir: Optional[str] = None,
) -> str:
    """
    Advanced version of fix_image_paths that handles conflicts and edge cases.

    Args:
        content (str): The markdown content containing image references
        selected_files_paths (List[str]): List of folder paths from knowledge base
        report_output_dir (Optional[str]): Path to the report output directory for calculating relative paths

    Returns:
        str: The content with fixed image paths (using relative paths)
    """
    if not selected_files_paths:
        logger.warning("No selected_files_paths provided, skipping image path fixing")
        return content

    # Create image mapping to handle conflicts
    image_mapping = resolve_image_conflicts(selected_files_paths)

    # Pattern to match img tags with problematic src paths (more comprehensive)
    # This pattern catches any image that starts with an underscore and contains common image extensions
    img_pattern = r'<img\s+src="([^"]*_[^"]*\.(?:jpeg|jpg|png|gif))"([^>]*)>'

    def replace_image_path(match):
        original_src = match.group(1)
        other_attributes = match.group(2)
        image_filename = os.path.basename(original_src)

        if image_mapping and image_filename in image_mapping:
            absolute_path = image_mapping[image_filename]

            # Calculate relative path if report_output_dir is provided
            if report_output_dir:
                try:
                    # Convert to Path objects for easier manipulation
                    report_dir = Path(report_output_dir)
                    image_path = Path(absolute_path)

                    # Calculate relative path from report directory to image
                    relative_path = os.path.relpath(image_path, report_dir)
                    return f'<img src="{relative_path}"{other_attributes}>'
                except Exception as e:
                    logger.warning(
                        f"Could not calculate relative path for {image_filename}: {e}"
                    )
                    # Fall back to absolute path if relative calculation fails
                    return f'<img src="{absolute_path}"{other_attributes}>'
            else:
                # Use absolute path if no report directory provided
                return f'<img src="{absolute_path}"{other_attributes}>'
        else:
            # Image not found, remove the img tag
            logger.warning(
                f"Image {image_filename} not found in any images folder, removing img tag"
            )
            return ""

    # Apply the replacement
    fixed_content = re.sub(
        img_pattern, replace_image_path, content, flags=re.IGNORECASE
    )

    if image_mapping:
        logger.info(
            f"Image path fixing completed. Found {len(image_mapping)} images in selected paths."
        )
    else:
        logger.warning("No images found in any selected_files_paths/images directories")

    return fixed_content


if __name__ == "__main__":
    exit(main())
