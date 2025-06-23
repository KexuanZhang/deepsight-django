import re
import argparse
import os
from pathlib import Path

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
    pattern3 = r'\s*\[(transcript|paper)\s+\d+\s+\d{2}:\d{2}:\d{2}\]\s*'
    
    # Pattern for [transcript x][00:00:00] (timestamp format)
    pattern2 = r'\s*\[(transcript|paper)\s+\d+\]\[\d{2}:\d{2}:\d{2}\]\s*'
    
    # Pattern for standalone [transcript x] or [paper x]
    pattern1 = r'\s*\[(transcript|paper)\s+\d+\]\s*'
    
    # First remove the special cases
    content = re.sub(pattern3, '', content)
    
    # Then remove timestamp patterns
    content = re.sub(pattern2, '', content)
    
    # Finally remove the standalone citation patterns
    content = re.sub(pattern1, '', content)
    
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
    chinese_pattern = r'^图\s*\d+：.*\n'
    
    # Pattern to match English captions: lines starting with "Figure" or "figure" followed by digits, then ":", then any text until newline
    english_pattern = r'^[Ff]igure\s*\d+\s*:.*\n'
    
    # Remove Chinese figure captions
    content = re.sub(chinese_pattern, '', content, flags=re.MULTILINE)
    
    # Remove English figure captions
    content = re.sub(english_pattern, '', content, flags=re.MULTILINE)
    
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
        (r'\n[ \t]*<\s*[Ff]igure\s*\d+\s*[^>]*>[ \t]*\n', '\n'),  # \n<Figure 9>\n -> \n
        (r'\n[ \t]*<\s*图\s*\d+\s*[^>]*>[ \t]*\n', '\n'),          # \n<图 9>\n -> \n  
        (r'\n[ \t]*<\s*[Cc]hart\s*>[ \t]*\n', '\n'),               # \n<chart>\n -> \n
        
        # Figure placeholders at the start of content
        (r'^[ \t]*<\s*[Ff]igure\s*\d+\s*[^>]*>[ \t]*\n', ''),     # ^<Figure 9>\n -> (empty)
        (r'^[ \t]*<\s*图\s*\d+\s*[^>]*>[ \t]*\n', ''),             # ^<图 9>\n -> (empty)
        (r'^[ \t]*<\s*[Cc]hart\s*>[ \t]*\n', ''),                  # ^<chart>\n -> (empty)
        
        # Figure placeholders at the end of content  
        (r'\n[ \t]*<\s*[Ff]igure\s*\d+\s*[^>]*>[ \t]*$', ''),     # \n<Figure 9>$ -> (empty)
        (r'\n[ \t]*<\s*图\s*\d+\s*[^>]*>[ \t]*$', ''),             # \n<图 9>$ -> (empty)
        (r'\n[ \t]*<\s*[Cc]hart\s*>[ \t]*$', ''),                  # \n<chart>$ -> (empty)
        
        # Any remaining inline figure placeholders
        (r'<\s*[Ff]igure\s*\d+\s*[^>]*>', ''),                    # <Figure 9> -> (empty)
        (r'<\s*图\s*\d+\s*[^>]*>', ''),                            # <图 9> -> (empty)
        (r'<\s*[Cc]hart\s*>', ''),                                 # <chart> -> (empty)
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Final cleanup: reduce multiple consecutive newlines to maximum of 2
    # This preserves intentional paragraph breaks (double spacing) while cleaning up excess
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content


def process_file(input_file, output_file=None, post_processing=True, remove_figure_captions=True, remove_placeholders=True):
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
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Process the content
    processed_content = remove_citations(content, post_processing)
    processed_content = remove_captions(processed_content, remove_figure_captions)
    processed_content = remove_figure_placeholders(processed_content, remove_placeholders)
    
    # Write the processed content
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(processed_content)
    
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Post-process polished articles to remove citation markers, figure captions, and figure placeholders")
    parser.add_argument("input_file", help="Path to the input markdown file")
    parser.add_argument("--output-file", "-o", help="Path to save the processed file")
    parser.add_argument("--no-post-processing", action="store_true", 
                        help="Skip removing citation markers like [transcript x] and [paper x]")
    parser.add_argument("--no-remove-captions", action="store_true",
                        help="Skip removing figure captions")
    parser.add_argument("--no-remove-placeholders", action="store_true",
                        help="Skip removing figure placeholders like <Figure 9>")
    
    args = parser.parse_args()
    
    try:
        output_file = process_file(
            args.input_file, 
            args.output_file, 
            not args.no_post_processing,  # post_processing is True by default unless --no-post-processing is used
            not args.no_remove_captions,  # remove_figure_captions is True by default unless --no-remove-captions is used
            not args.no_remove_placeholders  # remove_figure_placeholders is True by default unless --no-remove-placeholders is used
        )
        print(f"Processed file saved to: {output_file}")
    except Exception as e:
        print(f"Error processing file: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 