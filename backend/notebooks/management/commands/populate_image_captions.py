"""
Management command to populate empty image_caption fields in KnowledgeBaseImage table
using the extract_figure_data function from paper_processing.py.
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from notebooks.models import KnowledgeBaseImage, KnowledgeBaseItem

# Import the extract_figure_data function
from agents.report_agent.utils.paper_processing import extract_figure_data

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate empty image_caption fields using paper processing utilities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Process only images for a specific user ID',
        )
        parser.add_argument(
            '--kb-item-id',
            type=int,
            help='Process only images for a specific knowledge base item ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Update captions even if they already exist',
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting image caption population...")
        
        # Build query for images that need caption updates
        query = KnowledgeBaseImage.objects.select_related('knowledge_base_item')
        
        if options['user_id']:
            query = query.filter(knowledge_base_item__user=options['user_id'])
        
        if options['kb_item_id']:
            query = query.filter(knowledge_base_item_id=options['kb_item_id'])
        
        # Only process images with empty captions unless --force is used
        if not options['force']:
            query = query.filter(image_caption__in=['', None])
        
        images_to_process = query.order_by('knowledge_base_item_id', 'figure_name')
        
        self.stdout.write(f"Found {images_to_process.count()} images to process")
        
        updated_count = 0
        error_count = 0
        processed_kb_items = set()
        
        for image in images_to_process:
            try:
                kb_item = image.knowledge_base_item
                
                # Get the markdown content from the knowledge base item
                markdown_content = self._get_markdown_content(kb_item)
                
                if not markdown_content:
                    self.stdout.write(
                        self.style.WARNING(f"No markdown content found for KB item {kb_item.id}")
                    )
                    continue
                
                # Extract figure data from markdown only once per KB item
                if kb_item.id not in processed_kb_items:
                    figure_data = self._extract_figure_data_from_content(markdown_content)
                    processed_kb_items.add(kb_item.id)
                    
                    # Store figure data temporarily on the KB item for this processing session
                    kb_item._temp_figure_data = figure_data
                else:
                    # Use cached figure data
                    figure_data = getattr(kb_item, '_temp_figure_data', [])
                
                # Find matching caption for this image
                caption = self._find_caption_for_image(image, figure_data)
                
                if caption:
                    if options['dry_run']:
                        self.stdout.write(f"Would update image {image.id} with caption: {caption[:100]}...")
                    else:
                        image.image_caption = caption
                        image.save(update_fields=['image_caption', 'updated_at'])
                        self.stdout.write(f"Updated image {image.id} ({image.figure_name})")
                    
                    updated_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f"No caption found for image {image.id} ({image.figure_name})")
                    )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"Error processing image {image.id}: {e}")
                )
                logger.error(f"Error processing image {image.id}: {e}", exc_info=True)
        
        # Summary
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(f"Dry run complete: {updated_count} images would be updated")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Updated {updated_count} images successfully")
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f"{error_count} images had errors during processing")
            )

    def _get_markdown_content(self, kb_item):
        """Get markdown content from knowledge base item."""
        try:
            # First try to get content from the content field
            if kb_item.content:
                return kb_item.content
            
            # If no inline content, try to get from MinIO file
            if kb_item.file_object_key:
                content = kb_item.get_file_content()
                if content:
                    return content
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting markdown content for KB item {kb_item.id}: {e}")
            return None

    def _extract_figure_data_from_content(self, content):
        """Extract figure data from markdown content using a temporary file."""
        import tempfile
        import os
        
        try:
            # Create a temporary markdown file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Extract figure data using the paper processing function
                figure_data = extract_figure_data(temp_file_path)
                return figure_data or []
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Error extracting figure data from content: {e}")
            return []

    def _find_caption_for_image(self, image, figure_data):
        """Find matching caption for an image from figure data."""
        try:
            # Try to match by figure name first
            if image.figure_name:
                for figure in figure_data:
                    if figure.get('figure_name') == image.figure_name:
                        return figure.get('caption', '')
            
            # Try to match by image name from object key
            if image.minio_object_key:
                import os
                image_basename = os.path.basename(image.minio_object_key).lower()
                for figure in figure_data:
                    figure_image_path = figure.get('image_path', '')
                    if figure_image_path:
                        figure_basename = figure_image_path.split('/')[-1].lower()
                        if figure_basename == image_basename:
                            return figure.get('caption', '')
            
            # Try to match by figure_name/figure number  
            if image.figure_name:
                for figure in figure_data:
                    figure_name = figure.get('figure_name', '')
                    if image.figure_name in figure_name or figure_name in image.figure_name:
                        return figure.get('caption', '')
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding caption for image {image.id}: {e}")
            return None