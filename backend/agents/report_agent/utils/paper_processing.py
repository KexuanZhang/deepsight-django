import re
import os
import glob
import shutil
import logging
import json
import sys

# Add backend to path for common utilities
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from reports.image_utils import clean_title_text

if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )


def _get_figure_url_from_db(figure_id: str, report_id: str) -> str:
    """
    Get the MinIO URL for an image from the database using the figure_id and report_id.
    
    Args:
        figure_id: The figure_id of the ReportImage
        report_id: The report_id to uniquely identify the image
        
    Returns:
        The MinIO URL for the image, or None if not found
    """
    try:
        # Import here to avoid circular imports
        import django
        import os
        from django.conf import settings as django_settings
        
        # Initialize Django if not already done
        if not django_settings.configured:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
            django.setup()
        
        from reports.models import ReportImage
        
        try:
            image = ReportImage.objects.get(figure_id=figure_id, report_id=report_id)
            url = image.get_image_url()
            logging.info(f"Successfully retrieved image URL for figure_id {figure_id} and report_id {report_id} from ReportImage")
            return url
        except ReportImage.DoesNotExist:
            logging.warning(f"Image with figure_id {figure_id} and report_id {report_id} not found in ReportImage database")
            return None
        except ValueError as ve:
            logging.warning(f"Invalid figure_id format {figure_id}: {ve}")
            return None
            
    except Exception as e:
        logging.error(f"Error getting image URL for figure_id {figure_id} and report_id {report_id}: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return None


def parse_paper_title(paper_content: str) -> str:
    """
    Extracts and cleans the title from paper content.
    Priority: markdown headers > first substantial line

    Args:
        paper_content (str): The paper content as a string

    Returns:
        str: The cleaned paper title, or None if no valid title could be extracted
    """
    if not paper_content or not isinstance(paper_content, str):
        logging.warning("Invalid paper content provided for title parsing.")
        return None

    lines = paper_content.strip().split("\n")

    # First pass: Look for markdown headers (prioritize these)
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:  # Skip empty lines
            continue
        if stripped_line.startswith("![]"):  # Skip image lines
            continue

        # Check if this is a markdown header
        if stripped_line.startswith("#"):
            # Extract content after # symbols
            potential_title = stripped_line.lstrip("#").strip()
            if potential_title:
                cleaned_title = _clean_title_text(potential_title)
                if cleaned_title:
                    logging.info(
                        f"Extracted title from markdown header: '{cleaned_title}'"
                    )
                    return cleaned_title

    # Second pass: Fallback to first substantial line if no headers found
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("![]"):
            continue

        # Take first substantial line as fallback (avoid very short lines)
        if len(stripped_line) > 10:
            cleaned_title = _clean_title_text(stripped_line)
            if cleaned_title:
                logging.info(
                    f"Extracted title from first substantial line: '{cleaned_title}'"
                )
                return cleaned_title

    logging.info("Could not parse a valid paper title from the provided content.")
    return None


def _clean_title_text(text: str) -> str:
    """
    Clean title text by removing HTML tags and normalizing whitespace.

    Args:
        text (str): Raw title text that may contain HTML tags

    Returns:
        str: Cleaned title text, or None if no valid text remains
    """
    if not text:
        return None

    # First, extract text content from common HTML tags before removing them
    # Handle <strong>, <em>, <b>, <i> tags by keeping their content
    clean_title = re.sub(r"<(strong|em|b|i)>(.*?)</\1>", r"\2", text)

    # Handle span tags that may contain useful text
    # Extract content from spans but remove the span tags themselves
    clean_title = re.sub(r"<span[^>]*?>(.*?)</span>", r"\1", clean_title)

    # Remove any remaining HTML tags (including self-closing ones and those without content)
    clean_title = re.sub(r"<[^>]*?>", "", clean_title)

    # Normalize whitespace (collapse multiple spaces into one)
    clean_title = re.sub(r"\s+", " ", clean_title).strip()

    return clean_title if clean_title else None


def clean_paper_content(content: str) -> str:
    """Removes sections like References and Acknowledgments from paper content."""
    if not content:
        return ""

    lines = content.splitlines()
    cleaned_lines = []
    in_section_to_remove = False

    # These patterns match markdown-style headers (e.g., "# References", "## Acknowledgements:")
    section_header_patterns = [
        r"^#+\s*(?:References?|Bibliography|Citations)\s*[^a-zA-Z0-9\s]*\s*$",
        # Include both British and American spellings, singular and plural
        r"^#+\s*(?:Acknowledgements?|Acknowledgments?)\s*[^a-zA-Z0-9\s]*\s*$",
    ]

    # These patterns match lines that are essentially just the keyword, possibly with some non-alphanumeric flair
    # Used for non-markdown headers like a line containing only "REFERENCES"
    general_section_keywords = [
        r"^\s*[^a-zA-Z0-9\s]*(?:References?|Bibliography|Citations)[^a-zA-Z0-9\s]*\s*$",
        r"^\s*[^a-zA-Z0-9\s]*(?:Acknowledgements?|Acknowledgments?)[^a-zA-Z0-9\s]*\s*$",
    ]

    for line in lines:
        stripped_line = line.strip()
        is_section_to_remove_header = False

        # Check markdown-style headers for sections to remove
        for pattern in section_header_patterns:
            if re.match(pattern, stripped_line, re.IGNORECASE):
                is_section_to_remove_header = True
                break

        # Check non-markdown lines that exactly match section keywords
        if not is_section_to_remove_header:
            for keyword_pattern in general_section_keywords:
                if re.fullmatch(keyword_pattern, stripped_line, re.IGNORECASE):
                    is_section_to_remove_header = True
                    break

        # If this is the start of a removable section, enter removal mode and skip this line
        if is_section_to_remove_header:
            in_section_to_remove = True
            continue

        # If currently in removal mode and a new markdown header appears that's not marked for removal,
        # stop removing so that subsequent content is preserved
        if in_section_to_remove and stripped_line.startswith("#"):
            in_section_to_remove = False

        # Append lines only when not in a removable section
        if not in_section_to_remove:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def copy_paper_images(paper_md_path: str, report_output_dir: str) -> None:
    """
    Copies all .jpeg and .jpg files from the paper's source directory to a new 'Images_...' folder
    within the specified report output directory.

    Args:
        paper_md_path (str): The full path to the paper's markdown file.
                             Example: "/path/to/data/PaperName/PaperName.md"
        report_output_dir (str): The full path to the specific output directory for the report.
                                 Example: "/path/to/StormDeep/results/model/PaperName_Report"
    """
    if not paper_md_path:
        logging.warning("Paper markdown path not provided. Skipping image copying.")
        return
    if not report_output_dir:
        logging.warning("Report output directory not provided. Skipping image copying.")
        return

    try:
        paper_source_folder = os.path.dirname(paper_md_path)
        if not os.path.isdir(paper_source_folder):
            logging.warning(
                f"Paper source folder not found: {paper_source_folder}. Skipping image copying."
            )
            return

        # Extract the base name of the report_output_dir to use in the image folder name
        report_base_name = os.path.basename(report_output_dir)
        if not report_base_name:  # Handles cases like output_dir ending with a '/'
            report_base_name = os.path.basename(os.path.dirname(report_output_dir))

        images_folder_name = f"Images_{report_base_name}"
        images_destination_full_path = os.path.join(
            report_output_dir, images_folder_name
        )

        # Find all .jpeg and .jpg files
        jpeg_files = glob.glob(os.path.join(paper_source_folder, "*.jpeg"))
        jpg_files = glob.glob(os.path.join(paper_source_folder, "*.jpg"))
        png_files = glob.glob(os.path.join(paper_source_folder, "*.png"))  # Also common

        all_image_files = jpeg_files + jpg_files + png_files

        if not all_image_files:
            logging.info(
                f"No .jpeg, .jpg, or .png images found in {paper_source_folder} for {paper_md_path}."
            )
            return

        os.makedirs(images_destination_full_path, exist_ok=True)
        logging.info(
            f"Ensured image destination folder exists: {images_destination_full_path}"
        )

        copied_count = 0
        for img_src_path in all_image_files:
            img_file_name = os.path.basename(img_src_path)
            img_dst_path = os.path.join(images_destination_full_path, img_file_name)
            try:
                shutil.copy2(img_src_path, img_dst_path)
                logging.info(f"Copied '{img_src_path}' to '{img_dst_path}'")
                copied_count += 1
            except Exception as e:
                logging.error(
                    f"Failed to copy image '{img_src_path}' to '{img_dst_path}': {e}"
                )

        if copied_count > 0:
            logging.info(
                f"Successfully copied {copied_count} image(s) to {images_destination_full_path}."
            )
        # No message if no images copied, as "No .jpeg, .jpg, or .png images found" already covers it.

    except Exception as e:
        logging.error(
            f"Error during image copying process for paper {paper_md_path} to {report_output_dir}: {e}"
        )


# insert_figure_images function removed - use reports.utils.image_utils.ImageInsertionService directly


# preserve_figure_formatting_local function removed - using common utility instead




# extract_figure_data function removed - use reports.utils.image_utils.extract_figure_data_from_markdown directly


def format_author_affiliations(json_path):
    """
    Reads a JSON metadata file with keys 'authors' and 'affiliations' and
    returns a dict with two keys:
      - 'author': All authors with their affiliation superscripts
      - 'affiliation': All affiliations with their superscripts
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Format authors
    author_entries = []
    for author in data.get("authors", []):
        name = author.get("name", "")
        aff_ids = author.get("affiliations", [])
        supers = " ".join(f"<sup>{aid}</sup>" for aid in aff_ids)
        entry = f"{name} {supers}".rstrip()
        author_entries.append(entry)
    author_str = ", ".join(author_entries)

    # Format affiliations in the original order
    aff_entries = []
    for aff in data.get("affiliations", []):
        aid = aff.get("id", "")
        name = aff.get("name", "")
        supers = f"<sup>{aid}</sup>" if aid else ""
        entry = f"{name} {supers}".rstrip()
        aff_entries.append(entry)
    affiliation_str = ", ".join(aff_entries)

    return {"author": author_str, "affiliation": affiliation_str}


# preserve_figure_formatting function removed - use reports.utils.image_utils.preserve_figure_formatting directly
