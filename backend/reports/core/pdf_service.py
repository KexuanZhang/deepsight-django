#!/usr/bin/env python3
"""
PDF Service for converting Markdown reports to PDF

This service converts Markdown content to PDF format with proper image rendering.
It uses the markdown-pdf library which provides excellent image support and
doesn't require external binaries like wkhtmltopdf.

Features:
- Converts Markdown to PDF with embedded images
- Supports relative and absolute image paths
- Page numbers (no table of contents per requirements)
- Customizable styling with CSS
- No external binary dependencies
"""

import os
import logging
from pathlib import Path
from typing import Optional
from django.conf import settings

try:
    from markdown_pdf import MarkdownPdf, Section
except ImportError:
    MarkdownPdf = None
    Section = None

logger = logging.getLogger(__name__)


class PdfService:
    """Service for converting markdown reports to PDF"""
    
    def __init__(self):
        if MarkdownPdf is None:
            raise ImportError(
                "markdown-pdf library not found. "
                "Please install it using: pip install markdown-pdf"
            )
    
    def convert_markdown_to_pdf(
        self,
        markdown_content: str,
        output_path: str,
        title: str = "Research Report",
        paper_size: str = "A4",
        image_root: Optional[str] = None,
        input_file_path: Optional[str] = None
    ) -> str:
        """
        Convert markdown content to PDF.
        
        Args:
            markdown_content: The markdown content to convert
            output_path: Path where the PDF should be saved
            title: Title for the PDF document
            paper_size: Paper size (A4, Letter, etc.)
            image_root: Root directory for resolving image paths (optional)
            input_file_path: Path to the original markdown file (for image resolution)
            
        Returns:
            str: Path to the generated PDF file
            
        Raises:
            Exception: If conversion fails
        """
        try:
            # Ensure output directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Converting markdown to PDF: {output_file.name}")
            logger.debug(f"Content length: {len(markdown_content):,} characters")
            
            # Create PDF converter with no TOC and optimization enabled
            pdf = MarkdownPdf(
                toc_level=0,  # No table of contents per requirements
                optimize=True
            )
            
            # Check for image references and analyze paths
            import re
            image_patterns = [
                r'!\[.*?\]\((.*?)\)',  # Markdown image syntax
                r'<img[^>]+src=["\']([^"\']+)["\']',  # HTML img tags
            ]
            
            found_images = []
            for pattern in image_patterns:
                matches = re.findall(pattern, markdown_content)
                found_images.extend(matches)
            
            if found_images:
                logger.info(f"📷 Found {len(found_images)} image references:")
                for img in found_images[:5]:  # Show first 5
                    if img.startswith('../'):
                        logger.info(f"   - {img} (relative path)")
                    elif img.startswith('http'):
                        logger.info(f"   - {img} (web URL)")
                    else:
                        logger.info(f"   - {img}")
                if len(found_images) > 5:
                    logger.info(f"   ... and {len(found_images) - 5} more")
            
            # Determine the root directory for image resolution
            if input_file_path:
                # Use the input file path to calculate image root
                input_path = Path(input_file_path)
                
                # Try to intelligently determine the root directory
                # Check if the markdown contains paths that go up multiple levels
                if '../../' in markdown_content:
                    # Calculate how many levels up we need to go
                    max_levels_up = 0
                    lines = markdown_content.split('\n')
                    for line in lines:
                        if ('src=' in line or '![](' in line) and '../' in line:
                            levels = line.count('../')
                            max_levels_up = max(max_levels_up, levels)
                    
                    # Go up the calculated number of levels from the input file directory
                    root_dir = input_path.parent
                    for _ in range(max_levels_up):
                        root_dir = root_dir.parent
                    root_dir = str(root_dir.resolve())
                    
                    logger.info(f"📁 Detected complex relative paths, using root: {root_dir}")
                else:
                    # Use the input file's directory as root
                    root_dir = str(input_path.parent.resolve())
                    logger.info(f"📁 Using input file directory as root: {root_dir}")
            elif image_root:
                # Fallback to provided image root
                root_dir = str(Path(image_root).resolve())
                logger.info(f"📁 Using provided image root: {root_dir}")
            else:
                # Only try to intelligently determine the root directory if no image_root is provided
                # Check if the markdown contains paths that go up multiple levels
                if '../../' in markdown_content:
                    # Calculate how many levels up we need to go
                    max_levels_up = 0
                    lines = markdown_content.split('\n')
                    for line in lines:
                        if ('src=' in line or '![](' in line) and '../' in line:
                            levels = line.count('../')
                            max_levels_up = max(max_levels_up, levels)
                    
                    # IMPORTANT: Since we don't have an actual input file, we use the output directory
                    # but this is only when no image_root is provided (which shouldn't happen in our case)
                    root_dir = output_file.parent
                    for _ in range(max_levels_up):
                        root_dir = root_dir.parent
                    root_dir = str(root_dir.resolve())
                    
                    logger.info(f"📁 Detected complex relative paths, using root: {root_dir}")
                else:
                    # Use the output file's directory as root
                    root_dir = str(output_file.parent.resolve())
                    logger.info(f"📁 Using output directory as root: {root_dir}")
            
            # Create section with content
            section = Section(
                markdown_content,
                root=root_dir,
                paper_size=paper_size
            )
            
            # Custom CSS for better appearance with page numbers
            custom_css = """
            body {
                font-family: 'Helvetica', 'Arial', sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 20px;
                padding-bottom: 60px; /* Space for page numbers */
            }
            h1, h2, h3, h4, h5, h6 {
                color: #2c3e50;
                margin-top: 24px;
                margin-bottom: 16px;
            }
            h1 { 
                font-size: 24px; 
                border-bottom: 2px solid #eee; 
                padding-bottom: 8px; 
            }
            h2 { font-size: 20px; }
            h3 { font-size: 18px; }
            code {
                background-color: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
            pre {
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 12px;
                overflow-x: auto;
            }
            blockquote {
                border-left: 4px solid #ddd;
                margin: 0;
                padding-left: 16px;
                color: #666;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 16px 0;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
                font-weight: bold;
            }
            img {
                max-width: 100%;
                height: auto;
                display: block;
                margin: 16px auto;
            }
            /* Page styling */
            @page {
                margin: 2cm;
            }
            """
            
            # Add section with custom CSS
            pdf.add_section(section, user_css=custom_css)
            
            # Set PDF metadata
            pdf.meta["title"] = title
            pdf.meta["creator"] = "DeepSight Research Report Generator"
            pdf.meta["producer"] = "markdown-pdf library"
            
            # Save the PDF
            pdf.save(str(output_file))
            
            # Log success
            output_size = output_file.stat().st_size
            logger.info(f"Successfully converted to PDF: {output_file}")
            logger.info(f"Output size: {output_size:,} bytes")
            
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Failed to convert markdown to PDF: {e}")
            raise Exception(f"PDF conversion failed: {e}")
    
    def convert_report_file_to_pdf(
        self,
        report_file_path: str,
        title: str = "Research Report"
    ) -> str:
        """
        Convert an existing markdown report file to PDF.
        
        Args:
            report_file_path: Path to the markdown report file
            title: Title for the PDF document
            
        Returns:
            str: Path to the generated PDF file
        """
        try:
            # Read the markdown content
            report_path = Path(report_file_path)
            if not report_path.exists():
                raise FileNotFoundError(f"Report file not found: {report_file_path}")
            
            with open(report_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Generate PDF path (same directory, .pdf extension)
            pdf_path = report_path.with_suffix('.pdf')
            
            return self.convert_markdown_to_pdf(
                markdown_content=markdown_content,
                output_path=str(pdf_path),
                title=title,
                input_file_path=str(report_path)
            )
            
        except Exception as e:
            logger.error(f"Failed to convert report file to PDF: {e}")
            raise Exception(f"Report file PDF conversion failed: {e}") 