#!/usr/bin/env python3
"""
PDF Service for converting Markdown reports to PDF

This service converts Markdown content to PDF format with automatic remote image handling.
It converts remote images to base64 data URLs which work reliably with PDF conversion.

Features:
- Converts Markdown to PDF with embedded remote images
- Converts remote images to base64 data URLs for reliable embedding
- No temporary files or external dependencies required
- Professional PDF styling with CSS
"""

import logging
import re
import base64
import requests
from pathlib import Path
from typing import Optional

try:
    from markdown_pdf import MarkdownPdf, Section
except ImportError:
    MarkdownPdf = None
    Section = None

logger = logging.getLogger(__name__)


class PdfService:
    """Service for converting markdown reports to PDF with automatic image handling"""
    
    def __init__(self):
        if MarkdownPdf is None:
            raise ImportError(
                "markdown-pdf library not found. "
                "Please install it using: pip install markdown-pdf"
            )
    
    def _convert_remote_images_to_base64(self, content: str) -> str:
        """
        Convert remote image URLs to base64 data URLs.
        
        Args:
            content: HTML/markdown content with remote image URLs
            
        Returns:
            str: Content with remote images converted to base64 data URLs
        """
        # Find all img tags with remote URLs
        img_pattern = r'<img([^>]*?)src=["\']([^"\']*https?://[^"\']*)["\']([^>]*?)>'
        
        def replace_img(match):
            before_src = match.group(1)
            img_url = match.group(2)
            after_src = match.group(3)
            
            try:
                response = requests.get(img_url, timeout=30)
                response.raise_for_status()
                
                # Get image data and content type
                img_data = response.content
                content_type = response.headers.get('content-type', 'image/jpeg')
                
                # Convert to base64
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                
                # Create data URL
                data_url = f"data:{content_type};base64,{img_base64}"
                
                # Return the updated img tag
                return f'<img{before_src}src="{data_url}"{after_src}>'
                
            except Exception as e:
                logger.warning(f"Failed to convert image {img_url}: {e}")
                # Return original img tag if conversion fails
                return match.group(0)
        
        # Replace all remote images with base64 data URLs
        updated_content = re.sub(img_pattern, replace_img, content)
        
        return updated_content
    
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
        Convert markdown content to PDF with automatic remote image handling.
        
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
            
            # Convert remote images to base64 data URLs
            content_with_base64_images = self._convert_remote_images_to_base64(markdown_content)
            
            # Create PDF converter with no TOC and optimization enabled
            pdf = MarkdownPdf(
                toc_level=0,  # No table of contents per requirements
                optimize=True
            )
            
            # Determine root directory for any remaining local images
            if input_file_path:
                root_dir = str(Path(input_file_path).parent.resolve())
                logger.debug(f"Using input file directory as root: {root_dir}")
            elif image_root:
                root_dir = str(Path(image_root).resolve())
                logger.debug(f"Using provided image root: {root_dir}")
            else:
                root_dir = str(output_file.parent.resolve())
                logger.debug(f"Using output directory as root: {root_dir}")
            
            # Create section with content
            section = Section(
                content_with_base64_images,
                root=root_dir,
                paper_size=paper_size
            )
            
            # Custom CSS for better appearance with page numbers
            custom_css = """
            body {
                font-family: 'Georgia', 'Times New Roman', serif;
                line-height: 1.6;
                color: black;
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
                height: 500px;
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