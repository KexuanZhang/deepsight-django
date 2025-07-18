#!/usr/bin/env python3
"""
PDF Service for converting Markdown reports to PDF

This service converts Markdown content to PDF format with proper image rendering.
It uses the markdown-pdf library which provides excellent image support and
doesn't require external binaries like wkhtmltopdf.

Features:
- Converts Markdown to PDF with embedded images
- Downloads MinIO images to temp directory for PDF conversion
- Page numbers (no table of contents per requirements)
- Customizable styling with CSS
- No external binary dependencies
"""

import logging
import re
import tempfile
import shutil
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
    """Service for converting markdown reports to PDF"""
    
    def __init__(self):
        if MarkdownPdf is None:
            raise ImportError(
                "markdown-pdf library not found. "
                "Please install it using: pip install markdown-pdf"
            )
    
    def _download_images_and_update_content(self, content: str):
        """
        Download MinIO images to temp directory and update content with local paths.
        Returns (updated_content, temp_dir_path) or (original_content, None) if no images.
        """
        # Find MinIO URLs in content
        minio_pattern = r'<img[^>]+src=["\']([^"\']*localhost:9000[^"\']*)["\'][^>]*>'
        urls = re.findall(minio_pattern, content)
        
        if not urls:
            logger.info("No MinIO images found in content")
            return content, None
        
        # Create temp directory
        temp_dir = Path(tempfile.mkdtemp(prefix="pdf_images_"))
        images_dir = temp_dir / "images"
        images_dir.mkdir()
        
        updated_content = content
        
        try:
            logger.info(f"Found {len(urls)} images to download")
            
            for i, url in enumerate(urls):
                try:
                    # Download image
                    logger.debug(f"Downloading image from: {url}")
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    
                    # Save with simple filename
                    filename = f"image_{i+1}.jpeg"
                    local_path = images_dir / filename
                    
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Replace URL with local path in content
                    local_img_path = f"images/{filename}"
                    updated_content = updated_content.replace(url, local_img_path)
                    
                    logger.info(f"Downloaded image {i+1}: {filename} ({len(response.content):,} bytes)")
                    
                except Exception as e:
                    logger.warning(f"Failed to download image {url}: {e}")
                    continue
            
            return updated_content, str(temp_dir)
            
        except Exception as e:
            logger.error(f"Error downloading images: {e}")
            shutil.rmtree(temp_dir)
            return content, None
    
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
        temp_dir = None
        
        try:
            # Ensure output directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Converting markdown to PDF: {output_file.name}")
            logger.debug(f"Content length: {len(markdown_content):,} characters")
            
            # Download MinIO images and update content
            content_to_convert, temp_dir = self._download_images_and_update_content(markdown_content)
            
            # Use temp directory as image root if we downloaded images
            if temp_dir:
                root_dir = temp_dir
                logger.info(f"Using temp directory as image root: {root_dir}")
            elif image_root:
                root_dir = str(Path(image_root).resolve())
                logger.info(f"Using provided image root: {root_dir}")
            elif input_file_path:
                root_dir = str(Path(input_file_path).parent.resolve())
                logger.info(f"Using input file directory as root: {root_dir}")
            else:
                root_dir = str(output_file.parent.resolve())
                logger.info(f"Using output directory as root: {root_dir}")
            
            # Create PDF converter with no TOC and optimization enabled
            pdf = MarkdownPdf(
                toc_level=0,  # No table of contents per requirements
                optimize=True
            )
            
            # Create section with content
            section = Section(
                content_to_convert,
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
        
        finally:
            # Clean up temp directory
            if temp_dir and Path(temp_dir).exists():
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temp directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
    
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