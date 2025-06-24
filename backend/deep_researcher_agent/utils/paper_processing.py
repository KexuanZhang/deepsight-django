import re
import os
import glob
import shutil
import logging
import json

if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        
    lines = paper_content.strip().split('\n')
    
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
                    logging.info(f"Extracted title from markdown header: '{cleaned_title}'")
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
                logging.info(f"Extracted title from first substantial line: '{cleaned_title}'")
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
    clean_title = re.sub(r'<(strong|em|b|i)>(.*?)</\1>', r'\2', text)
    
    # Handle span tags that may contain useful text
    # Extract content from spans but remove the span tags themselves
    clean_title = re.sub(r'<span[^>]*?>(.*?)</span>', r'\1', clean_title)
    
    # Remove any remaining HTML tags (including self-closing ones and those without content)
    clean_title = re.sub(r'<[^>]*?>', '', clean_title)
    
    # Normalize whitespace (collapse multiple spaces into one)
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
    
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
        r"^#+\s*(?:Acknowledgements?|Acknowledgments?)\s*[^a-zA-Z0-9\s]*\s*$"
    ]

    # These patterns match lines that are essentially just the keyword, possibly with some non-alphanumeric flair
    # Used for non-markdown headers like a line containing only "REFERENCES"
    general_section_keywords = [
        r"^\s*[^a-zA-Z0-9\s]*(?:References?|Bibliography|Citations)[^a-zA-Z0-9\s]*\s*$",
        r"^\s*[^a-zA-Z0-9\s]*(?:Acknowledgements?|Acknowledgments?)[^a-zA-Z0-9\s]*\s*$"
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
            logging.warning(f"Paper source folder not found: {paper_source_folder}. Skipping image copying.")
            return

        # Extract the base name of the report_output_dir to use in the image folder name
        report_base_name = os.path.basename(report_output_dir)
        if not report_base_name: # Handles cases like output_dir ending with a '/'
            report_base_name = os.path.basename(os.path.dirname(report_output_dir))

        images_folder_name = f"Images_{report_base_name}"
        images_destination_full_path = os.path.join(report_output_dir, images_folder_name)

        # Find all .jpeg and .jpg files
        jpeg_files = glob.glob(os.path.join(paper_source_folder, "*.jpeg"))
        jpg_files = glob.glob(os.path.join(paper_source_folder, "*.jpg"))
        png_files = glob.glob(os.path.join(paper_source_folder, "*.png")) # Also common

        all_image_files = jpeg_files + jpg_files + png_files

        if not all_image_files:
            logging.info(f"No .jpeg, .jpg, or .png images found in {paper_source_folder} for {paper_md_path}.")
            return

        os.makedirs(images_destination_full_path, exist_ok=True)
        logging.info(f"Ensured image destination folder exists: {images_destination_full_path}")

        copied_count = 0
        for img_src_path in all_image_files:
            img_file_name = os.path.basename(img_src_path)
            img_dst_path = os.path.join(images_destination_full_path, img_file_name)
            try:
                shutil.copy2(img_src_path, img_dst_path)
                logging.info(f"Copied '{img_src_path}' to '{img_dst_path}'")
                copied_count += 1
            except Exception as e:
                logging.error(f"Failed to copy image '{img_src_path}' to '{img_dst_path}': {e}")
        
        if copied_count > 0:
            logging.info(f"Successfully copied {copied_count} image(s) to {images_destination_full_path}.")
        # No message if no images copied, as "No .jpeg, .jpg, or .png images found" already covers it.

    except Exception as e:
        logging.error(f"Error during image copying process for paper {paper_md_path} to {report_output_dir}: {e}")

def insert_figure_images(article_content: str, figures: list[dict], reorder: bool = False) -> str:
    """
    Inserts image paths and captions into the article content at placeholders in the format <Figure X>.
    """
    figure_dict = {fig['figure_name']: (fig['image_path'], fig['caption']) for fig in figures}
    # Look for placeholders in format <Figure X> on standalone lines
    pattern = r"^\s*<Figure \d+>\s*$"
    matches = list(re.finditer(pattern, article_content, re.MULTILINE | re.IGNORECASE))
    
    # Initialize as empty dict first
    first_occurrences = {}
    # Then add each match if it's not already in the dict
    for match in matches:
        # Extract figure name from <Figure X> placeholder
        placeholder_text = match.group().strip()
        figure_name = re.sub(r"[<>]", "", placeholder_text)  # Remove < and > to get "Figure X"
        if figure_name not in first_occurrences:
            first_occurrences[figure_name] = match.start()

    if reorder:
        sorted_figures = sorted(first_occurrences, key=first_occurrences.get)
        mapping = {old: f"Figure {i+1}" for i, old in enumerate(sorted_figures)}
        for old, new in mapping.items():
            # Update placeholders in content
            article_content = re.sub(rf"<{old}>", f"<{new}>", article_content, flags=re.IGNORECASE)
        new_figure_dict = {mapping[old]: figure_dict[old] for old in mapping if old in figure_dict}
        figure_dict = new_figure_dict
        first_occurrences = {mapping[k]: v for k, v in first_occurrences.items() if k in mapping}

    # Filter out figure references that don't exist in figure_dict
    valid_occurrences = {}
    for figure_name, pos in first_occurrences.items():
        if figure_name in figure_dict:
            valid_occurrences[figure_name] = pos
        else:
            logging.warning(f"Figure placeholder '<{figure_name}>' found in article but no matching figure data exists. Skipping insertion.")

    # Sort insertion points by position in text
    insertion_points = [(pos, figure_name) for figure_name, pos in valid_occurrences.items()]
    insertion_points.sort(key=lambda x: x[0])
    
    output_segments = []
    prev_end = 0
    # Define the max height for the images to half a page
    max_image_height = "500px"
    
    # Find and replace each placeholder with figure content
    for pos, figure_name in insertion_points:
        # Find the end of the placeholder line
        placeholder_match = re.search(r"^\s*<" + re.escape(figure_name) + r">\s*$", article_content[pos:], re.MULTILINE)
        if placeholder_match:
            placeholder_end = pos + placeholder_match.end()
            
            # Add content before placeholder
            output_segments.append(article_content[prev_end:pos])
            
            # Add figure content
            image_path, caption = figure_dict[figure_name]
            insertion_text = f'<img src="{image_path}" alt="{figure_name}" style="max-height: {max_image_height};">\n\n{figure_name}: {caption}\n\n'
            output_segments.append(insertion_text)
            
            prev_end = placeholder_end
            
    output_segments.append(article_content[prev_end:])
    result = ''.join(output_segments)
    return re.sub(r'\n{3,}', '\n\n', result)


def preserve_figure_formatting(content: str) -> str:
    """
    Ensures that all figure image embeds are in HTML format <img src="..."> and properly formatted with
    consistent spacing around images and captions.
    """
    # First convert any Markdown images to HTML format
    def md_to_html(match):
        # Extract image path from ![...](...)
        md_img = match.group(0)
        path_match = re.search(r'\]\(([^)]+)\)', md_img)
        if path_match:
            path = path_match.group(1)
            alt_match = re.search(r'\!\[(.*?)\]', md_img)
            alt = alt_match.group(1) if alt_match else "Figure"
            # Convert to HTML format with max-height
            return f'<img src="{path}" alt="{alt}" style="max-height: 500px;">'
        return md_img
    
    # Convert standalone Markdown images to HTML
    content = re.sub(r'\!\[(?:Figure|图)?\s*\d*\]\([^\)]+\)', md_to_html, content)
    
    # Match HTML image tag + caption (ASCII ':' or full-width '：')
    html_figure_pattern = (
        r"(<img\s+[^>]*?(?:src|alt)=[\"'][^>]*?>)"  # HTML img tag
        r"\s*(?:\r?\n)*\s*"                         # any whitespace/newlines
        r"((?:Figure|图)\s*\d+[:：].+?)[ \t]*\r?\n"  # caption line
    )
    content = re.sub(
        html_figure_pattern,
        r"\n\n\1\n\n\2\n\n",
        content,
        flags=re.DOTALL
    )
    
    # Wrap any standalone HTML images with proper spacing
    def wrap_html_img(m):
        return f"\n\n{m.group(1)}\n\n"
    
    content = re.sub(r"(<img\s+[^>]*?(?:src|alt)=[\"'][^>]*?>)", wrap_html_img, content)
    
    # Collapse more than two newlines into exactly two
    content = re.sub(r"\n{3,}", "\n\n", content)
    
    # Ensure each caption line is followed by exactly two newlines
    caption_pattern = re.compile(
        r"^((?:Figure|图)\s*\d+[:：].*?)(?:\r?\n)(?!\r?\n)",
        flags=re.MULTILINE
    )
    content = caption_pattern.sub(r"\1\n\n", content)
    
    return content

def extract_figure_data_from_json(json_file_path):
    """
    Extracts figure information from a video caption JSON file.
    
    Args:
        json_file_path (str): The path to the JSON caption file.
        
    Returns:
        list: A list of dictionaries, where each dictionary represents a figure
              and contains 'image_path', 'figure_name', and 'caption'.
              Returns an empty list if the file_path is empty, or a ValueError
              if the file cannot be read. Returns an empty list if no figures are found.
    """
    if not json_file_path:
        return []
        
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            caption_data = json.load(f)
        
        if not isinstance(caption_data, list):
            logging.warning(f"Expected list in JSON file {json_file_path}, got {type(caption_data)}")
            return []
            
        # Convert to figure data format with proper figure names
        figures = []
        figure_count = 1
        for item in caption_data:
            if isinstance(item, dict) and all(key in item for key in ['image_path', 'figure_name', 'caption']):
                # Use "Figure X" format for consistency with markdown extraction
                figure_name = f"Figure {figure_count}"
                figures.append({
                    "image_path": item["image_path"],
                    "figure_name": figure_name,
                    "caption": item["caption"]
                })
                figure_count += 1
            else:
                logging.warning(f"Skipping invalid item in JSON file {json_file_path}: {item}")
                
        logging.info(f"Extracted {len(figures)} figures from video caption file {json_file_path}")
        return figures
        
    except Exception as e:
        raise ValueError(f"Error reading JSON file {json_file_path}: {e}")

def extract_figure_data(file_path):
    """
    Extracts figure information (image path, figure name, caption) from a Markdown file or JSON caption file.

    Args:
        file_path (str): The path to the Markdown file or JSON caption file.

    Returns:
        list: A list of dictionaries, where each dictionary represents a figure
              and contains 'image_path', 'figure_name', and 'caption'.
              Returns an empty list if the file_path is empty, or a ValueError
              if the file cannot be read. Returns an empty list if no figures are found.
    """
    if not file_path:
        return []

    # Check if it's a JSON caption file
    if file_path.endswith('.json') and '_caption.json' in file_path:
        return extract_figure_data_from_json(file_path)

    # Original markdown processing
    figures = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        raise ValueError(f"Error reading file {file_path}: {e}")

    # Regex to find image path: Allow optional HTML tags around ![](<image_path>)
    image_regex = re.compile(r"^(?:<[^>]+>\s*)*!\[\]\((.*?)\)\s*(?:<[^>]+>)*$", re.IGNORECASE)
    
    # Regex to find HTML img tag with src attribute
    html_img_regex = re.compile(r'^<img\s+[^>]*?src=["\'](.*?)["\'][^>]*?>$', re.IGNORECASE)
    
    # Regex to find figure line: Allow optional HTML tags before "Figure X..."
    # Captures figure number and caption.
    figure_line_regex = re.compile(r"^(?:<[^>]+>\s*)*(?:Figure|图)\s+(\d+)\.?[\s:]?(.*)", re.IGNORECASE)

    # First pass: collect all images
    image_locations = []
    for i, line in enumerate(lines):
        line_cleaned = line.strip()
        image_match = image_regex.match(line_cleaned)
        html_img_match = None if image_match else html_img_regex.match(line_cleaned)
        
        if image_match or html_img_match:
            image_path = image_match.group(1) if image_match else html_img_match.group(1)
            image_locations.append((i, image_path))

    # Second pass: look for captions and associate with the nearest preceding image
    for i, line in enumerate(lines):
        caption_candidate_line = line.lstrip('\ufeff').strip()
        figure_match = figure_line_regex.match(caption_candidate_line)
        
        if figure_match:
            figure_number = figure_match.group(1)
            caption = figure_match.group(2).strip()
            figure_name = f"Figure {figure_number}"
            
            # Find the nearest preceding image
            preceding_images = [(img_idx, img_path) for img_idx, img_path in image_locations if img_idx < i]
            if preceding_images:
                # Get the closest image above this caption
                closest_img_idx, image_path = max(preceding_images, key=lambda x: x[0])
                
                # Check if the distance between image and caption is reasonable (within 10 lines)
                if i - closest_img_idx <= 10:
                    figures.append({
                        "image_path": image_path,
                        "figure_name": figure_name,
                        "caption": caption
                    })
    
    # Remove duplicates while preserving order (in case of multiple captions matching the same figure number)
    unique_figures = []
    seen = set()
    for fig in figures:
        if fig["figure_name"] not in seen:
            seen.add(fig["figure_name"])
            unique_figures.append(fig)
    
    return unique_figures

def format_author_affiliations(json_path):
    """
    Reads a JSON metadata file with keys 'authors' and 'affiliations' and
    returns a dict with two keys:
      - 'author': All authors with their affiliation superscripts
      - 'affiliation': All affiliations with their superscripts
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Format authors
    author_entries = []
    for author in data.get('authors', []):
        name = author.get('name', '')
        aff_ids = author.get('affiliations', [])
        supers = ' '.join(f"<sup>{aid}</sup>" for aid in aff_ids)
        entry = f"{name} {supers}".rstrip()
        author_entries.append(entry)
    author_str = ', '.join(author_entries)

    # Format affiliations in the original order
    aff_entries = []
    for aff in data.get('affiliations', []):
        aid = aff.get('id', '')
        name = aff.get('name', '')
        supers = f"<sup>{aid}</sup>" if aid else ''
        entry = f"{name} {supers}".rstrip()
        aff_entries.append(entry)
    affiliation_str = ', '.join(aff_entries)

    return {"author": author_str, "affiliation": affiliation_str}